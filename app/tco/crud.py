"""
TCO CRUD operations.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func

from . import models, schemas
from .core import calculate_tco


def create_scenario(db: Session, scenario: schemas.ScenarioCreate) -> models.Scenario:
    """Create a new scenario with computed TCO."""
    tco_result = calculate_tco(
        initial_price=scenario.initial_price,
        useful_life_years=scenario.useful_life_years,
        residual_value=scenario.residual_value,
        annual_maintenance=scenario.annual_maintenance,
        annual_operating_cost=scenario.annual_operating_cost,
        discount_rate=scenario.discount_rate,
    )

    db_scenario = models.Scenario(
        name=scenario.name,
        description=scenario.description,
        tags=scenario.tags,
        initial_price=scenario.initial_price,
        useful_life_years=scenario.useful_life_years,
        residual_value=scenario.residual_value,
        annual_maintenance=scenario.annual_maintenance,
        annual_operating_cost=scenario.annual_operating_cost,
        discount_rate=scenario.discount_rate,
        **tco_result,
    )

    db.add(db_scenario)
    db.commit()
    db.refresh(db_scenario)
    return db_scenario


def get_scenario(db: Session, scenario_id: int) -> models.Scenario | None:
    """Get a single scenario by ID."""
    return db.query(models.Scenario).filter(models.Scenario.id == scenario_id).first()


def get_scenarios(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
) -> tuple[list[models.Scenario], int]:
    """Get paginated list of scenarios."""
    query = db.query(models.Scenario)

    if search:
        query = query.filter(models.Scenario.name.ilike(f"%{search}%"))

    total = query.count()
    offset = (page - 1) * per_page
    scenarios = (
        query.order_by(models.Scenario.updated_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    return scenarios, total


def update_scenario(
    db: Session, scenario_id: int, scenario_update: schemas.ScenarioUpdate
) -> models.Scenario | None:
    """Update a scenario and recalculate TCO."""
    db_scenario = get_scenario(db, scenario_id)
    if not db_scenario:
        return None

    update_data = scenario_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_scenario, field, value)

    # Recalculate TCO
    tco_result = calculate_tco(
        initial_price=db_scenario.initial_price,
        useful_life_years=db_scenario.useful_life_years,
        residual_value=db_scenario.residual_value,
        annual_maintenance=db_scenario.annual_maintenance,
        annual_operating_cost=db_scenario.annual_operating_cost,
        discount_rate=db_scenario.discount_rate,
    )
    for field, value in tco_result.items():
        setattr(db_scenario, field, value)

    db.commit()
    db.refresh(db_scenario)
    return db_scenario


def delete_scenario(db: Session, scenario_id: int) -> bool:
    """Delete a scenario."""
    db_scenario = get_scenario(db, scenario_id)
    if not db_scenario:
        return False

    db.delete(db_scenario)
    db.commit()
    return True


def get_scenario_stats(db: Session) -> dict:
    """Get aggregate statistics."""
    result = db.query(
        func.count(models.Scenario.id).label("total_scenarios"),
        func.avg(models.Scenario.monthly_cost).label("avg_monthly_cost"),
        func.min(models.Scenario.monthly_cost).label("min_monthly_cost"),
        func.max(models.Scenario.monthly_cost).label("max_monthly_cost"),
    ).first()

    return {
        "total_scenarios": result.total_scenarios or 0,
        "avg_monthly_cost": round(result.avg_monthly_cost or 0, 2),
        "min_monthly_cost": round(result.min_monthly_cost or 0, 2),
        "max_monthly_cost": round(result.max_monthly_cost or 0, 2),
    }
