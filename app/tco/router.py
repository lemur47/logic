"""
TCO API Router.

All TCO endpoints are defined here and mounted to /tco in main.py.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from . import schemas, crud
from .core import calculate_tco, calculate_breakeven, compare_options

router = APIRouter()


# =============================================================================
# Stateless Calculations
# =============================================================================


@router.post("/calculate", response_model=schemas.TCOCalculation)
async def calculate(input_data: schemas.TCOInput):
    """
    Calculate TCO without saving.

    Returns comprehensive cost metrics including NPV-adjusted values.
    """
    try:
        result = calculate_tco(**input_data.model_dump())
        return schemas.TCOCalculation(
            input=input_data, result=schemas.TCOResult(**result)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/compare", response_model=schemas.CompareResponse)
async def compare(request: schemas.CompareRequest):
    """
    Compare multiple TCO options.

    Returns options ranked by annual cost (rank 1 = best).
    """
    try:
        options = [opt.model_dump() for opt in request.options]
        results = compare_options(options)
        return schemas.CompareResponse(
            results=[schemas.CompareResultItem(**r) for r in results],
            best_option=results[0]["name"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/breakeven", response_model=schemas.BreakevenResponse)
async def breakeven(request: schemas.BreakevenRequest):
    """
    Calculate break-even point between two options.

    Determines when a higher initial investment pays off.
    """
    try:
        years = calculate_breakeven(
            request.option_a.model_dump(), request.option_b.model_dump()
        )
        if years is not None:
            return schemas.BreakevenResponse(
                breakeven_years=years,
                has_breakeven=True,
                message=f"Option A breaks even after {years} years",
            )
        return schemas.BreakevenResponse(
            breakeven_years=None,
            has_breakeven=False,
            message="No break-even: Option A has higher or equal annual cost",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Scenario Persistence
# =============================================================================


@router.post("/scenarios", response_model=schemas.ScenarioResponse, status_code=201)
async def create_scenario(
    scenario: schemas.ScenarioCreate, db: Session = Depends(get_db)
):
    """Save a new TCO scenario."""
    try:
        return crud.create_scenario(db, scenario)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/scenarios", response_model=schemas.ScenarioList)
async def list_scenarios(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """List all saved scenarios with pagination."""
    scenarios, total = crud.get_scenarios(
        db, page=page, per_page=per_page, search=search
    )
    return schemas.ScenarioList(
        items=scenarios, total=total, page=page, per_page=per_page
    )


@router.get("/scenarios/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get aggregate statistics across all scenarios."""
    return crud.get_scenario_stats(db)


@router.get("/scenarios/{scenario_id}", response_model=schemas.ScenarioResponse)
async def get_scenario(scenario_id: int, db: Session = Depends(get_db)):
    """Get a specific scenario by ID."""
    scenario = crud.get_scenario(db, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.patch("/scenarios/{scenario_id}", response_model=schemas.ScenarioResponse)
async def update_scenario(
    scenario_id: int,
    scenario_update: schemas.ScenarioUpdate,
    db: Session = Depends(get_db),
):
    """Update a scenario. TCO is automatically recalculated."""
    scenario = crud.update_scenario(db, scenario_id, scenario_update)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.delete("/scenarios/{scenario_id}", status_code=204)
async def delete_scenario(scenario_id: int, db: Session = Depends(get_db)):
    """Delete a scenario."""
    if not crud.delete_scenario(db, scenario_id):
        raise HTTPException(status_code=404, detail="Scenario not found")
