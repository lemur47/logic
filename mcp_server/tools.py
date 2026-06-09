"""
MCP tool implementations (v0.1 — four classic PMO tools).

Each public, registered function is exposed as an MCP tool by ``server.py``. Tools
are verb-noun named, and every description leads with the *decision question* —
that is what helps an LLM pick the right tool, not the underlying maths.

Design rules for v0.1:

- **One core, multiple surfaces.** Imports flow ``mcp_server/ → app.{module}.core``
  (pure functions only). We never import FastAPI, routers, or DB models here, so the
  server runs without uvicorn or the SQLite file.
- **Shared Pydantic models, single source of truth.** Inputs and outputs reuse the
  exact models from ``app.{module}.schemas`` — the same classes that validate the
  FastAPI surface. No duplicated field definitions.
- **Structured errors.** Every tool is wrapped by ``@structured_errors`` so failures
  reach the client as tagged messages, never as Python tracebacks.

Note: this module intentionally does *not* use ``from __future__ import annotations``.
The ``@structured_errors`` wrapper lives in another module, and concrete (non-string)
annotations let FastMCP resolve the tool schema without cross-module globals lookups.
"""

import statistics
from typing import Any, Literal

import numpy as np

from app.evm.core import evm_metrics, health_signal
from app.evm.schemas import (
    EvmCalculateInput,
    EvmCalculateResponse,
    EvmMetricsResult,
    HealthResult,
)
from app.montecarlo.core import Task, simulate_schedule
from app.montecarlo.schemas import (
    HistogramResult,
    PercentileResult,
    SimulationConfig,
    SimulationResult,
)
from app.montecarlo.schemas import TaskInput as MonteCarloTaskInput
from app.pert.core import DEFAULT_TAGS, InsightTag, calculate_task
from app.pert.schemas import TaskEstimation
from app.pert.schemas import TaskInput as PertTaskInput
from app.tco.core import compare_options
from app.tco.schemas import CompareRequest, CompareResponse, CompareResultItem

from .errors import ToolValidationError, structured_errors

# Stochastic tools default to this seed so worked examples and tests are
# reproducible (project worked-example convention). Pass a different integer
# to vary the run.
DEFAULT_SEED = 42


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _resolve_task_tags(
    task: PertTaskInput,
) -> list[InsightTag | tuple[InsightTag, float]] | None:
    """Resolve a task's insight-tag names into ``(InsightTag, severity)`` pairs.

    Names are matched case-insensitively against the known catalogue. An unknown
    name fails loudly — better than silently applying nothing.
    """
    if not task.tags:
        return None
    resolved: list[InsightTag | tuple[InsightTag, float]] = []
    for tag_input in task.tags:
        tag = DEFAULT_TAGS.get(tag_input.name.upper())
        if tag is None:
            available = ", ".join(sorted(DEFAULT_TAGS.keys()))
            raise ToolValidationError(
                f"Unknown insight tag '{tag_input.name}'. Available: {available}"
            )
        resolved.append((tag, tag_input.severity))
    return resolved


# ─────────────────────────────────────────────────────────────────────
# Tool 1 — estimate_task_duration (PERT)
# ─────────────────────────────────────────────────────────────────────


@structured_errors
def estimate_task_duration(task: PertTaskInput) -> TaskEstimation:
    """Estimate how long a single task will take from a three-point estimate.

    Use when: you have a human optimistic / most-likely / pessimistic estimate for
    one task and want the textbook PERT expected duration, plus — optionally — an
    estimate adjusted for known real-world frictions.

    The PERT expected value is ``(O + 4M + P) / 6`` and the standard deviation is
    ``(P - O) / 6``; both are expressed in whatever time unit the estimates use
    (days, weeks — the tool is unit-agnostic). Insight tags widen the pessimistic
    tail to reflect frictions the raw estimate ignores.

    Args:
        task: The three-point estimate. Fields:
            ``optimistic`` (O, best case), ``most_likely`` (M), ``pessimistic``
            (P, worst case) — all in the same time unit, with ``O <= M <= P``.
            ``tags`` (optional): insight tags, each a ``{name, severity}`` pair with
            severity in ``[0, 1]``. Known names (case-insensitive):
            FRAGMENTED_COMMUNICATION, MULTIPLE_STAKEHOLDERS, HIDDEN_DEPENDENCIES.

    Returns:
        A ``TaskEstimation`` with ``input`` (echo of O/M/P), ``textbook`` (PERT
        ``expected``, ``std_dev``, ``variance`` and the 68/95/99% ranges), and
        ``adjusted`` (the same stats after tags widen the tail, or ``null`` when no
        tags were supplied).
    """
    tags = _resolve_task_tags(task)
    result = calculate_task(
        optimistic=task.optimistic,
        most_likely=task.most_likely,
        pessimistic=task.pessimistic,
        tags=tags,
    )
    return TaskEstimation.model_validate(result)


