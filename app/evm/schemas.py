"""
EVM Pydantic schemas for request/response validation.
"""

from datetime import datetime
from math import isinf

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..common.limits import MAX_LIST_ITEMS
from ..common.schemas import PaginatedList

# =============================================================================
# Stateless Calculation Schemas
# =============================================================================


class EvmCalculateInput(BaseModel):
    """Input for direct EVM metric calculation."""

    pv: float = Field(..., ge=0, description="Planned Value")
    ev: float = Field(..., ge=0, description="Earned Value")
    ac: float = Field(..., ge=0, description="Actual Cost")
    bac: float = Field(..., gt=0, description="Budget at Completion")

    model_config = ConfigDict(
        json_schema_extra={"example": {"pv": 100000, "ev": 85000, "ac": 95000, "bac": 200000}}
    )


class EvmMetricsResult(BaseModel):
    """Computed EVM metrics. Infinity values are converted to null for JSON."""

    sv: float
    spi: float | None
    cv: float
    cpi: float | None
    eac: float | None
    etc: float | None
    vac: float | None
    tcpi: float | None
    percent_complete: float
    percent_spent: float

    @field_validator("spi", "cpi", "eac", "etc", "vac", "tcpi", mode="before")
    @classmethod
    def inf_to_none(cls, v: float | None) -> float | None:
        if v is not None and isinstance(v, float) and isinf(v):
            return None
        return v


class HealthThresholdsInput(BaseModel):
    """Custom thresholds for health signal. Nested in HealthInput only."""

    spi_off_track: float = Field(default=0.9, ge=0, le=2)
    spi_at_risk: float = Field(default=1.0, ge=0, le=2)
    cpi_off_track: float = Field(default=0.9, ge=0, le=2)
    cpi_at_risk: float = Field(default=1.0, ge=0, le=2)


class HealthInput(BaseModel):
    """Input for standalone health signal calculation."""

    spi: float = Field(..., description="Schedule Performance Index")
    cpi: float = Field(..., description="Cost Performance Index")
    thresholds: HealthThresholdsInput | None = None


class HealthResult(BaseModel):
    """Health signal response."""

    status: str
    reasons: list[str]
    summary: str


class EvmCalculateResponse(BaseModel):
    """Combined metrics + health response for /evm/calculate."""

    metrics: EvmMetricsResult
    health: HealthResult


# =============================================================================
# Baseline CRUD Schemas
# =============================================================================


class WorkPackageInput(BaseModel):
    """A work package in a baseline creation request."""

    name: str = Field(..., min_length=1, max_length=255)
    planned_value: float = Field(..., gt=0)
    weight: float | None = Field(default=None, ge=0, le=1)


class BaselineCreate(BaseModel):
    """Request to create a new baseline."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    work_packages: list[WorkPackageInput] = Field(..., min_length=1, max_length=MAX_LIST_ITEMS)


class WorkPackageResponse(BaseModel):
    """A work package in a baseline response."""

    id: int
    name: str
    planned_value: float
    weight: float

    model_config = ConfigDict(from_attributes=True)


class BaselineResponse(BaseModel):
    """Full baseline response with computed BAC and work packages."""

    id: int
    name: str
    description: str | None
    bac: float
    work_packages: list[WorkPackageResponse]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


BaselineList = PaginatedList[BaselineResponse]


# =============================================================================
# Evaluation Schemas
# =============================================================================


class ActualCompletion(BaseModel):
    """Completion status for a single work package."""

    name: str = Field(..., min_length=1)
    percent_complete: float = Field(..., ge=0, le=100)


class EvaluateInput(BaseModel):
    """Input for evaluating progress against a stored baseline."""

    percent_planned: float = Field(..., ge=0, le=100)
    actual_completions: list[ActualCompletion] = Field(
        default_factory=list, max_length=MAX_LIST_ITEMS
    )
    actual_cost: float = Field(..., ge=0)
    thresholds: HealthThresholdsInput | None = None


class WorkPackageBreakdown(BaseModel):
    """Per-work-package breakdown in evaluation result."""

    name: str
    planned_value: float
    percent_complete: float
    earned_value: float


class EvaluateResponse(BaseModel):
    """Full evaluation response: inputs, metrics, health, breakdown."""

    input: dict
    metrics: EvmMetricsResult
    health: HealthResult
    work_packages: list[WorkPackageBreakdown]


# =============================================================================
# Snapshot Schemas
# =============================================================================


class SnapshotResponse(BaseModel):
    """A single evaluation snapshot."""

    id: int
    baseline_id: int
    percent_planned: float
    actual_cost: float
    pv: float
    ev: float
    sv: float
    spi: float | None
    cv: float
    cpi: float | None
    eac: float | None
    etc: float | None
    vac: float | None
    tcpi: float | None
    percent_complete: float
    percent_spent: float
    health_status: str
    health_summary: str
    created_at: datetime

    @field_validator("spi", "cpi", "eac", "etc", "vac", "tcpi", mode="before")
    @classmethod
    def inf_to_none(cls, v: float | None) -> float | None:
        if v is not None and isinstance(v, float) and isinf(v):
            return None
        return v

    model_config = ConfigDict(from_attributes=True)


SnapshotList = PaginatedList[SnapshotResponse]
