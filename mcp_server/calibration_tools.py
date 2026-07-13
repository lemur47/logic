"""
Calibration-memory MCP tools (opt-in — registered only when ``PMORUN_DB`` is set).

These tools close the estimation feedback loop the four v0.1 tools cannot: record
a three-point estimate, later record what actually happened, and let conjugate
Bayesian updating (``app.bayesian.core``) turn the accumulated (estimated, actual)
pairs into a calibrated delay factor. They also re-enable the previously parked
``estimate_from_history`` estimator, whose stated re-enablement condition — "once
the estimation_log data source exists to ground the Layer 2 constants" — this
module fulfils.

Same design rules as ``tools.py``: thin adapters over pure core functions,
verb-noun names, descriptions leading with the decision question, and
``@structured_errors`` on every tool. Persistence lives entirely in
``storage.py``; nothing here holds state between calls.
"""

import json

from app.bayesian.core import Observation, Prior, adjust_estimate, update_belief
from app.pert.core import calculate_task

from . import storage, tools
from .errors import ToolValidationError, structured_errors


def _require_db() -> str:
    """The log path — present by construction when these tools are registered,
    but guarded anyway so a mid-session unset fails with a clear message."""
    path = storage.db_path()
    if path is None:
        raise ToolValidationError(
            f"Calibration memory is not enabled: set the {storage.ENV_VAR} "
            "environment variable to a writable file path and restart the server."
        )
    return path


# ─────────────────────────────────────────────────────────────────────
# Tool 5 — record_estimate
# ─────────────────────────────────────────────────────────────────────


