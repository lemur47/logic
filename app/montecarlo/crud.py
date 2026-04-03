"""
Monte Carlo schedule simulation CRUD operations.
"""

from typing import cast

import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..common.crud import delete_by_id, get_by_id, paginate
from . import models, schemas
from .core import Task, simulate_schedule

CALCULATION_FIELDS = {
    "tasks",
    "num_simulations",
    "seed",
}


def _tasks_from_json(tasks_json: list[dict]) -> list[Task]:
    """Convert JSON task list to core Task dataclasses."""
    return [
        Task(
            name=t["name"],
            optimistic=t["optimistic"],
            most_likely=t["most_likely"],
            pessimistic=t["pessimistic"],
            depends_on=tuple(t.get("depends_on", [])),
        )
        for t in tasks_json
    ]


def _tasks_to_json(tasks: list[schemas.TaskInput]) -> list[dict]:
    """Convert Pydantic TaskInput list to JSON-serialisable dicts."""
    return [t.model_dump() for t in tasks]


def _run_simulation(
    tasks_json: list[dict],
    num_simulations: int,
    seed: int | None,
) -> dict:
    """Run simulation and return results as a flat dict for ORM assignment."""
    core_tasks = _tasks_from_json(tasks_json)
    result = simulate_schedule(core_tasks, n_simulations=num_simulations, seed=seed)

    return {
        "percentiles": result.percentiles,
        "histogram": result.histogram,
        "critical_path_frequency": result.critical_path_frequency,
        "mean_duration": round(float(np.mean(result.durations)), 2),
        "std_dev_duration": round(float(np.std(result.durations)), 2),
        "min_duration": round(float(np.min(result.durations)), 2),
        "max_duration": round(float(np.max(result.durations)), 2),
    }


def create_scenario(db: Session, payload: schemas.ScenarioCreate) -> models.MonteCarloScenario:
    """Create a new scenario with computed simulation results."""
    tasks_json = _tasks_to_json(payload.tasks)
    sim_results = _run_simulation(tasks_json, payload.num_simulations, payload.seed)

    db_scenario = models.MonteCarloScenario(
        name=payload.name,
        description=payload.description,
        tasks=tasks_json,
        num_simulations=payload.num_simulations,
        seed=payload.seed,
        **sim_results,
    )

    db.add(db_scenario)
    db.commit()
    db.refresh(db_scenario)
    return db_scenario


def get_scenario(db: Session, scenario_id: int) -> models.MonteCarloScenario | None:
    """Get a single scenario by ID."""
    return get_by_id(db, models.MonteCarloScenario, scenario_id)


def get_scenarios(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
) -> tuple[list[models.MonteCarloScenario], int]:
    """Get paginated list of scenarios."""
    return paginate(db, models.MonteCarloScenario, page=page, per_page=per_page, search=search)


def update_scenario(
    db: Session, scenario_id: int, payload: schemas.ScenarioUpdate
) -> models.MonteCarloScenario | None:
    """Update a scenario. Resimulates only when calculation fields change."""
    db_scenario = get_scenario(db, scenario_id)
    if not db_scenario:
        return None

    update_data = payload.model_dump(exclude_unset=True)

    # Convert tasks from Pydantic models to JSON if present
    if "tasks" in update_data and update_data["tasks"] is not None:
        update_data["tasks"] = [
            t.model_dump() if hasattr(t, "model_dump") else t for t in update_data["tasks"]
        ]

    for field, value in update_data.items():
        setattr(db_scenario, field, value)

    # Only resimulate when calculation-affecting fields changed
    if update_data.keys() & CALCULATION_FIELDS:
        tasks_json = cast(list[dict], db_scenario.tasks)
        sim_results = _run_simulation(
            tasks_json,
            int(cast(int, db_scenario.num_simulations)),
            cast(int | None, db_scenario.seed),
        )
        for field, value in sim_results.items():
            setattr(db_scenario, field, value)

    db.commit()
    db.refresh(db_scenario)
    return db_scenario


def delete_scenario(db: Session, scenario_id: int) -> bool:
    """Delete a scenario."""
    return delete_by_id(db, models.MonteCarloScenario, scenario_id)


def get_scenario_stats(db: Session) -> dict:
    """Get aggregate statistics across all scenarios."""
    result = db.query(
        func.count(models.MonteCarloScenario.id).label("total_scenarios"),
        func.avg(models.MonteCarloScenario.mean_duration).label("avg_mean_duration"),
        func.min(models.MonteCarloScenario.mean_duration).label("min_mean_duration"),
        func.max(models.MonteCarloScenario.mean_duration).label("max_mean_duration"),
    ).first()

    if result is None:
        return {
            "total_scenarios": 0,
            "avg_mean_duration": 0,
            "min_mean_duration": 0,
            "max_mean_duration": 0,
        }

    return {
        "total_scenarios": result.total_scenarios or 0,
        "avg_mean_duration": round(result.avg_mean_duration or 0, 2),
        "min_mean_duration": round(result.min_mean_duration or 0, 2),
        "max_mean_duration": round(result.max_mean_duration or 0, 2),
    }
