"""
Monte Carlo schedule simulation Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Annotated, Self

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from ..common.limits import MAX_LIST_ITEMS, MAX_NAME_LENGTH
from ..common.schemas import PaginatedList
from . import core
from .core import MAX_SIMULATION_CELLS


def _check_simulation_cells(n_tasks: int, num_simulations: int, n_classes: int = 0) -> None:
    """Reject simulation-count products that would over-allocate.

    Monte Carlo allocates several (n_tasks, num_simulations) float64 arrays, so
    the product — not either factor alone — governs memory. Raising here surfaces
    as a 422 at the API boundary, before any array is allocated.

    The drift path adds (num_simulations, n_classes) arrays, so risk-class count
    bounds the allocation just as task count does. This mirrors
    `core._check_allocation`; both exist deliberately, and both must be widened
    together — widening only the core copy would move the rejection from a 422
    here to a 400 raised out of the router's ValueError handler.
    """
    dimension, extent = "tasks", n_tasks
    if n_classes > n_tasks:
        dimension, extent = "risk_classes", n_classes

    if extent * num_simulations > MAX_SIMULATION_CELLS:
        msg = (
            f"{dimension} × num_simulations ({extent} × {num_simulations}) exceeds the "
            f"limit of {MAX_SIMULATION_CELLS}. Reduce {dimension} or num_simulations."
        )
        raise ValueError(msg)


# =============================================================================
# Stateless Simulation Schemas
# =============================================================================


class TaskInput(BaseModel):
    """A task with three-point estimates and optional dependencies."""

    name: str = Field(..., min_length=1, max_length=255)
    optimistic: float = Field(..., ge=0, description="Best-case duration (O)")
    most_likely: float = Field(..., ge=0, description="Most probable duration (M)")
    pessimistic: float = Field(..., ge=0, description="Worst-case duration (P)")
    depends_on: list[Annotated[str, StringConstraints(max_length=MAX_NAME_LENGTH)]] = Field(
        default_factory=list,
        max_length=MAX_LIST_ITEMS,
        description="Names of predecessor tasks",
    )
    risk_class: str | None = Field(
        default=None,
        max_length=255,
        description=(
            "Optional risk-class identifier consumed by drift simulation. "
            "Ignored unless drift_config is also supplied."
        ),
    )


class SimulationConfig(BaseModel):
    """Configuration for a Monte Carlo simulation run."""

    num_simulations: int = Field(default=10_000, ge=100, le=1_000_000)
    seed: int | None = Field(default=None, description="Random seed for reproducibility")


class PosteriorInput(BaseModel):
    """Gaussian posterior on a risk class's delay factor."""

    mu: float = Field(..., ge=0, description="Posterior mean delay factor (1.0 = unbiased)")
    sigma: float = Field(..., ge=0, description="Posterior standard deviation")


class RiskClassInput(BaseModel):
    """A risk class with Dirichlet concentration and optional posterior."""

    name: str = Field(..., min_length=1, max_length=255)
    prior_alpha: float = Field(
        default=1.0,
        gt=0,
        description="Dirichlet concentration parameter (default 1.0 = uniform)",
    )
    posterior: PosteriorInput | None = Field(
        default=None,
        description="Caller-supplied posterior. None falls back to N(1.0, 0.5).",
    )


class DriftConfigInput(BaseModel):
    """Drift configuration: risk classes and seed for the Dirichlet draw."""

    risk_classes: list[RiskClassInput] = Field(..., min_length=1, max_length=MAX_LIST_ITEMS)
    seed: int | None = Field(
        default=None,
        description="Random seed for the drift draws. Falls back to config.seed if None.",
    )


class SimulateInput(BaseModel):
    """Input for stateless Monte Carlo simulation.

    Adding `drift_config` switches the response from `SimulationResult` to
    `DriftResult` (which extends it with class-mix diagnostics). Legacy
    payloads — without `drift_config` — behave exactly as before.
    """

    tasks: list[TaskInput] = Field(..., min_length=1, max_length=MAX_LIST_ITEMS)
    config: SimulationConfig = Field(default_factory=SimulationConfig)
    drift_config: DriftConfigInput | None = Field(
        default=None,
        description="Optional drift configuration. Triggers Dirichlet-drift simulation.",
    )

    @model_validator(mode="after")
    def _validate_cells(self) -> Self:
        n_classes = len(self.drift_config.risk_classes) if self.drift_config else 0
        _check_simulation_cells(len(self.tasks), self.config.num_simulations, n_classes)
        return self

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