# ─────────────────────────────────────────────────────────────────────
# Tool 2 — identify_schedule_risk (Monte Carlo schedule)
# ─────────────────────────────────────────────────────────────────────


@structured_errors
def identify_schedule_risk(
    tasks: list[MonteCarloTaskInput],
    config: SimulationConfig | None = None,
) -> SimulationResult:
    """Find how long a task network is likely to take, and which tasks drive the risk.

    Use when: you have several tasks with three-point estimates and dependencies, and
    want a probabilistic completion forecast rather than a single additive number.
    Runs a Monte Carlo simulation, sampling each task from its beta-PERT distribution
    and honouring the dependency graph.

    Args:
        tasks: The task network. Each task has ``name``, three-point estimates
            (``optimistic`` / ``most_likely`` / ``pessimistic``, same time unit), and
            an optional ``depends_on`` list of predecessor task names. (``risk_class``
            is reserved for v0.2 drift simulation and is ignored here.)
            Note: if **no** task in the network declares a ``depends_on`` the tasks
            are assumed to form a sequential chain (durations sum) — bare tasks are
            *not* inferred to run in parallel. Declare ``depends_on`` to model genuine
            concurrency, where the makespan is the longest path, not the sum.
        config: Optional run settings — ``num_simulations`` (100–1,000,000; default
            10,000) and ``seed``. When ``seed`` is omitted it defaults to 42 for a
            reproducible run; pass a different integer to vary it.

    Returns:
        A ``SimulationResult`` with ``percentiles`` (P50/P75/P85/P95 of total
        duration), ``critical_path_frequency`` (per task, the fraction of runs in
        which it sat on the critical path — the higher, the more it drives schedule
        risk), a 50-bin ``histogram`` of durations, and the run's ``mean``,
        ``std_dev``, ``min_duration`` and ``max_duration``.
    """
    if not tasks:
        raise ToolValidationError("Provide at least one task to simulate.")

    run_config = config or SimulationConfig()
    seed = run_config.seed if run_config.seed is not None else DEFAULT_SEED

    core_tasks = [
        Task(
            name=t.name,
            optimistic=t.optimistic,
            most_likely=t.most_likely,
            pessimistic=t.pessimistic,
            depends_on=tuple(t.depends_on),
        )
        for t in tasks
    ]
    result = simulate_schedule(core_tasks, n_simulations=run_config.num_simulations, seed=seed)

    return SimulationResult(
        n_simulations=result.n_simulations,
        percentiles=PercentileResult(**result.percentiles),
        histogram=HistogramResult(
            bin_edges=result.histogram["bin_edges"],
            counts=[int(c) for c in result.histogram["counts"]],
        ),
        critical_path_frequency=result.critical_path_frequency,
        mean=round(float(np.mean(result.durations)), 2),
        std_dev=round(float(np.std(result.durations)), 2),
        min_duration=round(float(np.min(result.durations)), 2),
        max_duration=round(float(np.max(result.durations)), 2),
    )


# ─────────────────────────────────────────────────────────────────────
# Tool 3 — compare_investment_options (TCO)
# ─────────────────────────────────────────────────────────────────────


@structured_errors
def compare_investment_options(request: CompareRequest) -> CompareResponse:
    """Compare options on real lifetime cost, not sticker price.

    Use when: you have two or more options (vendors, platforms, tools), each with an
    initial price, a useful life, and recurring costs, and want them ranked by
    total cost of ownership rather than up-front price.

    Args:
        request: ``options`` — a list of at least two options. Each option has
            ``name``, ``initial_price``, ``useful_life_years``, and optional
            ``residual_value``, ``annual_maintenance``, ``annual_operating_cost`` and
            ``discount_rate`` (default 0.03). Monetary fields share one currency;
            the tool is currency-agnostic.

    Returns:
        A ``CompareResponse`` whose ``results`` are ranked by annual cost ascending
        (rank 1 = cheapest). Each item carries ``total_cost``, ``annual_cost``,
        ``monthly_cost``, ``cost_per_day``, NPV-adjusted ``npv_tco`` / ``npv_annual``,
        and its ``rank``. ``best_option`` names the cheapest.
    """
    options = [option.model_dump() for option in request.options]
    results = compare_options(options)
    return CompareResponse(
        results=[CompareResultItem(**result) for result in results],
        best_option=results[0]["name"],
    )


# ─────────────────────────────────────────────────────────────────────
# Tool 4 — evaluate_project_health (EVM)
# ─────────────────────────────────────────────────────────────────────


