"""
PERT CRUD operations.
"""

import math

from sqlalchemy.orm import Session

from ..common.crud import delete_by_id, get_by_id, paginate
from . import models, schemas
from .core import calculate_task


def _compute_scenario(
    tasks: list[schemas.ScenarioTaskInput],
) -> tuple[list[dict], dict]:
    """Compute per-task estimates and project-level aggregates.

    Returns:
        Tuple of (tasks_data, project_stats).
    """
    tasks_data = []
    total_expected = 0.0
    total_variance = 0.0

    for task in tasks:
        result = calculate_task(
            optimistic=task.optimistic,
            most_likely=task.most_likely,
            pessimistic=task.pessimistic,
        )
        stats = result["textbook"]
        tasks_data.append(
            {
                "name": task.name,
                "optimistic": task.optimistic,
                "most_likely": task.most_likely,
                "pessimistic": task.pessimistic,
                "expected": stats["expected"],
                "std_dev": stats["std_dev"],
                "variance": stats["variance"],
            }
        )
        total_expected += stats["expected"]
        total_variance += stats["variance"]

    total_std_dev = math.sqrt(total_variance)

    project_stats = {
        "total_expected": round(total_expected, 2),
        "total_std_dev": round(total_std_dev, 2),
        "total_variance": round(total_variance, 2),
        "range_68": [
            round(total_expected - total_std_dev, 2),
            round(total_expected + total_std_dev, 2),
        ],
        "range_95": [
            round(total_expected - 2 * total_std_dev, 2),
            round(total_expected + 2 * total_std_dev, 2),
        ],
        "range_99": [
            round(total_expected - 3 * total_std_dev, 2),
            round(total_expected + 3 * total_std_dev, 2),
        ],
    }

    return tasks_data, project_stats


def create_scenario(db: Session, scenario: schemas.ScenarioCreate) -> models.PertScenario:
    """Create a new scenario with computed PERT estimates."""
    tasks_data, project_stats = _compute_scenario(scenario.tasks)

    db_scenario = models.PertScenario(
        name=scenario.name,
        description=scenario.description,
        tags=scenario.tags,
        tasks=tasks_data,
        **project_stats,
    )

    db.add(db_scenario)
    db.commit()
    db.refresh(db_scenario)
    return db_scenario


def get_scenario(db: Session, scenario_id: int) -> models.PertScenario | None:
    """Get a single scenario by ID."""
    return get_by_id(db, models.PertScenario, scenario_id)


def get_scenarios(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
) -> tuple[list[models.PertScenario], int]:
    """Get paginated list of scenarios."""
    return paginate(db, models.PertScenario, page=page, per_page=per_page, search=search)


def update_scenario(
    db: Session, scenario_id: int, scenario_update: schemas.ScenarioUpdate
) -> models.PertScenario | None:
    """Update a scenario and recalculate PERT estimates."""
    db_scenario = get_scenario(db, scenario_id)
    if not db_scenario:
        return None

    update_data = scenario_update.model_dump(exclude_unset=True)

    # Update metadata fields
    for field in ("name", "description", "tags"):
        if field in update_data:
            setattr(db_scenario, field, update_data[field])

    # If tasks were updated, recalculate everything
    if "tasks" in update_data:
        tasks_input = [schemas.ScenarioTaskInput(**t) for t in update_data["tasks"]]
        tasks_data, project_stats = _compute_scenario(tasks_input)
        db_scenario.tasks = tasks_data  # type: ignore[assignment]
        for field, value in project_stats.items():
            setattr(db_scenario, field, value)

    db.commit()
    db.refresh(db_scenario)
    return db_scenario


def delete_scenario(db: Session, scenario_id: int) -> bool:
    """Delete a scenario."""
    return delete_by_id(db, models.PertScenario, scenario_id)
