"""
PERT Pydantic schemas for request/response validation.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..common.limits import MAX_LIST_ITEMS, MAX_NAME_LENGTH
from ..common.schemas import PaginatedList

# =============================================================================
# Input Schemas
# =============================================================================


class TagInput(BaseModel):
    """A tag to apply to a task's pessimistic estimate."""

    name: str = Field(..., min_length=1, max_length=MAX_NAME_LENGTH)
    severity: float = Field(default=0.5, ge=0.0, le=1.0)


class TaskInput(BaseModel):
    """Input for a single PERT task calculation."""

    optimistic: float = Field(..., ge=0)
    most_likely: float = Field(..., ge=0)
    pessimistic: float = Field(..., ge=0)
    tags: list[TagInput] | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "optimistic": 5,
                "most_likely": 10,
                "pessimistic": 20,
                "tags": [{"name": "FRAGMENTED_COMMUNICATION", "severity": 0.8}],
            }
        }
    )


class ProjectTaskInput(TaskInput):
    """A named task within a project estimation."""

    name: str = Field(..., min_length=1, max_length=255)


class ProjectInput(BaseModel):
    """Input for project-level PERT estimation."""

    tasks: list[ProjectTaskInput] = Field(..., min_length=1, max_length=MAX_LIST_ITEMS)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tasks": [
                    {"name": "Design", "optimistic": 3, "most_likely": 5, "pessimistic": 10},
                    {
                        "name": "Build",
                        "optimistic": 10,
                        "most_likely": 15,
                        "pessimistic": 30,
                        "tags": [{"name": "FRAGMENTED_COMMUNICATION", "severity": 0.8}],
                    },
                    {"name": "Test", "optimistic": 2, "most_likely": 4, "pessimistic": 8},
                ]
            }
        }
    )


# =============================================================================
# Output Schemas
# =============================================================================


class StatsResult(BaseModel):
    """Standard PERT statistical results."""

    expected: float
    std_dev: float
    variance: float
    range_68: list[float]
    range_95: list[float]
    range_99: list[float]


class TagApplied(BaseModel):
    """A tag that was applied to an estimate."""

    name: str
    severity: float
    multiplier: float


class AdjustedResult(StatsResult):
    """PERT stats adjusted by insight tags."""

    pessimistic: float
    tags_applied: list[TagApplied]
    combined_multiplier: float


class TaskEstimateInput(BaseModel):
    """Echo of the original task input values."""

    optimistic: float
    most_likely: float
    pessimistic: float


class TaskEstimation(BaseModel):
    """Full result of a single task PERT calculation."""

    input: TaskEstimateInput
    textbook: StatsResult
    adjusted: AdjustedResult | None


class ProjectTaskResult(BaseModel):
    """Individual task result within a project estimation."""

    name: str
    input: TaskEstimateInput
    textbook: StatsResult
    adjusted: AdjustedResult | None


class ProjectEstimation(BaseModel):
    """Full result of a project-level PERT calculation."""

    tasks: list[ProjectTaskResult]
    project: StatsResult
    adjusted_project: StatsResult | None


# =============================================================================
# Scenario (Persistence) Schemas
# =============================================================================


class ScenarioTaskInput(BaseModel):
    """A task within a scenario creation/update request."""

    name: str = Field(..., min_length=1, max_length=255)
    optimistic: float = Field(..., ge=0)
    most_likely: float = Field(..., ge=0)
    pessimistic: float = Field(..., ge=0)


class ScenarioCreate(BaseModel):
    """Create a new PERT scenario."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    tags: list[str] = Field(default_factory=list)
    tasks: list[ScenarioTaskInput] = Field(..., min_length=1, max_length=MAX_LIST_ITEMS)


class ScenarioUpdate(BaseModel):
    """Update a scenario (all fields optional)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    tags: list[str] | None = None
    tasks: list[ScenarioTaskInput] | None = Field(
        default=None, min_length=1, max_length=MAX_LIST_ITEMS
    )


class ScenarioTaskResult(BaseModel):
    """A task stored in a scenario with computed estimates."""

    name: str
    optimistic: float
    most_likely: float
    pessimistic: float
    expected: float
    std_dev: float
    variance: float


class ScenarioResponse(BaseModel):
    """Scenario response with computed results."""

    id: int
    name: str
    description: str | None
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    tasks: list[ScenarioTaskResult]
    total_expected: float
    total_std_dev: float
    total_variance: float
    range_68: list[float]
    range_95: list[float]
    range_99: list[float]

    model_config = ConfigDict(from_attributes=True)


ScenarioList = PaginatedList[ScenarioResponse]