@structured_errors
def evaluate_project_health(evm: EvmCalculateInput) -> EvmCalculateResponse:
    """Judge whether a project is on track, at risk, or off track, using EVM.

    Use when: you know the planned value, earned value, actual cost and total budget,
    and want the standard earned-value indices plus a plain-English health verdict.

    Args:
        evm: The four earned-value fundamentals, all in one currency:
            ``pv`` (Planned Value — budgeted cost of work scheduled by now),
            ``ev`` (Earned Value — budgeted cost of work actually completed),
            ``ac`` (Actual Cost — what was actually spent),
            ``bac`` (Budget at Completion — total planned budget, must be > 0).

    Returns:
        An ``EvmCalculateResponse`` with ``metrics`` — schedule (``sv``, ``spi``),
        cost (``cv``, ``cpi``), forecasts (``eac``, ``etc``, ``vac``, ``tcpi``) and
        ``percent_complete`` / ``percent_spent`` — and ``health`` (a coarse
        ``status`` of on_track / at_risk / off_track, the ``reasons``, and a one-line
        ``summary``). Indices are unitless ratios where 1.0 is on-plan; an index that
        is undefined (e.g. SPI when PV is 0) is reported as ``null``.
    """
    metrics = evm_metrics(pv=evm.pv, ev=evm.ev, ac=evm.ac, bac=evm.bac)
    signal = health_signal(spi=metrics["spi"], cpi=metrics["cpi"])
    return EvmCalculateResponse(
        metrics=EvmMetricsResult(**metrics),
        health=HealthResult(**signal),
    )


# ═════════════════════════════════════════════════════════════════════
# PARKED — not registered in v0.1 (see server.py)
# ═════════════════════════════════════════════════════════════════════
# `estimate_from_history` is the two-layer, calibration-driven estimator. It is
# parked for v0.1 under the same rationale that parked the Bayesian and
# Dirichlet-drift tools in the v0.1 MCP scoping Decision: the calibration is
# conservative and unvalidated (no field data yet), so its PMO story is not sharp
# enough to ship as a single-call LLM tool at the v0.1 quality bar. The code is
# kept intact, not deleted. Re-enable it (re-register in server.py, restore its
# tests) once the estimation_log data source exists to ground the Layer 2
# constants — earliest Sprint 10.
# ─────────────────────────────────────────────────────────────────────

# Layer 2 calibration constants. Conservative defaults agreed with CTO; to be
# tuned against field data before this tool ships.
_COMPLEXITY_M_UPLIFT = 0.4  # complexity_factor=1.0 lifts M by 40%
_NOVELTY_P_UPLIFT = 0.5  # novelty_factor=1.0 lifts the tail by 50%
_FAMILIARITY_MAX_SPREAD = 2.0  # familiarity=0 doubles the historical spread


def _resolve_insight_tags(
    insight_tags: dict[str, float] | None,
) -> list[InsightTag | tuple[InsightTag, float]] | None:
    """Convert ``{tag_name: severity}`` → ``[(InsightTag, severity), ...]``.

    Unknown tag names raise. Severities are clamped to ``[0.0, 1.0]`` by the
    underlying PERT helper.
    """
    if not insight_tags:
        return None
    resolved: list[InsightTag | tuple[InsightTag, float]] = []
    for name, severity in insight_tags.items():
        key = name.upper()
        if key not in DEFAULT_TAGS:
            available = ", ".join(sorted(DEFAULT_TAGS.keys()))
            raise ValueError(f"Unknown insight tag '{name}'. Available: {available}")
        resolved.append((DEFAULT_TAGS[key], severity))
    return resolved


