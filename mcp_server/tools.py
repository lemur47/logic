"""
MCP tool implementations.

Each function is registered as an MCP tool by `server.py`. Tools are
verb-noun named — the description states the *decision question*, not
the maths, because that's what helps an LLM pick the right one.

Imports flow: mcp_server/ → app.{module}.core (pure functions only).
We never import FastAPI or DB models here — the MCP server stays
runnable without uvicorn or the SQLite file.
"""

from __future__ import annotations

import math
import statistics
from typing import Any, Literal

from app.evm.core import HealthThresholds, evm_metrics, health_signal
from app.montecarlo.core import Task, simulate_schedule
from app.pert.core import DEFAULT_TAGS, InsightTag, calculate_task
from app.tco.core import compare_options

# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _resolve_insight_tags(
    insight_tags: dict[str, float] | None,
) -> list[InsightTag | tuple[InsightTag, float]] | None:
    """Convert {tag_name: severity} → [(InsightTag, severity), ...].

    Unknown tag names raise — better to fail loudly than silently apply
    nothing. Severities are clamped to [0.0, 1.0] by the underlying
    PERT helper.
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


# ─────────────────────────────────────────────────────────────────────
# Tool 1 — estimate_task_duration
# ─────────────────────────────────────────────────────────────────────


def estimate_task_duration(
    optimistic: float,
    most_likely: float,
    pessimistic: float,
    insight_tags: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Estimate how long a single task will take, with optional reality
    adjustments.

    Use when: you have a human three-point estimate and want the
    textbook PERT expected value plus an adjusted estimate that
    accounts for known frictions (fragmented communication, multiple
    stakeholders, hidden dependencies).

    Args:
        optimistic: Best-case duration (O). Must be >= 0.
        most_likely: Most probable duration (M). Must be >= O.
        pessimistic: Worst-case duration (P). Must be >= M.
        insight_tags: Optional mapping of tag name → severity (0.0-1.0).
            Names are case-insensitive. Available tags:
            FRAGMENTED_COMMUNICATION, MULTIPLE_STAKEHOLDERS,
            HIDDEN_DEPENDENCIES.

    Returns:
        Dict with `input`, `textbook` (PERT stats), and `adjusted`
        (PERT stats after tag application; None if no tags).
    """
    tags = _resolve_insight_tags(insight_tags)
    return calculate_task(optimistic, most_likely, pessimistic, tags)


# ─────────────────────────────────────────────────────────────────────
# Tool 2 — estimate_from_history (flagship, v0.1)
# ─────────────────────────────────────────────────────────────────────

# Layer 2 calibration constants. v0.1 — these multipliers are the
# conservative defaults agreed with CTO. Tune via field data.
_COMPLEXITY_M_UPLIFT = 0.4  # complexity_factor=1.0 lifts M by 40%
_NOVELTY_P_UPLIFT = 0.5  # novelty_factor=1.0 lifts the tail by 50%
_FAMILIARITY_MAX_SPREAD = 2.0  # familiarity=0 doubles the historical spread


