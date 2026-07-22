"""
Bayesian Estimation Calibration API Router.

All Bayesian endpoints are defined here and mounted to /bayesian in main.py.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from ..common.dependencies import DbSession
from ..common.limits import MAX_SEARCH_LENGTH
from . import crud, schemas
from .core import (
    Observation,
    Posterior,
    Prior,
    _confidence_label,
    adjust_estimate,
    update_belief,
)

router = APIRouter()


# =============================================================================
# Stateless Calculations
# =============================================================================


@router.post("/calculate", response_model=schemas.PosteriorResult)
async def calculate(input_data: schemas.BayesianCalculateInput):
    """Compute posterior from raw prior, observations, and noise — no DB."""
    try:
        prior = Prior(mean=input_data.prior.mean, variance=input_data.prior.variance)
        observations = [
            Observation(estimated=obs.estimated, actual=obs.actual)
            for obs in input_data.observations
        ]
        posterior = update_belief(
            prior, observations, observation_noise=input_data.observation_noise
        )
        return _posterior_to_result(posterior)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/adjust", response_model=schemas.AdjustEstimateResult)
async def adjust(input_data: schemas.AdjustEstimateInput):
    """Apply a delay factor to a PERT estimate — the cross-module bridge."""
    posterior = Posterior(
        mean=input_data.delay_factor,
        variance=input_data.std_dev**2,
        n_observations=input_data.n_observations,
        observations=(),
    )
    result = adjust_estimate(input_data.pert_expected, posterior)
    return schemas.AdjustEstimateResult(**result)


# =============================================================================
# Context CRUD
# =============================================================================


@router.post("/contexts", response_model=schemas.ContextResponse, status_code=201)
async def create_context(payload: schemas.ContextCreate, db: DbSession):
    """Create a new estimation context (e.g. 'auth', 'infra')."""
    try:
        db_context = crud.create_context(db, payload)
        return _context_to_response(db_context)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/contexts", response_model=schemas.ContextList)
async def list_contexts(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=MAX_SEARCH_LENGTH)] = None,
):
    """List all estimation contexts with pagination."""
    contexts, total = crud.get_contexts(db, page=page, per_page=per_page, search=search)
    return schemas.ContextList(
        items=[_context_to_response(c) for c in contexts],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/contexts/{context_id}", response_model=schemas.ContextResponse)
async def get_context(context_id: int, db: DbSession):
    """Get a specific context with its current belief."""
    db_context = crud.get_context(db, context_id)
    if not db_context:
        raise HTTPException(status_code=404, detail="Context not found")
    return _context_to_response(db_context)


@router.delete("/contexts/{context_id}", status_code=204)
async def delete_context(context_id: int, db: DbSession):
    """Delete a context and all its observations."""
    if not crud.delete_context(db, context_id):
        raise HTTPException(status_code=404, detail="Context not found")


# =============================================================================
# Observations (append-only)
# =============================================================================


@router.post(
    "/contexts/{context_id}/observations",
    response_model=list[schemas.ObservationResponse],
    status_code=201,
)
async def add_observations(
    context_id: int,
    payload: schemas.ObservationBatchCreate,
    db: DbSession,
):
    """Add one or more observations to a context."""
    db_context = crud.get_context(db, context_id)
    if not db_context:
        raise HTTPException(status_code=404, detail="Context not found")
    try:
        new_obs = crud.add_observations(db, db_context, payload)
        return [schemas.ObservationResponse.model_validate(o) for o in new_obs]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/contexts/{context_id}/observations",
    response_model=schemas.ObservationList,
)
async def list_observations(
    context_id: int,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """List observations for a context, most recent first."""
    db_context = crud.get_context(db, context_id)
    if not db_context:
        raise HTTPException(status_code=404, detail="Context not found")
    observations, total = crud.get_observations(db, context_id, page=page, per_page=per_page)
    return schemas.ObservationList(
        items=[schemas.ObservationResponse.model_validate(o) for o in observations],
        total=total,
        page=page,
        per_page=per_page,
    )


# =============================================================================
# Belief Query
# =============================================================================


@router.get("/contexts/{context_id}/belief", response_model=schemas.BeliefResponse)
async def get_belief(context_id: int, db: DbSession):
    """Get the current posterior belief for a context."""
    db_context = crud.get_context(db, context_id)
    if not db_context:
        raise HTTPException(status_code=404, detail="Context not found")
    return _belief_from_context(db_context)


@router.post("/contexts/{context_id}/adjust", response_model=schemas.ContextAdjustResponse)
async def adjust_from_context(
    context_id: int,
    payload: schemas.ContextAdjustInput,
    db: DbSession,
):
    """Apply a context's current belief to a PERT estimate."""
    db_context = crud.get_context(db, context_id)
    if not db_context:
        raise HTTPException(status_code=404, detail="Context not found")

    posterior = crud.compute_belief(db_context)
    belief = _belief_from_posterior(db_context, posterior)
    result = adjust_estimate(payload.pert_expected, posterior)

    return schemas.ContextAdjustResponse(
        belief=belief,
        adjustment=schemas.AdjustEstimateResult(**result),
    )


# =============================================================================
# Helpers
# =============================================================================


def _posterior_to_result(posterior: Posterior) -> schemas.PosteriorResult:
    """Convert core Posterior to response schema."""
    return schemas.PosteriorResult(
        mean=posterior.mean,
        variance=posterior.variance,
        std_dev=posterior.std_dev,
        n_observations=posterior.n_observations,
        credible_interval_68=list(posterior.credible_interval_68),
        credible_interval_95=list(posterior.credible_interval_95),
        credible_interval_99=list(posterior.credible_interval_99),
    )


def _belief_from_context(db_context) -> schemas.BeliefResponse:
    """Compute belief response from a loaded context."""
    posterior = crud.compute_belief(db_context)
    return _belief_from_posterior(db_context, posterior)


def _belief_from_posterior(db_context, posterior: Posterior) -> schemas.BeliefResponse:
    """Build belief response from a pre-computed posterior."""
    return schemas.BeliefResponse(
        context_id=db_context.id,
        context_name=db_context.name,
        posterior=_posterior_to_result(posterior),
        confidence=_confidence_label(posterior),
        n_observations=posterior.n_observations,
    )


def _context_to_response(db_context) -> schemas.ContextResponse:
    """Convert ORM context to response schema with computed belief."""
    posterior = crud.compute_belief(db_context)
    belief = _posterior_to_result(posterior) if db_context.observations else None

    return schemas.ContextResponse(
        id=db_context.id,
        name=db_context.name,
        description=db_context.description,
        prior_mean=db_context.prior_mean,
        prior_variance=db_context.prior_variance,
        observation_noise=db_context.observation_noise,
        n_observations=len(db_context.observations),
        current_belief=belief,
        created_at=db_context.created_at,
        updated_at=db_context.updated_at,
    )