@structured_errors
def record_estimate(
    task_category: str,
    optimistic: float,
    most_likely: float,
    pessimistic: float,
    unit: str = "sessions",
    description: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Log a three-point estimate so it can later be compared with what actually
    happened.

    Use when: you are committing to an estimate (task, work item, sprint line)
    and want it captured for the calibration loop — every recorded estimate that
    later receives an actual becomes one observation for
    ``summarise_calibration`` and one data point for ``estimate_from_history``.

    Args:
        task_category: Short label for the task class (e.g. "content", "infra",
            "module-dev"). Calibration is learned per category, so consistent
            labels matter more than precise ones.
        optimistic: Best-case duration (O). Same unit as the other two.
        most_likely: Most-likely duration (M), with ``O <= M <= P``.
        pessimistic: Worst-case duration (P).
        unit: The time unit the estimates are denominated in. Defaults to
            "sessions" (one focused working context); "days" and "hours" are
            equally valid — the log stores, it does not convert.
        description: Optional free-text note on what is being estimated.
        tags: Optional labels stored alongside (e.g. friction markers).

    Returns:
        Dict with ``estimate_id`` (use it in ``record_actual``), the echoed
        inputs, the computed ``pert_expected`` and ``pert_std_dev``, and
        ``estimated_at`` (ISO-8601 UTC).
    """
    path = _require_db()
    result = calculate_task(optimistic, most_likely, pessimistic)
    expected = result["textbook"]["expected"]
    std_dev = result["textbook"]["std_dev"]

    estimate_id, recorded_at = storage.insert_estimate(
        path,
        task_category=task_category,
        optimistic=optimistic,
        most_likely=most_likely,
        pessimistic=pessimistic,
        pert_expected=expected,
        unit=unit,
        description=description,
        tags=json.dumps(tags) if tags else None,
    )
    return {
        "estimate_id": estimate_id,
        "task_category": task_category,
        "optimistic": optimistic,
        "most_likely": most_likely,
        "pessimistic": pessimistic,
        "pert_expected": expected,
        "pert_std_dev": std_dev,
        "unit": unit,
        "estimated_at": recorded_at,
    }


# ─────────────────────────────────────────────────────────────────────
# Tool 6 — record_actual
# ─────────────────────────────────────────────────────────────────────


@structured_errors
def record_actual(estimate_id: int, actual: float) -> dict:
    """Record what a previously estimated task actually took, closing one
    feedback-loop observation.

    Use when: an estimated task is done and you know its real duration. Calling
    again with the same ``estimate_id`` overwrites the actual (corrections are
    allowed; the log keeps the latest value).

    Args:
        estimate_id: The id returned by ``record_estimate``.
        actual: The observed duration, in the same unit the estimate used.
            Must be >= 0.

    Returns:
        Dict with the full log row (category, O/M/P, ``pert_expected``, unit,
        timestamps) plus ``delay_factor`` — ``actual / pert_expected``, where
        1.0 means the estimate was exactly right and 2.0 means it took twice
        as long as expected.
    """
    path = _require_db()
    if actual < 0:
        raise ToolValidationError(f"actual must be >= 0, got {actual}")
    row = storage.set_actual(path, estimate_id, actual)
    return {
        "estimate_id": row["id"],
        "task_category": row["task_category"],
        "unit": row["unit"],
        "optimistic": row["optimistic"],
        "most_likely": row["most_likely"],
        "pessimistic": row["pessimistic"],
        "pert_expected": row["pert_expected"],
        "actual": row["actual"],
        "delay_factor": round(row["actual"] / row["pert_expected"], 4),
        "estimated_at": row["estimated_at"],
        "actual_recorded_at": row["actual_recorded_at"],
    }


# ─────────────────────────────────────────────────────────────────────
# Tool 7 — summarise_calibration
# ─────────────────────────────────────────────────────────────────────


@structured_errors
def summarise_calibration(
    task_category: str | None = None,
    pert_expected: float | None = None,
    observation_noise: float = 0.15,
) -> dict:
    """Learn the systematic estimation bias from the recorded history, and
    optionally apply it to a new estimate.

    Use when: you want to know "how wrong are our estimates, and in which
    direction?" — or you have a fresh PERT expected value and want it adjusted
    by the learnt bias before committing to it.

    Runs conjugate normal-normal Bayesian updating (``app.bayesian.core``) over
    every completed (estimated, actual) pair in the log, starting from the
    uninformative prior N(1.0, 0.25). The posterior mean is the calibrated
    delay factor: 1.0 = estimates are unbiased, 2.0 = things take twice as
    long as estimated.

    Args:
        task_category: Restrict learning to one category. Omit to learn from
            the whole log (categories differ — prefer per-category once each
            has a few observations).
        pert_expected: Optional fresh PERT expected duration. When given, the
            response includes ``adjusted_estimate`` — the estimate multiplied
            by the posterior delay factor, with 68%/95% bands.
        observation_noise: Assumed scatter of individual delay factors around
            the true bias (sigma; default 0.15 = ±15%).

    Returns:
        Dict with ``n_observations``, ``delay_factor`` (posterior mean),
        ``credible_interval_68`` / ``credible_interval_95``, ``confidence``
        (none/low/medium/high), the per-category observation counts, and —
        when ``pert_expected`` was supplied — ``adjusted_estimate``.
    """
    path = _require_db()
    pairs = storage.completed_pairs(path, task_category)

    observations = [
        Observation(
            estimated=pair["pert_expected"],
            actual=pair["actual"],
            context=pair["task_category"],
        )
        for pair in pairs
    ]
    posterior = update_belief(Prior(), observations, observation_noise=observation_noise)

    # adjust_estimate(1.0, posterior) yields the posterior itself in estimate
    # space — used here only for its confidence label so the wording stays
    # single-sourced in app.bayesian.core.
    confidence = adjust_estimate(1.0, posterior)["confidence"]

    category_counts: dict[str, int] = {}
    for pair in pairs:
        category_counts[pair["task_category"]] = category_counts.get(pair["task_category"], 0) + 1

    summary = {
        "task_category": task_category,
        "n_observations": posterior.n_observations,
        "delay_factor": posterior.mean,
        "credible_interval_68": list(posterior.credible_interval_68),
        "credible_interval_95": list(posterior.credible_interval_95),
        "confidence": confidence,
        "observations_by_category": category_counts,
    }
    if pert_expected is not None:
        if pert_expected <= 0:
            raise ToolValidationError(f"pert_expected must be > 0, got {pert_expected}")
        summary["adjusted_estimate"] = adjust_estimate(pert_expected, posterior)
    return summary


# ─────────────────────────────────────────────────────────────────────
# Tool 8 — estimate_from_history (unparked; grounded in the log)
# ─────────────────────────────────────────────────────────────────────


@structured_errors
def estimate_from_history(
    task_category: str,
    optimistic: float,
    team_familiarity: float = 0.5,
    complexity_factor: float = 0.5,
    novelty_factor: float = 0.5,
    insight_tags: dict[str, float] | None = None,
    past_actuals: list[float] | None = None,
) -> dict:
    """Estimate a task's duration from past actual durations plus calibration
    knobs — the two-layer, history-grounded estimator.

    Use when: the log already holds actuals for this task category (recorded via
    ``record_estimate`` + ``record_actual``) and you want a calibrated estimate
    derived from them rather than a fresh guess. Layer 2 (pre-PERT) translates
    the history into M and P; Layer 1 (post-PERT) widens the tail via insight
    tags.

    Args:
        task_category: The task class whose recorded actuals ground the
            estimate. Must match the labels used in ``record_estimate``.
        optimistic: Human-supplied best-case duration; acts as the floor.
        team_familiarity: 0.0 (entirely new team) — 1.0 (same team as the past
            tasks). Higher = narrower spread.
        complexity_factor: 0.0 (simpler than past work) — 1.0 (much more
            complex). Higher = larger M and P.
        novelty_factor: 0.0 (familiar territory) — 1.0 (entirely new). Higher =
            wider tail.
        insight_tags: Optional ``{tag_name: severity}`` Layer 1 adjustments
            (severity in [0, 1]; known names as in ``estimate_task_duration``).
        past_actuals: Explicit past durations. Normally omit — the tool reads
            the recorded actuals for ``task_category`` from the log. Supply
            only to override the log (e.g. for a what-if).

    Returns:
        Dict with ``derived_most_likely`` / ``derived_pessimistic``, textbook
        and tag-adjusted PERT estimates, ``confidence`` (p50/p85),
        human-readable Layer 1/2 adjustment notes, and ``data_quality``
        (low/medium/high by observation count).
    """
    if past_actuals is None:
        path = _require_db()
        past_actuals = storage.actuals_for_category(path, task_category)
        if not past_actuals:
            raise ToolValidationError(
                f"No recorded actuals for category '{task_category}'. Record at "
                "least one completed estimate (record_estimate + record_actual) "
                "or pass past_actuals explicitly."
            )
    return tools.estimate_from_history(
        task_category=task_category,
        optimistic=optimistic,
        past_actuals=past_actuals,
        team_familiarity=team_familiarity,
        complexity_factor=complexity_factor,
        novelty_factor=novelty_factor,
        insight_tags=insight_tags,
    )