def estimate_from_history(
    task_category: str,
    optimistic: float,
    past_actuals: list[float],
    team_familiarity: float = 0.5,
    complexity_factor: float = 0.5,
    novelty_factor: float = 0.5,
    insight_tags: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Estimate a task's duration by composing past actual durations
    with calibration knobs and insight tags.

    Use when: you have observed past durations for similar tasks and
    want a calibrated estimate, not a guess. This is the two-layer
    flagship — Layer 2 (pre-PERT) translates history into M and P;
    Layer 1 (post-PERT) widens the tail via insight tags.

    **v0.1 calibration formula** — subject to revision once we have
    field data:

        base_M = median(past_actuals)
        base_spread = max(past_actuals) - base_M     # if len >= 2
                    = base_M * 0.3                   # if len == 1

        derived_M = base_M * (1 + complexity_factor * 0.4)

        familiarity_multiplier = 2.0 - team_familiarity   # ∈ [1.0, 2.0]
        novelty_multiplier = 1 + novelty_factor * 0.5
        derived_spread = base_spread * familiarity_multiplier * novelty_multiplier
        derived_P = derived_M + derived_spread

    Then `calculate_task(optimistic, derived_M, derived_P, insight_tags)`
    runs the standard PERT pipeline (Layer 1).

    Args:
        task_category: Short label for the task class (e.g. "auth-api").
            Recorded in the response for traceability; not used in the
            maths.
        optimistic: Human-supplied best-case duration. Acts as the floor.
        past_actuals: Observed durations of past tasks in this class.
            At least one is required.
        team_familiarity: 0.0 (entirely new team) — 1.0 (same team that
            ran all past tasks). Higher = narrower spread.
        complexity_factor: 0.0 (simpler than past) — 1.0 (much more
            complex). Higher = larger M and P.
        novelty_factor: 0.0 (familiar work) — 1.0 (entirely new
            territory). Higher = wider tail.
        insight_tags: Optional Layer 1 adjustments — same shape as
            `estimate_task_duration`'s.

    Returns:
        Dict with `derived_most_likely`, `derived_pessimistic`,
        `textbook_estimate`, `adjusted_estimate`, `confidence`,
        `layer2_adjustment`, `layer1_adjustment`, `data_quality`.
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


# ─────────────────────────────────────────────────────────────────────
# Tool 3 — identify_schedule_risk
# ─────────────────────────────────────────────────────────────────────


def identify_schedule_risk(
    tasks: list[dict[str, Any]],
    num_simulations: int = 10_000,
    seed: int | None = None,
) -> dict[str, Any]:
    """Rank tasks by their contribution to schedule risk.

    Use when: you have a network of tasks with three-point estimates
    and want to know which ones are most likely to drive the project
    over schedule. Runs Monte Carlo simulation and combines critical-path
    frequency with PERT variance into a single risk score.

    Args:
        tasks: List of task dicts. Each must have `name`, `optimistic`,
            `most_likely`, `pessimistic`. Optional `depends_on` is a list
            of predecessor task names.
        num_simulations: Iterations to run (100 - 1,000,000). Default 10,000.
        seed: Optional random seed for reproducible runs.

    Returns:
        Dict with `ranked_risks` (tasks ordered by risk_score, descending),
        `project_percentiles` (P50/P75/P85/P95 of total duration), and
        `summary` (one-line plain-English verdict).
    """
    if not tasks:
        raise ValueError("tasks must contain at least one task")

    core_tasks = [
        Task(
            name=t["name"],
            optimistic=t["optimistic"],
            most_likely=t["most_likely"],
            pessimistic=t["pessimistic"],
            depends_on=tuple(t.get("depends_on", [])),
        )
        for t in tasks
    ]
    result = simulate_schedule(core_tasks, n_simulations=num_simulations, seed=seed)

    ranked: list[dict[str, Any]] = []
    for t in core_tasks:
        cp_freq = result.critical_path_frequency.get(t.name, 0.0)
        # Risk score: critical-path probability × PERT variance — simple and
        # interpretable. A task that's always on the critical path with a
        # tight estimate scores low; a task that's sometimes critical with a
        # wide spread scores high.
        score = cp_freq * (t.pert_std_dev**2)
        ranked.append(
            {
                "name": t.name,
                "critical_path_frequency": round(cp_freq, 4),
                "pert_variance": round(t.pert_std_dev**2, 4),
                "risk_score": round(score, 4),
            }
        )
    ranked.sort(key=lambda r: r["risk_score"], reverse=True)
    for i, r in enumerate(ranked):
        r["rank"] = i + 1

    p50, p85 = result.percentiles["P50"], result.percentiles["P85"]
    summary = (
        f"P50 duration {p50}, P85 {p85}. "
        f"Top risk: {ranked[0]['name']} (score {ranked[0]['risk_score']})."
        if ranked
        else f"P50 duration {p50}, P85 {p85}."
    )

    return {
        "ranked_risks": ranked,
        "project_percentiles": result.percentiles,
        "summary": summary,
    }


# ─────────────────────────────────────────────────────────────────────
# Tool 4 — compare_investment_options
# ─────────────────────────────────────────────────────────────────────


def compare_investment_options(
    options: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare investment options on NPV-adjusted total cost of ownership.

    Use when: you have two or more options (vendors, platforms, tools)
    each with initial price + lifetime + recurring costs, and want to
    rank them on real lifetime cost rather than sticker price.

    Args:
        options: List of option dicts. Each must have `name`,
            `initial_price`, `useful_life_years`. Optional fields:
            `residual_value`, `annual_maintenance`, `annual_operating_cost`,
            `discount_rate` (default 0.03).

    Returns:
        Dict with `ranked_options` (sorted by annual cost ascending) and
        `summary` (plain-English verdict including delta vs. cheapest).
    """
    if len(options) < 2:
        raise ValueError("compare_investment_options requires at least 2 options")
    ranked = compare_options(options)
    cheapest = ranked[0]
    summary = (
        f"Cheapest annual cost: {cheapest['name']} "
        f"(${cheapest['annual_cost']:.2f}/yr over {cheapest['useful_life_years']}y)."
    )
    if len(ranked) > 1:
        runner_up = ranked[1]
        delta = runner_up["annual_cost"] - cheapest["annual_cost"]
        summary += (
            f" {runner_up['name']} costs ${delta:.2f}/yr more (${runner_up['annual_cost']:.2f}/yr)."
        )
    return {"ranked_options": ranked, "summary": summary}


# ─────────────────────────────────────────────────────────────────────
# Tool 5 — evaluate_project_health
# ─────────────────────────────────────────────────────────────────────


def evaluate_project_health(
    planned_value: float,
    earned_value: float,
    actual_cost: float,
    budget_at_completion: float,
) -> dict[str, Any]:
    """Evaluate project health from EVM fundamentals.

    Use when: you have planned value (PV), earned value (EV), actual
    cost (AC), and the total budget (BAC), and want SPI/CPI/EAC plus
    a plain-English health verdict.

    Args:
        planned_value: How much work should be done by now (in budget terms).
        earned_value: How much work is actually done (valued at planned rates).
        actual_cost: What we actually spent on the work performed.
        budget_at_completion: Total planned budget.

    Returns:
        Dict with `metrics` (SPI/CPI/EAC/ETC/VAC/TCPI/percent_complete),
        `health` (status + reasons + summary), and `verdict` (one-line
        plain-English roll-up).
    """
    metrics = evm_metrics(
        pv=planned_value, ev=earned_value, ac=actual_cost, bac=budget_at_completion
    )
    # health_signal needs SPI and CPI; cap inf for the signal call so a
    # zero-PV / zero-AC corner case still produces a usable status.
    spi_for_signal = metrics["spi"] if math.isfinite(metrics["spi"]) else 0.0
    cpi_for_signal = metrics["cpi"] if math.isfinite(metrics["cpi"]) else 0.0
    health = health_signal(spi=spi_for_signal, cpi=cpi_for_signal, thresholds=HealthThresholds())
    verdict = (
        f"{health['status'].upper()} — SPI {metrics['spi']}, CPI {metrics['cpi']}, "
        f"EAC ${metrics['eac']} (BAC ${budget_at_completion:.2f})."
    )
    return {"metrics": metrics, "health": health, "verdict": verdict}
