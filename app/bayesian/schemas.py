"""
Bayesian estimation calibration Pydantic schemas for request/response validation.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..common.limits import MAX_LIST_ITEMS
from ..common.schemas import PaginatedList

# =============================================================================
# Stateless Calculation Schemas
# =============================================================================


class PriorInput(BaseModel):
    """Prior belief parameters. Defaults to uninformative N(1.0, 0.25)."""

    mean: float = Field(default=1.0, description="Prior mean delay factor")
    variance: float = Field(default=0.25, gt=0, description="Prior variance")


class ObservationInput(BaseModel):
    """A single (estimated, actual) duration pair for stateless calculation."""

    estimated: float = Field(..., gt=0, description="Estimated duration")
    actual: float = Field(..., ge=0, description="Actual duration")


class BayesianCalculateInput(BaseModel):
    """Input for direct Bayesian update calculation."""

    prior: PriorInput = Field(default_factory=PriorInput)
    observations: list[ObservationInput] = Field(..., min_length=1, max_length=MAX_LIST_ITEMS)
    observation_noise: float = Field(
        default=0.15, gt=0, description="Assumed scatter in observations"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "prior": {"mean": 1.0, "variance": 0.25},
                "observations": [
                    {"estimated": 5, "actual": 7},
                    {"estimated": 10, "actual": 13},
                ],
                "observation_noise": 0.15,
            }
        }
    )


class PosteriorResult(BaseModel):
    """Computed posterior distribution."""

    mean: float
    variance: float
    std_dev: float
    n_observations: int
    credible_interval_68: list[float]
    credible_interval_95: list[float]
    credible_interval_99: list[float]


class AdjustEstimateInput(BaseModel):
    """Input for applying a delay factor to a PERT estimate."""

    pert_expected: float = Field(..., gt=0, description="PERT expected duration")
    delay_factor: float = Field(..., gt=0, description="Calibrated delay factor")
    n_observations: int = Field(
        default=0, ge=0, description="Number of observations behind this factor"
    )
    std_dev: float = Field(default=0.5, ge=0, description="Posterior standard deviation")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pert_expected": 12.0,
                "delay_factor": 1.31,
                "n_observations": 6,
                "std_dev": 0.06,
            }
        }
    )


class AdjustEstimateResult(BaseModel):
    """Adjusted PERT estimate with confidence bands."""

    pert_expected: float
    delay_factor: float
    adjusted_expected: float
    adjusted_range_68: list[float]
    adjusted_range_95: list[float]
    n_observations: int
    confidence: str


# =============================================================================
# Context CRUD Schemas
# =============================================================================


class ContextCreate(BaseModel):
    """Request to create a new estimation context."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    prior_mean: float = Field(default=1.0, description="Prior mean delay factor")
    prior_variance: float = Field(default=0.25, gt=0, description="Prior variance")
    observation_noise: float = Field(default=0.15, gt=0, description="Assumed observation scatter")


class ContextResponse(BaseModel):
    """Full context response with current belief."""

    id: int
    name: str
    description: str | None
    prior_mean: float
    prior_variance: float
    observation_noise: float
    n_observations: int
    current_belief: PosteriorResult | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


ContextList = PaginatedList[ContextResponse]


# =============================================================================
# Observation Schemas
# =============================================================================


class ObservationCreate(BaseModel):
    """A single observation to add. Only estimated and actual — delay_factor computed server-side."""

    estimated: float = Field(..., gt=0, description="Estimated duration")
    actual: float = Field(..., ge=0, description="Actual duration")


class ObservationBatchCreate(BaseModel):
    """Batch of observations to add to a context."""

    observations: list[ObservationCreate] = Field(..., min_length=1, max_length=MAX_LIST_ITEMS)


class ObservationResponse(BaseModel):
    """A persisted observation."""

    id: int
    estimated: float
    actual: float
    delay_factor: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


ObservationList = PaginatedList[ObservationResponse]


# =============================================================================
# Belief Query Schemas
# =============================================================================


class BeliefResponse(BaseModel):
    """Current belief for a context — posterior + confidence."""

    context_id: int
    context_name: str
    posterior: PosteriorResult
    confidence: str
    n_observations: int


class ContextAdjustInput(BaseModel):
    """Input for applying a context's belief to a PERT estimate."""

    pert_expected: float = Field(..., gt=0, description="PERT expected duration")


class ContextAdjustResponse(BaseModel):
    """Adjusted estimate using a context's current belief."""

    belief: BeliefResponse
    adjustment: AdjustEstimateResult
