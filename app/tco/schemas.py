"""
TCO Pydantic schemas for request/response validation.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Calculation Schemas
# =============================================================================


class TCOInput(BaseModel):
    """Input parameters for TCO calculation."""

    initial_price: float = Field(..., gt=0)
    useful_life_years: int = Field(..., gt=0, le=100)
    residual_value: float = Field(default=0, ge=0)
    annual_maintenance: float = Field(default=0, ge=0)
    annual_operating_cost: float = Field(default=0, ge=0)
    discount_rate: float = Field(default=0.03, ge=0, le=1)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "initial_price": 450000,
                "useful_life_years": 12,
                "residual_value": 90000,
                "annual_maintenance": 5000,
            }
        }
    )


class TCOResult(BaseModel):
    """Computed TCO results."""

    total_cost: float
    annual_cost: float
    monthly_cost: float
    cost_per_day: float
    npv_tco: float
    npv_annual: float


class TCOCalculation(BaseModel):
    """Full TCO calculation response."""

    input: TCOInput
    result: TCOResult


# =============================================================================
# Comparison Schemas
# =============================================================================


class CompareOption(TCOInput):
    """Option for comparison (TCOInput + name)."""

    name: str = Field(..., min_length=1, max_length=255)


class CompareRequest(BaseModel):
    """Request for comparing multiple options."""

    options: list[CompareOption] = Field(..., min_length=2)


class CompareResultItem(BaseModel):
    """Single comparison result item."""

    name: str
    initial_price: float
    useful_life_years: int
    monthly_cost: float
    annual_cost: float
    cost_per_day: float
    total_cost: float
    npv_tco: float
    npv_annual: float
    rank: int


class CompareResponse(BaseModel):
    """Comparison results."""

    results: list[CompareResultItem]
    best_option: str


# =============================================================================
# Breakeven Schemas
# =============================================================================


class BreakevenRequest(BaseModel):
    """Request for break-even analysis."""

    option_a: TCOInput
    option_b: TCOInput


class BreakevenResponse(BaseModel):
    """Break-even result."""

    breakeven_years: float | None
    has_breakeven: bool
    message: str


# =============================================================================
# Scenario (Persistence) Schemas
# =============================================================================


class ScenarioCreate(BaseModel):
    """Create a new scenario."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    tags: list[str] = Field(default_factory=list)
    initial_price: float = Field(..., gt=0)
    useful_life_years: int = Field(..., gt=0, le=100)
    residual_value: float = Field(default=0, ge=0)
    annual_maintenance: float = Field(default=0, ge=0)
    annual_operating_cost: float = Field(default=0, ge=0)
    discount_rate: float = Field(default=0.03, ge=0, le=1)


class ScenarioUpdate(BaseModel):
    """Update a scenario (all fields optional)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    tags: list[str] | None = None
    initial_price: float | None = Field(default=None, gt=0)
    useful_life_years: int | None = Field(default=None, gt=0, le=100)
    residual_value: float | None = Field(default=None, ge=0)
    annual_maintenance: float | None = Field(default=None, ge=0)
    annual_operating_cost: float | None = Field(default=None, ge=0)
    discount_rate: float | None = Field(default=None, ge=0, le=1)


class ScenarioResponse(BaseModel):
    """Scenario response with computed results."""

    id: int
    name: str
    description: str | None
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    initial_price: float
    useful_life_years: int
    residual_value: float
    annual_maintenance: float
    annual_operating_cost: float
    discount_rate: float
    total_cost: float
    annual_cost: float
    monthly_cost: float
    cost_per_day: float
    npv_tco: float
    npv_annual: float

    model_config = ConfigDict(from_attributes=True)


class ScenarioList(BaseModel):
    """Paginated scenario list."""

    items: list[ScenarioResponse]
    total: int
    page: int
    per_page: int
