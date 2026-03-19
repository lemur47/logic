"""
EVM API Router.

All EVM endpoints are defined here and mounted to /evm in main.py.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from ..common.dependencies import DbSession
from . import crud, schemas
from .core import HealthThresholds, evm_metrics, health_signal

router = APIRouter()


# =============================================================================
# Stateless Calculations
# =============================================================================


@router.post("/calculate", response_model=schemas.EvmCalculateResponse)
async def calculate(input_data: schemas.EvmCalculateInput):
    """Calculate EVM metrics and health signal from raw PV, EV, AC, BAC."""
    try:
        metrics = evm_metrics(
            pv=input_data.pv,
            ev=input_data.ev,
            ac=input_data.ac,
            bac=input_data.bac,
        )
        signal = health_signal(spi=metrics["spi"], cpi=metrics["cpi"])
        return schemas.EvmCalculateResponse(
            metrics=schemas.EvmMetricsResult(**metrics),
            health=schemas.HealthResult(**signal),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/health", response_model=schemas.HealthResult)
async def health(input_data: schemas.HealthInput):
    """Calculate health signal from SPI and CPI."""
    thresholds = None
    if input_data.thresholds:
        thresholds = HealthThresholds(
            spi_off_track=input_data.thresholds.spi_off_track,
            spi_at_risk=input_data.thresholds.spi_at_risk,
            cpi_off_track=input_data.thresholds.cpi_off_track,
            cpi_at_risk=input_data.thresholds.cpi_at_risk,
        )
    result = health_signal(spi=input_data.spi, cpi=input_data.cpi, thresholds=thresholds)
    return schemas.HealthResult(**result)


# =============================================================================
# Baseline CRUD
# =============================================================================


@router.post("/baselines", response_model=schemas.BaselineResponse, status_code=201)
async def create_baseline(payload: schemas.BaselineCreate, db: DbSession):
    """Create a new project baseline from work packages."""
    try:
        return crud.create_baseline_record(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/baselines", response_model=schemas.BaselineList)
async def list_baselines(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query()] = None,
):
    """List all baselines with pagination."""
    baselines, total = crud.get_baselines(db, page=page, per_page=per_page, search=search)
    return schemas.BaselineList(
        items=[schemas.BaselineResponse.model_validate(b) for b in baselines],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/baselines/{baseline_id}", response_model=schemas.BaselineResponse)
async def get_baseline(baseline_id: int, db: DbSession):
    """Get a specific baseline by ID."""
    baseline = crud.get_baseline(db, baseline_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline not found")
    return baseline


@router.delete("/baselines/{baseline_id}", status_code=204)
async def delete_baseline(baseline_id: int, db: DbSession):
    """Delete a baseline and all its work packages and snapshots."""
    if not crud.delete_baseline(db, baseline_id):
        raise HTTPException(status_code=404, detail="Baseline not found")


# =============================================================================
# Evaluation & Snapshots
# =============================================================================


@router.post("/baselines/{baseline_id}/evaluate", response_model=schemas.EvaluateResponse)
async def evaluate(
    baseline_id: int,
    payload: schemas.EvaluateInput,
    db: DbSession,
):
    """Evaluate progress against a stored baseline. Persists a snapshot."""
    baseline = crud.get_baseline(db, baseline_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline not found")
    try:
        result = crud.evaluate_and_snapshot(db, baseline, payload)
        return schemas.EvaluateResponse(
            input=result["input"],
            metrics=schemas.EvmMetricsResult(**result["metrics"]),
            health=schemas.HealthResult(**result["health"]),
            work_packages=[schemas.WorkPackageBreakdown(**wp) for wp in result["work_packages"]],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/baselines/{baseline_id}/snapshots", response_model=schemas.SnapshotList)
async def list_snapshots(
    baseline_id: int,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """List evaluation snapshots for a baseline, most recent first."""
    baseline = crud.get_baseline(db, baseline_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline not found")
    snapshots, total = crud.get_snapshots(db, baseline_id, page=page, per_page=per_page)
    return schemas.SnapshotList(
        items=[schemas.SnapshotResponse.model_validate(s) for s in snapshots],
        total=total,
        page=page,
        per_page=per_page,
    )