class ClassContribution(BaseModel):
    """Per-class diagnostic for drift simulations.

    Every field is O(1) per class, so the response size scales with the number
    of risk classes and never with the number of simulations.
    """

    mean_weight: float
    mean_mu: float
    n_tasks_bound: int
    weight_std_dev: float
    weight_p10: float
    weight_p50: float
    weight_p90: float


class DriftResult(SimulationResult):
    """Output of a Dirichlet-drift Monte Carlo simulation.

    Extends `SimulationResult` with class-mix diagnostics. Returned by the
    `/simulate` endpoint when the request includes `drift_config`.

    Note: `dirichlet_weights_used` — the full (num_simulations, n_classes) draw
    matrix — was removed. It made response size scale with num_simulations, so
    a valid request could echo back hundreds of megabytes. `class_contribution`
    now carries the spread statistics that made it useful.
    """

    class_contribution: dict[str, ClassContribution]


def _shared_result_fields(result: core.SimulationResult | core.DriftResult) -> dict:
    """Project a core result onto the fields both response models share.

    This block was written out four times — twice in the Monte Carlo router, once
    in the MCP tool, and partially again for the drift response — so the derived
    statistics (mean, std dev, min, max) were each computed independently and
    could drift apart in rounding or definition.

    Lives here rather than in core.py because it builds Pydantic models, which
    core must not know about; and here rather than in a transport, because both
    transports need it.
    """
    return {
        "n_simulations": result.n_simulations,
        "percentiles": PercentileResult(**result.percentiles),
        "histogram": HistogramResult(
            bin_edges=result.histogram["bin_edges"],
            counts=[int(c) for c in result.histogram["counts"]],
        ),
        "critical_path_frequency": result.critical_path_frequency,
        "mean": round(float(np.mean(result.durations)), 2),
        "std_dev": round(float(np.std(result.durations)), 2),
        "min_duration": round(float(np.min(result.durations)), 2),
        "max_duration": round(float(np.max(result.durations)), 2),
    }


def simulation_result_from_core(result: core.SimulationResult) -> SimulationResult:
    """Convert a core simulation result into the API/MCP response model."""
    return SimulationResult(**_shared_result_fields(result))


def drift_result_from_core(result: core.DriftResult) -> DriftResult:
    """Convert a core drift result into the API response model.

    Extends the shared fields with the per-class diagnostics. `n_tasks_bound` is
    cast because the core carries the whole contribution map as dict[str, float].
    """
    return DriftResult(
        **_shared_result_fields(result),
        class_contribution={
            name: ClassContribution(
                mean_weight=stats["mean_weight"],
                mean_mu=stats["mean_mu"],
                n_tasks_bound=int(stats["n_tasks_bound"]),
                weight_std_dev=stats["weight_std_dev"],
                weight_p10=stats["weight_p10"],
                weight_p50=stats["weight_p50"],
                weight_p90=stats["weight_p90"],
            )
            for name, stats in result.class_contribution.items()
        },
    )


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
    tasks: list[TaskInput] = Field(..., min_length=1, max_length=MAX_LIST_ITEMS)
    num_simulations: int = Field(default=10_000, ge=100, le=1_000_000)
    seed: int | None = Field(default=None, description="Random seed for reproducibility")

    @model_validator(mode="after")
    def _validate_cells(self) -> Self:
        _check_simulation_cells(len(self.tasks), self.num_simulations)
        return self


class ScenarioUpdate(BaseModel):
    """Update a scenario (all fields optional)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    tasks: list[TaskInput] | None = Field(default=None, min_length=1, max_length=MAX_LIST_ITEMS)
    num_simulations: int | None = Field(default=None, ge=100, le=1_000_000)
    seed: int | None = None

    @model_validator(mode="after")
    def _validate_cells(self) -> Self:
        # Only checkable when both factors are supplied in the same patch; the
        # crud layer and core guard bound the mixed case (new tasks + stored count).
        if self.tasks is not None and self.num_simulations is not None:
            _check_simulation_cells(len(self.tasks), self.num_simulations)
        return self


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
