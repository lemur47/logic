"""
PERT API Router.

All PERT endpoints are defined here and mounted to /pert in main.py.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from ..common.dependencies import DbSession
from ..common.limits import MAX_SEARCH_LENGTH
from . import calculate_project, calculate_task, crud
from .core import resolve_insight_tags
from .schemas import (
    ProjectEstimation,
    ProjectInput,
    ScenarioCreate,
    ScenarioList,
    ScenarioResponse,
    ScenarioUpdate,
    TaskEstimation,
    TaskInput,
)

router = APIRouter()


def _resolve_tags(task_input: TaskInput) -> list | None:
    """Adapt this transport's tag models to the shared core resolver.

    The resolution policy itself lives in `app.pert.core.resolve_insight_tags`,
    shared with the MCP surface. All this does is unwrap Pydantic models into the
    plain pairs the core accepts — the core must not import transport schemas.
    """
    if not task_input.tags:
        return None
    return resolve_insight_tags((t.name, t.severity) for t in task_input.tags)


@router.post("/task", response_model=TaskEstimation)
async def estimate_task(task_input: TaskInput):
    """Calculate PERT estimate for a single task.

    Optionally apply insight tags to adjust the pessimistic estimate
    based on real-world risk factors.
    """
    try:
        tags = _resolve_tags(task_input)
        result = calculate_task(
            optimistic=task_input.optimistic,
            most_likely=task_input.most_likely,
            pessimistic=task_input.pessimistic,
            tags=tags,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/project", response_model=ProjectEstimation)
async def estimate_project(project_input: ProjectInput):
    """Aggregate PERT estimates across multiple tasks.

    Project-level statistics assume task independence: expected values sum,
    variances sum, and project std_dev is the square root of summed variances.
    """
    try:
        tasks = []
        for task in project_input.tasks:
            task_dict: dict = {
                "name": task.name,
                "optimistic": task.optimistic,
                "most_likely": task.most_likely,
                "pessimistic": task.pessimistic,
            }
            tags = _resolve_tags(task)
            if tags:
                task_dict["tags"] = tags
            tasks.append(task_dict)

        result = calculate_project(tasks)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# =============================================================================
# Scenario Persistence
# =============================================================================


@router.post("/scenarios", response_model=ScenarioResponse, status_code=201)
async def create_scenario(scenario: ScenarioCreate, db: DbSession):
    """Save a new PERT scenario."""
    try:
        return crud.create_scenario(db, scenario)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/scenarios", response_model=ScenarioList)
async def list_scenarios(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=MAX_SEARCH_LENGTH)] = None,
):
    """List all saved scenarios with pagination."""
    scenarios, total = crud.get_scenarios(db, page=page, per_page=per_page, search=search)
    return ScenarioList(
        items=[ScenarioResponse.model_validate(s) for s in scenarios],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/scenarios/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(scenario_id: int, db: DbSession):
    """Get a specific scenario by ID."""
    scenario = crud.get_scenario(db, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.patch("/scenarios/{scenario_id}", response_model=ScenarioResponse)
async def update_scenario(
    scenario_id: int,
    scenario_update: ScenarioUpdate,
    db: DbSession,
):
    """Update a scenario. PERT estimates are automatically recalculated."""
    scenario = crud.update_scenario(db, scenario_id, scenario_update)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.delete("/scenarios/{scenario_id}", status_code=204)
async def delete_scenario(scenario_id: int, db: DbSession):
    """Delete a scenario."""
    if not crud.delete_scenario(db, scenario_id):
        raise HTTPException(status_code=404, detail="Scenario not found")
