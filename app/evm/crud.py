"""
EVM CRUD operations.
"""

from typing import cast

from sqlalchemy.orm import Session, joinedload

from . import models, schemas
from .core import (
    Baseline,
    HealthThresholds,
    WorkPackage,
    create_baseline,
    evaluate_progress,
)


def create_baseline_record(db: Session, payload: schemas.BaselineCreate) -> models.EvmBaseline:
    """Create a baseline from work packages, compute BAC and weights."""
    work_packages = [
        WorkPackage(
            name=wp.name,
            planned_value=wp.planned_value,
            weight=wp.weight,
        )
        for wp in payload.work_packages
    ]

    core_baseline = create_baseline(work_packages)

    db_baseline = models.EvmBaseline(
        name=payload.name,
        description=payload.description,
        bac=core_baseline.bac,
    )
    db.add(db_baseline)
    db.flush()

    for wp_data in core_baseline.work_packages:
        db_wp = models.EvmWorkPackage(
            baseline_id=db_baseline.id,
            name=wp_data["name"],
            planned_value=wp_data["planned_value"],
            weight=wp_data["weight"],
        )
        db.add(db_wp)

    db.commit()
    db.refresh(db_baseline)
    return db_baseline


def get_baseline(db: Session, baseline_id: int) -> models.EvmBaseline | None:
    """Get a single baseline by ID with eager-loaded work packages."""
    return (
        db.query(models.EvmBaseline)
        .options(joinedload(models.EvmBaseline.work_packages))
        .filter(models.EvmBaseline.id == baseline_id)
        .first()
    )


def get_baselines(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
) -> tuple[list[models.EvmBaseline], int]:
    """Get paginated list of baselines."""
    query = db.query(models.EvmBaseline)

    if search:
        query = query.filter(models.EvmBaseline.name.ilike(f"%{search}%"))

    total = query.count()
    offset = (page - 1) * per_page
    baselines = (
        query.options(joinedload(models.EvmBaseline.work_packages))
        .order_by(models.EvmBaseline.updated_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    return baselines, total


def delete_baseline(db: Session, baseline_id: int) -> bool:
    """Delete a baseline (cascade deletes work packages and snapshots)."""
    db_baseline = db.query(models.EvmBaseline).filter(models.EvmBaseline.id == baseline_id).first()
    if not db_baseline:
        return False

    db.delete(db_baseline)
    db.commit()
    return True


def evaluate_and_snapshot(
    db: Session,
    db_baseline: models.EvmBaseline,
    payload: schemas.EvaluateInput,
) -> dict:
    """Reconstruct core Baseline from ORM, evaluate, and persist snapshot."""
    core_baseline = Baseline(
        bac=float(cast(float, db_baseline.bac)),
        work_packages=[
            {
                "name": wp.name,
                "planned_value": float(cast(float, wp.planned_value)),
                "weight": float(cast(float, wp.weight)),
            }
            for wp in db_baseline.work_packages
        ],
    )

    thresholds = None
    if payload.thresholds:
        thresholds = HealthThresholds(
            spi_off_track=payload.thresholds.spi_off_track,
            spi_at_risk=payload.thresholds.spi_at_risk,
            cpi_off_track=payload.thresholds.cpi_off_track,
            cpi_at_risk=payload.thresholds.cpi_at_risk,
        )

    actual_completions = [
        {"name": ac.name, "percent_complete": ac.percent_complete}
        for ac in payload.actual_completions
    ]

    result = evaluate_progress(
        baseline=core_baseline,
        percent_planned=payload.percent_planned,
        actual_completions=actual_completions,
        actual_cost=payload.actual_cost,
        thresholds=thresholds,
    )

    snapshot = models.EvmSnapshot(
        baseline_id=db_baseline.id,
        percent_planned=payload.percent_planned,
        actual_cost=payload.actual_cost,
        pv=result["input"]["pv"],
        ev=result["input"]["ev"],
        sv=result["metrics"]["sv"],
        spi=result["metrics"]["spi"],
        cv=result["metrics"]["cv"],
        cpi=result["metrics"]["cpi"],
        eac=result["metrics"]["eac"],
        etc=result["metrics"]["etc"],
        vac=result["metrics"]["vac"],
        tcpi=result["metrics"]["tcpi"],
        percent_complete=result["metrics"]["percent_complete"],
        percent_spent=result["metrics"]["percent_spent"],
        health_status=result["health"]["status"],
        health_summary=result["health"]["summary"],
    )
    db.add(snapshot)
    db.commit()

    return result


def get_snapshots(
    db: Session,
    baseline_id: int,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[models.EvmSnapshot], int]:
    """Get paginated snapshots for a baseline, reverse chronological."""
    query = db.query(models.EvmSnapshot).filter(models.EvmSnapshot.baseline_id == baseline_id)

    total = query.count()
    offset = (page - 1) * per_page
    snapshots = (
        query.order_by(models.EvmSnapshot.created_at.desc()).offset(offset).limit(per_page).all()
    )

    return snapshots, total