def estimate_from_history(
    task_category: str,
    optimistic: float,
    past_actuals: list[float],
    team_familiarity: float = 0.5,
    complexity_factor: float = 0.5,
    novelty_factor: float = 0.5,
    insight_tags: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Estimate a task's duration by composing past actual durations with
    calibration knobs and insight tags.

    PARKED for v0.1 — see the section banner above. Kept intact for re-enablement.

    Use when: you have observed past durations for similar tasks and want a
    calibrated estimate, not a guess. Layer 2 (pre-PERT) translates history into M
    and P; Layer 1 (post-PERT) widens the tail via insight tags.

    **v0.1 calibration formula** — subject to revision once we have field data:

        base_M = median(past_actuals)
        base_spread = max(past_actuals) - base_M     # if len >= 2
                    = base_M * 0.3                   # if len == 1

        derived_M = base_M * (1 + complexity_factor * 0.4)

        familiarity_multiplier = 2.0 - team_familiarity   # ∈ [1.0, 2.0]
        novelty_multiplier = 1 + novelty_factor * 0.5
        derived_spread = base_spread * familiarity_multiplier * novelty_multiplier
        derived_P = derived_M + derived_spread

    Then ``calculate_task(optimistic, derived_M, derived_P, insight_tags)`` runs the
    standard PERT pipeline (Layer 1).

    Args:
        task_category: Short label for the task class (e.g. "auth-api"). Recorded for
            traceability; not used in the maths.
        optimistic: Human-supplied best-case duration. Acts as the floor.
        past_actuals: Observed durations of past tasks in this class. At least one.
        team_familiarity: 0.0 (entirely new team) — 1.0 (same team that ran all past
            tasks). Higher = narrower spread.
        complexity_factor: 0.0 (simpler than past) — 1.0 (much more complex). Higher
            = larger M and P.
        novelty_factor: 0.0 (familiar work) — 1.0 (entirely new territory). Higher =
            wider tail.
        insight_tags: Optional Layer 1 adjustments — same shape as the dict form used
            by the parked prototype.

    Returns:
        Dict with ``derived_most_likely``, ``derived_pessimistic``,
        ``textbook_estimate``, ``adjusted_estimate``, ``confidence``,
        ``layer2_adjustment``, ``layer1_adjustment``, ``data_quality``.
    """
    if not past_actuals:
        raise ValueError("past_actuals must contain at least one observation")
    for k, v in {
        "team_familiarity": team_familiarity,
        "complexity_factor": complexity_factor,
        "novelty_factor": novelty_factor,
    }.items():
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"{k} must be in [0.0, 1.0], got {v}")
    if optimistic < 0:
        raise ValueError(f"optimistic must be >= 0, got {optimistic}")
    if any(a < 0 for a in past_actuals):
        raise ValueError("past_actuals values must all be >= 0")

    # ── Layer 2: history → derived M and P ────────────────────────
    base_m = float(statistics.median(past_actuals))
    # One observation: fall back to a 30% spread heuristic so the tail isn't
    # collapsed to zero. With ≥ 2 observations we use the actual range.
    base_spread = max(past_actuals) - base_m if len(past_actuals) >= 2 else base_m * 0.3

    derived_m = base_m * (1 + complexity_factor * _COMPLEXITY_M_UPLIFT)

    familiarity_multiplier = _FAMILIARITY_MAX_SPREAD - team_familiarity
    novelty_multiplier = 1 + novelty_factor * _NOVELTY_P_UPLIFT
    derived_spread = base_spread * familiarity_multiplier * novelty_multiplier
    derived_p = derived_m + derived_spread

    # Optimistic floor: derived_m must be >= optimistic for PERT validation
    if derived_m < optimistic:
        derived_m = float(optimistic)
    if derived_p < derived_m:
        derived_p = derived_m

    # ── Layer 1: PERT + insight tags ──────────────────────────────
    pert_result = calculate_task(
        optimistic, derived_m, derived_p, _resolve_insight_tags(insight_tags)
    )

    textbook = pert_result["textbook"]
    adjusted = pert_result["adjusted"]
    primary = adjusted if adjusted is not None else textbook

    # PERT std_dev approximates a normal-tail; map to P85 ≈ μ + 1.04σ.
    p50 = round(primary["expected"], 2)
    p85 = round(primary["expected"] + 1.04 * primary["std_dev"], 2)

    n = len(past_actuals)
    if n >= 8:
        data_quality: Literal["low", "medium", "high"] = "high"
    elif n >= 3:
        data_quality = "medium"
    else:
        data_quality = "low"

    layer2_text = (
        f"Layer 2 (pre-PERT): {n} past actual(s), median={base_m:.2f}. "
        f"Adjusted by complexity={complexity_factor:.2f} → M={derived_m:.2f}; "
        f"team_familiarity={team_familiarity:.2f}, novelty={novelty_factor:.2f} "
        f"→ P={derived_p:.2f}."
    )

    if adjusted is not None:
        tag_summary = ", ".join(
            f"{t['name'].lower()}@{t['severity']:.2f}" for t in adjusted["tags_applied"]
        )
        layer1_text = (
            f"Layer 1 (post-PERT): tags [{tag_summary}] widen the pessimistic "
            f"tail (combined ×{adjusted['combined_multiplier']:.3f})."
        )
    else:
        layer1_text = "Layer 1 (post-PERT): no insight tags applied."

    return {
        "task_category": task_category,
        "derived_most_likely": round(derived_m, 2),
        "derived_pessimistic": round(derived_p, 2),
        "textbook_estimate": textbook,
        "adjusted_estimate": adjusted,
        "confidence": {"p50": p50, "p85": p85},
        "layer2_adjustment": layer2_text,
        "layer1_adjustment": layer1_text,
        "data_quality": data_quality,
        "calibration_version": "v0.1",
    }
