"""
EVM (Earned Value Management) - Core Logic

Performance metrics for project schedule and cost tracking.
Answers the question: "Are we on track?"

Textbook EVM gives you four numbers. Reality-adjusted EVM gives you a signal.

License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

# ============================================================================
# Health Signal
# ============================================================================


class HealthStatus(Enum):
    """Project health derived from EVM metrics.

    Three states, not five. PMOs drown in traffic-light gradients.
    The point is to trigger action, not to admire dashboards.
    """

    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    OFF_TRACK = "off_track"


@dataclass(frozen=True)
class HealthThresholds:
    """Configurable thresholds for health signal interpretation.

    Defaults come from PMI/PMBOK general guidance:
    - SPI or CPI below 0.9 is typically "off track"
    - SPI or CPI below 1.0 but above 0.9 is "at risk"
    - Both at or above 1.0 is "on track"

    Adjust these per project or per organisation. A startup burning
    VC cash has different tolerances than a government infrastructure project.
    """

    spi_off_track: float = 0.9
    spi_at_risk: float = 1.0
    cpi_off_track: float = 0.9
    cpi_at_risk: float = 1.0


# ============================================================================
# Data Structures
# ============================================================================


@dataclass(frozen=True)
class WorkPackage:
    """A unit of planned work in the baseline.

    This is a WBS work package — not an activity or task.
    Granularity matters: too fine and nobody maintains it,
    too coarse and EVM signals are useless.

    Args:
        name: Human-readable identifier (e.g. "Authentication module").
        planned_value: Budgeted cost for this work package.
        weight: Relative weight (0.0–1.0). If None, auto-calculated
            from planned_value / BAC during baseline creation.
    """

    name: str
    planned_value: float
    weight: float | None = None


@dataclass(frozen=True)
class Baseline:
    """The approved plan — the reference point for all EVM calculations.

    A baseline is frozen at project approval. Changing the baseline
    means re-baselining, which is a governance decision, not a math problem.

    Args:
        bac: Budget at Completion (sum of all planned values).
        work_packages: List of planned work packages with weights.
    """

    bac: float
    work_packages: list[dict] = field(default_factory=list)


# ============================================================================
# Core Functions
# ============================================================================


def evm_metrics(
    pv: float,
    ev: float,
    ac: float,
    bac: float,
) -> dict:
    """Calculate all EVM metrics from the three fundamental values.

    This is the atomic calculation — no opinions, just math.

    Args:
        pv: Planned Value — how much work should be done by now (in budget terms).
        ev: Earned Value — how much work is actually done (valued at planned rates).
        ac: Actual Cost — what we actually spent on the work performed.
        bac: Budget at Completion — total planned budget.

    Returns:
        dict with schedule metrics, cost metrics, and forecasts.

    Raises:
        ValueError: If any input is negative, or BAC is zero.

    Example:
        >>> result = evm_metrics(pv=100, ev=90, ac=110, bac=500)
        >>> result["sv"]   # -10.0 (behind schedule)
        >>> result["cpi"]  # 0.82  (over budget)
    """
    # --- Validation ---
    if bac <= 0:
        raise ValueError(f"BAC must be positive, got {bac}")
    if pv < 0:
        raise ValueError(f"PV cannot be negative, got {pv}")
    if ev < 0:
        raise ValueError(f"EV cannot be negative, got {ev}")
    if ac < 0:
        raise ValueError(f"AC cannot be negative, got {ac}")

    # --- Schedule Performance ---
    sv = ev - pv  # Schedule Variance
    spi = ev / pv if pv > 0 else float("inf")  # Schedule Performance Index

    # --- Cost Performance ---
    cv = ev - ac  # Cost Variance
    cpi = ev / ac if ac > 0 else float("inf")  # Cost Performance Index

    # --- Forecasting ---
    eac = bac / cpi if cpi > 0 else float("inf")  # Estimate at Completion
    etc = eac - ac  # Estimate to Complete
    vac = bac - eac  # Variance at Completion

    # To-Complete Performance Index: what CPI must be for remaining work
    remaining_budget = bac - ac
    remaining_work = bac - ev
    tcpi = remaining_work / remaining_budget if remaining_budget > 0 else float("inf")

    # --- Percent Complete ---
    percent_complete = (ev / bac) * 100
    percent_spent = (ac / bac) * 100

    return {
        # Schedule
        "sv": round(sv, 2),
        "spi": round(spi, 4),
        # Cost
        "cv": round(cv, 2),
        "cpi": round(cpi, 4),
        # Forecasting
        "eac": round(eac, 2),
        "etc": round(etc, 2),
        "vac": round(vac, 2),
        "tcpi": round(tcpi, 4),
        # Progress
        "percent_complete": round(percent_complete, 2),
        "percent_spent": round(percent_spent, 2),
    }


def health_signal(
    spi: float,
    cpi: float,
    thresholds: HealthThresholds | None = None,
) -> dict:
    """Interpret SPI and CPI into an actionable health signal.

    The signal is deliberately coarse — three states, not a gradient.
    Nuance belongs in the narrative, not the indicator.

    Args:
        spi: Schedule Performance Index.
        cpi: Cost Performance Index.
        thresholds: Optional custom thresholds. Defaults to PMI guidance.

    Returns:
        dict with status, reasons list, and a one-line summary.

    Example:
        >>> signal = health_signal(spi=0.85, cpi=1.05)
        >>> signal["status"]  # "off_track"
        >>> signal["reasons"] # ["Schedule: SPI 0.85 < 0.9 threshold"]
    """
    if thresholds is None:
        thresholds = HealthThresholds()

    reasons: list[str] = []
    status = HealthStatus.ON_TRACK

    # --- Schedule assessment ---
    if spi < thresholds.spi_off_track:
        status = HealthStatus.OFF_TRACK
        reasons.append(f"Schedule: SPI {spi} < {thresholds.spi_off_track} threshold")
    elif spi < thresholds.spi_at_risk:
        if status != HealthStatus.OFF_TRACK:
            status = HealthStatus.AT_RISK
        reasons.append(f"Schedule: SPI {spi} < {thresholds.spi_at_risk} threshold")

    # --- Cost assessment ---
    if cpi < thresholds.cpi_off_track:
        status = HealthStatus.OFF_TRACK
        reasons.append(f"Cost: CPI {cpi} < {thresholds.cpi_off_track} threshold")
    elif cpi < thresholds.cpi_at_risk:
        if status != HealthStatus.OFF_TRACK:
            status = HealthStatus.AT_RISK
        reasons.append(f"Cost: CPI {cpi} < {thresholds.cpi_at_risk} threshold")

    # --- Summary ---
    if not reasons:
        summary = "Project is on track — schedule and cost within tolerance."
    elif status == HealthStatus.AT_RISK:
        summary = "Project at risk — minor deviation detected."
    else:
        summary = "Project off track — immediate attention required."

    return {
        "status": status.value,
        "reasons": reasons,
        "summary": summary,
    }


def create_baseline(work_packages: list[WorkPackage]) -> Baseline:
    """Create a project baseline from planned work packages.

    Computes BAC from the sum of planned values and normalises weights.
    This is the "freeze" moment — after this, any change is a re-baseline.

    Args:
        work_packages: List of WorkPackage with planned values.

    Returns:
        Baseline with BAC and normalised work packages.

    Raises:
        ValueError: If work_packages is empty or any planned_value is negative.

    Example:
        >>> baseline = create_baseline([
        ...     WorkPackage("Auth", 5000),
        ...     WorkPackage("API", 8000),
        ...     WorkPackage("Frontend", 7000),
        ... ])
        >>> baseline.bac  # 20000.0
    """
    if not work_packages:
        raise ValueError("At least one work package is required")

    for wp in work_packages:
        if wp.planned_value < 0:
            raise ValueError(f"Planned value cannot be negative: {wp.name} = {wp.planned_value}")

    bac = sum(wp.planned_value for wp in work_packages)

    if bac <= 0:
        raise ValueError("Total planned value (BAC) must be positive")

    normalised = []
    for wp in work_packages:
        weight = wp.weight if wp.weight is not None else wp.planned_value / bac
        normalised.append(
            {
                "name": wp.name,
                "planned_value": wp.planned_value,
                "weight": round(weight, 4),
            }
        )

    return Baseline(bac=round(bac, 2), work_packages=normalised)


def evaluate_progress(
    baseline: Baseline,
    percent_planned: float,
    actual_completions: list[dict],
    actual_cost: float,
    thresholds: HealthThresholds | None = None,
) -> dict:
    """Evaluate project progress against baseline.

    This is the high-level function that connects baseline to current state.
    It computes PV, EV from the inputs and delegates to evm_metrics + health_signal.

    Args:
        baseline: The approved project baseline.
        percent_planned: How far through the schedule we should be (0.0–100.0).
            E.g. if today is month 3 of a 12-month project, this is 25.0.
        actual_completions: List of dicts with "name" and "percent_complete" (0.0–100.0)
            for each work package. Missing work packages are treated as 0% complete.
        actual_cost: Total actual cost incurred so far.
        thresholds: Optional custom health thresholds.

    Returns:
        dict with "input", "metrics", "health", and per-work-package breakdown.

    Raises:
        ValueError: If percent_planned not in [0, 100] or actual_cost < 0.

    Example:
        >>> result = evaluate_progress(
        ...     baseline=baseline,
        ...     percent_planned=50.0,
        ...     actual_completions=[
        ...         {"name": "Auth", "percent_complete": 100.0},
        ...         {"name": "API", "percent_complete": 30.0},
        ...     ],
        ...     actual_cost=11000,
        ... )
        >>> result["metrics"]["spi"]   # Are we ahead or behind?
        >>> result["health"]["status"] # "on_track" | "at_risk" | "off_track"
    """
    # --- Validation ---
    if not 0.0 <= percent_planned <= 100.0:
        raise ValueError(f"percent_planned must be 0–100, got {percent_planned}")
    if actual_cost < 0:
        raise ValueError(f"actual_cost cannot be negative, got {actual_cost}")

    # --- Compute PV (Planned Value) ---
    # PV = BAC * (percent_planned / 100)
    # This is a linear approximation. For non-linear planned curves,
    # a future version will accept a PV curve function.
    pv = baseline.bac * (percent_planned / 100.0)

    # --- Compute EV (Earned Value) ---
    # EV = sum of (work_package.planned_value * percent_complete / 100)
    # Build a lookup from actual completions
    completion_map = {item["name"]: item["percent_complete"] for item in actual_completions}

    ev = 0.0
    wp_breakdown = []

    for wp in baseline.work_packages:
        pct = completion_map.get(wp["name"], 0.0)

        if not 0.0 <= pct <= 100.0:
            raise ValueError(f"percent_complete must be 0–100 for '{wp['name']}', got {pct}")

        wp_ev = wp["planned_value"] * (pct / 100.0)
        ev += wp_ev

        wp_breakdown.append(
            {
                "name": wp["name"],
                "planned_value": wp["planned_value"],
                "percent_complete": pct,
                "earned_value": round(wp_ev, 2),
            }
        )

    ev = round(ev, 2)
    pv = round(pv, 2)

    # --- Calculate metrics ---
    metrics = evm_metrics(pv=pv, ev=ev, ac=actual_cost, bac=baseline.bac)

    # --- Health signal ---
    signal = health_signal(
        spi=metrics["spi"],
        cpi=metrics["cpi"],
        thresholds=thresholds,
    )

    return {
        "input": {
            "bac": baseline.bac,
            "pv": pv,
            "ev": ev,
            "ac": actual_cost,
            "percent_planned": percent_planned,
        },
        "metrics": metrics,
        "health": signal,
        "work_packages": wp_breakdown,
    }
