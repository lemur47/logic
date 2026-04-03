"""
Monte Carlo schedule simulation Pydantic schemas for request/response validation.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..common.schemas import PaginatedList

# =============================================================================
# Stateless Simulation Schemas
# =============================================================================


class TaskInput(BaseModel):
    """A task with three-point estimates and optional dependencies."""

    name: str = Field(..., min_length=1, max_length=255)
    optimistic: float = Field(..., ge=0, description="Best-case duration (O)")
    most_likely: float = Field(..., ge=0, description="Most probable duration (M)")
    pessimistic: float = Field(..., ge=0, description="Worst-case duration (P)")
    depends_on: list[str] = Field(default_factory=list, description="Names of predecessor tasks")


class SimulationConfig(BaseModel):
    """Configuration for a Monte Carlo simulation run."""

    num_simulations: int = Field(default=10_000, ge=100, le=1_000_000)
    seed: int | None = Field(default=None, description="Random seed for reproducibility")


class SimulateInput(BaseModel):
    """Input for stateless Monte Carlo simulation."""

    tasks: list[TaskInput] = Field(..., min_length=1)
    config: SimulationConfig = Field(default_factory=SimulationConfig)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tasks": [
                    {"name": "Design", "optimistic": 3, "most_likely": 5, "pessimistic": 10},
                    {
                        "name": "Build",
                        "optimistic": 8,
                        "most_likely": 14,
                        "pessimistic": 25,
                        "depends_on": ["Design"],
                    },
                    {
                        "name": "Test",
                        "optimistic": 3,
                        "most_likely": 5,
                        "pessimistic": 10,
                        "depends_on": ["Build"],
                    },
                ],
                "config": {"num_simulations": 10000, "seed": 42},
            }
        }
    )


class PercentileResult(BaseModel):
    """Percentile values from the simulation."""

    P50: float
    P75: float
    P85: float
    P95: float


class HistogramResult(BaseModel):
    """Histogram data for visualisation."""

    bin_edges: list[float]
    counts: list[int]


class SimulationResult(BaseModel):
    """Output of a Monte Carlo schedule simulation."""

    n_simulations: int
    percentiles: PercentileResult
    histogram: HistogramResult
    critical_path_frequency: dict[str, float]
    mean: float
    std_dev: float
    min_duration: float
    max_duration: float


class TargetProbabilityInput(BaseModel):
    """Input for target completion probability query."""

    target_duration: float = Field(..., gt=0, description="Target deadline to evaluate")


class TargetProbabilityResult(BaseModel):
    """Probability of completing within a target duration."""

    target_duration: float
    probability: float


class CompareWithPertResult(BaseModel):
    """Side-by-side PERT vs Monte Carlo comparison."""

    pert: dict
    montecarlo: dict
    n_tasks: int


# =============================================================================
# Scenario (Persistence) Schemas
# =============================================================================


class ScenarioCreate(BaseModel):
    """Create a new Monte Carlo scenario."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    tasks: list[TaskInput] = Field(..., min_length=1)
    num_simulations: int = Field(default=10_000, ge=100, le=1_000_000)
    seed: int | None = Field(default=None, description="Random seed for reproducibility")


class ScenarioUpdate(BaseModel):
    """Update a scenario (all fields optional)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    tasks: list[TaskInput] | None = Field(default=None, min_length=1)
    num_simulations: int | None = Field(default=None, ge=100, le=1_000_000)
    seed: int | None = None


class ScenarioResponse(BaseModel):
    """Scenario response with cached simulation results."""

    id: int
    name: str
    description: str | None
    tasks: list[TaskInput]
    num_simulations: int
    seed: int | None
    percentiles: PercentileResult
    histogram: HistogramResult
    critical_path_frequency: dict[str, float]
    mean_duration: float
    std_dev_duration: float
    min_duration: float
    max_duration: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


ScenarioList = PaginatedList[ScenarioResponse]
