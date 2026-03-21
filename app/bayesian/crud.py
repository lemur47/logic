"""
Bayesian estimation calibration CRUD operations.
"""

from typing import cast

from sqlalchemy.orm import Session, joinedload

from ..common.crud import delete_by_id, get_by_id, paginate
from . import models, schemas
from .core import Observation, Posterior, Prior, update_belief


def create_context(db: Session, payload: schemas.ContextCreate) -> models.BayesianContext:
    """Create a new estimation context."""
    db_context = models.BayesianContext(
        name=payload.name,
        description=payload.description,
        prior_mean=payload.prior_mean,
        prior_variance=payload.prior_variance,
        observation_noise=payload.observation_noise,
    )
    db.add(db_context)
    db.commit()
    db.refresh(db_context)
    return db_context


def get_context(db: Session, context_id: int) -> models.BayesianContext | None:
    """Get a single context by ID with eager-loaded observations."""
    return get_by_id(
        db,
        models.BayesianContext,
        context_id,
        options=[joinedload(models.BayesianContext.observations)],
    )


def get_contexts(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
) -> tuple[list[models.BayesianContext], int]:
    """Get paginated list of contexts."""
    return paginate(
        db,
        models.BayesianContext,
        page=page,
        per_page=per_page,
        search=search,
        options=[joinedload(models.BayesianContext.observations)],
    )


def delete_context(db: Session, context_id: int) -> bool:
    """Delete a context (cascade deletes observations)."""
    return delete_by_id(db, models.BayesianContext, context_id)


def add_observations(
    db: Session,
    db_context: models.BayesianContext,
    payload: schemas.ObservationBatchCreate,
) -> list[models.BayesianObservation]:
    """Append observations to a context. Delay factor computed server-side."""
    new_obs = []
    for obs_input in payload.observations:
        db_obs = models.BayesianObservation(
            context_id=db_context.id,
            estimated=obs_input.estimated,
            actual=obs_input.actual,
            delay_factor=round(obs_input.actual / obs_input.estimated, 6),
        )
        db.add(db_obs)
        new_obs.append(db_obs)

    db.commit()
    for obs in new_obs:
        db.refresh(obs)
    return new_obs


def get_observations(
    db: Session,
    context_id: int,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[models.BayesianObservation], int]:
    """Get paginated observations for a context, reverse chronological."""
    query = db.query(models.BayesianObservation).filter(
        models.BayesianObservation.context_id == context_id
    )

    total = query.count()
    offset = (page - 1) * per_page
    observations = (
        query.order_by(models.BayesianObservation.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    return observations, total


def compute_belief(db_context: models.BayesianContext) -> Posterior:
    """Recompute posterior from a context's prior and eager-loaded observations.

    Expects db_context to have observations already loaded (via joinedload).
    """
    prior = Prior(
        mean=float(cast(float, db_context.prior_mean)),
        variance=float(cast(float, db_context.prior_variance)),
    )

    core_observations = [
        Observation(
            estimated=float(cast(float, obs.estimated)),
            actual=float(cast(float, obs.actual)),
        )
        for obs in db_context.observations
    ]

    return update_belief(
        prior=prior,
        observations=core_observations,
        observation_noise=float(cast(float, db_context.observation_noise)),
    )
