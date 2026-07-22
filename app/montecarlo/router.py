"""
Monte Carlo Schedule Simulation API Router.

All Monte Carlo endpoints are defined here and mounted to /montecarlo in main.py.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from ..common.dependencies import DbSession
from ..common.limits import MAX_SEARCH_LENGTH
from . import crud, schemas
from .core import (
    DriftConfig,
    DriftTask,
    Posterior,
    RiskClass,
    Task,
    probability_of_completion,
    simulate_schedule,
    simulate_with_drift,
)

router = APIRouter()


# =============================================================================
# Stateless Simulation
# =============================================================================


@router.post(
    "/simulate",
    response_model=schemas.DriftResult | schemas.SimulationResult,
)
async def simulate(input_data: schemas.SimulateInput):
    """Run a Monte Carlo schedule simulation — no DB, stateless.

    Without `drift_config`, returns a plain `SimulationResult` (legacy
    behaviour). With `drift_config`, returns a `DriftResult` carrying the
    class-mix diagnostics on top of the standard fields.
    """
    try:
        if input_data.drift_config is None:
            core_tasks = [
                Task(
                    name=t.name,
                    optimistic=t.optimistic,
                    most_likely=t.most_likely,
                    pessimistic=t.pessimistic,
                    depends_on=tuple(t.depends_on),
                )
                for t in input_data.tasks
            ]
            result = simulate_schedule(
                core_tasks,
                n_simulations=input_data.config.num_simulations,
                seed=input_data.config.seed,
            )
            return schemas.simulation_result_from_core(result)

        drift_tasks = [
            DriftTask(
                name=t.name,
                optimistic=t.optimistic,
                most_likely=t.most_likely,
                pessimistic=t.pessimistic,
                depends_on=tuple(t.depends_on),
                risk_class=t.risk_class,
            )
            for t in input_data.tasks
        ]
        risk_classes = tuple(
            RiskClass(
                name=rc.name,
                prior_alpha=rc.prior_alpha,
                posterior=(
                    Posterior(mu=rc.posterior.mu, sigma=rc.posterior.sigma)
                    if rc.posterior is not None
                    else None
                ),
            )
            for rc in input_data.drift_config.risk_classes
        )
        drift_seed = (
            input_data.drift_config.seed
            if input_data.drift_config.seed is not None
            else input_data.config.seed
        )
        drift_cfg = DriftConfig(risk_classes=risk_classes, seed=drift_seed)
        drift_result = simulate_with_drift(
            drift_tasks,
            drift_cfg,
            n_simulations=input_data.config.num_simulations,
        )
        return schemas.drift_result_from_core(drift_result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/simulate/target", response_model=schemas.TargetProbabilityResult)
async def simulate_target(
    input_data: schemas.SimulateInput,
    target: schemas.TargetProbabilityInput,
):
    """Run simulation and return probability of completing within a target duration."""
    try:
        core_tasks = [
            Task(
                name=t.name,
                optimistic=t.optimistic,
                most_likely=t.most_likely,
                pessimistic=t.pessimistic,
                depends_on=tuple(t.depends_on),
            )
            for t in input_data.tasks
        ]
        result = simulate_schedule(
            core_tasks,
            n_simulations=input_data.config.num_simulations,
            seed=input_data.config.seed,
        )
        prob = probability_of_completion(result, target.target_duration)
        return schemas.TargetProbabilityResult(
            target_duration=target.target_duration,
            probability=prob,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# =============================================================================
# Scenario Persistence
# =============================================================================


@router.post("/scenarios", response_model=schemas.ScenarioResponse, status_code=201)
async def create_scenario(payload: schemas.ScenarioCreate, db: DbSession):
    """Save a new Monte Carlo scenario with simulation results."""
    try:
        return _scenario_to_response(crud.create_scenario(db, payload))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/scenarios", response_model=schemas.ScenarioList)
async def list_scenarios(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=MAX_SEARCH_LENGTH)] = None,
):
    """List all saved scenarios with pagination."""
    scenarios, total = crud.get_scenarios(db, page=page, per_page=per_page, search=search)
    return schemas.ScenarioList(
        items=[_scenario_to_response(s) for s in scenarios],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/scenarios/stats")
async def get_stats(db: DbSession):
    """Get aggregate statistics across all scenarios."""
    return crud.get_scenario_stats(db)


@router.get("/scenarios/{scenario_id}", response_model=schemas.ScenarioResponse)
async def get_scenario(scenario_id: int, db: DbSession):
    """Get a specific scenario by ID with cached results."""
    scenario = crud.get_scenario(db, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return _scenario_to_response(scenario)


@router.patch("/scenarios/{scenario_id}", response_model=schemas.ScenarioResponse)
async def update_scenario(
    scenario_id: int,
    payload: schemas.ScenarioUpdate,
    db: DbSession,
):
    """Update a scenario. Resimulates automatically when task data changes."""
    try:
        scenario = crud.update_scenario(db, scenario_id, payload)
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        return _scenario_to_response(scenario)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/scenarios/{scenario_id}", status_code=204)
async def delete_scenario(scenario_id: int, db: DbSession):
    """Delete a scenario."""
    if not crud.delete_scenario(db, scenario_id):
        raise HTTPException(status_code=404, detail="Scenario not found")


# =============================================================================
# Helpers
# =============================================================================


def _scenario_to_response(db_scenario) -> schemas.ScenarioResponse:
    """Convert ORM scenario to response schema."""
    return schemas.ScenarioResponse(
        id=db_scenario.id,
        name=db_scenario.name,
        description=db_scenario.description,
        tasks=[schemas.TaskInput(**t) for t in db_scenario.tasks],
        num_simulations=db_scenario.num_simulations,
        seed=db_scenario.seed,
        percentiles=schemas.PercentileResult(**db_scenario.percentiles),
        histogram=schemas.HistogramResult(**db_scenario.histogram),
        critical_path_frequency=db_scenario.critical_path_frequency,
        mean_duration=db_scenario.mean_duration,
        std_dev_duration=db_scenario.std_dev_duration,
        min_duration=db_scenario.min_duration,
        max_duration=db_scenario.max_duration,
        created_at=db_scenario.created_at,
        updated_at=db_scenario.updated_at,
    )
