"""
PERT core calculation logic.
Pure functions - no dependencies on FastAPI or SQLAlchemy.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class InsightTag:
    """A composable multiplier on the pessimistic estimate.

    Tags encode "reality adjustments" — factors that consistently cause estimates
    to overshoot in practice. Each tag defines a range of multipliers; severity
    (0.0–1.0) interpolates between min and max.
    """

    name: str
    description: str
    min_multiplier: float
    max_multiplier: float


FRAGMENTED_COMMUNICATION = InsightTag(
    name="FRAGMENTED_COMMUNICATION",
    description="Chat/meetings/manual workflows increase overhead",
    min_multiplier=1.1,
    max_multiplier=1.5,
)

MULTIPLE_STAKEHOLDERS = InsightTag(
    name="MULTIPLE_STAKEHOLDERS",
    description="Misaligned interests across orgs (strategic, political)",
    min_multiplier=1.15,
    max_multiplier=2.0,
)

HIDDEN_DEPENDENCIES = InsightTag(
    name="HIDDEN_DEPENDENCIES",
    description="Undocumented task relationships, upstream blockers",
    min_multiplier=1.1,
    max_multiplier=1.5,
)

DEFAULT_TAGS: dict[str, InsightTag] = {
    "FRAGMENTED_COMMUNICATION": FRAGMENTED_COMMUNICATION,
    "MULTIPLE_STAKEHOLDERS": MULTIPLE_STAKEHOLDERS,
    "HIDDEN_DEPENDENCIES": HIDDEN_DEPENDENCIES,
}


def _apply_tags(
    pessimistic: float,
    tags: list[InsightTag | tuple[InsightTag, float]],
) -> tuple[float, list[dict], float]:
    """Apply insight tags to the pessimistic estimate.

    Returns:
        Tuple of (adjusted_pessimistic, tags_applied_list, combined_multiplier).
    """
    tags_applied = []
    combined_multiplier = 1.0

    for entry in tags:
        if isinstance(entry, tuple):
            tag, severity = entry
        else:
            tag = entry
            severity = 0.5

        if not 0.0 <= severity <= 1.0:
            raise ValueError(f"Severity must be between 0.0 and 1.0, got {severity}")

        effective = tag.min_multiplier + severity * (tag.max_multiplier - tag.min_multiplier)
        combined_multiplier *= effective
        tags_applied.append(
            {
                "name": tag.name,
                "severity": severity,
                "multiplier": round(effective, 4),
            }
        )

    adjusted_p = pessimistic * combined_multiplier
    return adjusted_p, tags_applied, combined_multiplier


def _pert_stats(optimistic: float, most_likely: float, pessimistic: float) -> dict:
    """Calculate PERT statistics from three-point estimates."""
    expected = (optimistic + 4 * most_likely + pessimistic) / 6
    std_dev = (pessimistic - optimistic) / 6
    variance = std_dev**2

    return {
        "expected": expected,
        "std_dev": std_dev,
        "variance": variance,
        "range_68": [expected - std_dev, expected + std_dev],
        "range_95": [expected - 2 * std_dev, expected + 2 * std_dev],
        "range_99": [expected - 3 * std_dev, expected + 3 * std_dev],
    }


def _round_stats(stats: dict) -> dict:
    """Round all numeric values in a stats dict to 2 decimal places."""
    return {
        "expected": round(stats["expected"], 2),
        "std_dev": round(stats["std_dev"], 2),
        "variance": round(stats["variance"], 2),
        "range_68": [round(stats["range_68"][0], 2), round(stats["range_68"][1], 2)],
        "range_95": [round(stats["range_95"][0], 2), round(stats["range_95"][1], 2)],
        "range_99": [round(stats["range_99"][0], 2), round(stats["range_99"][1], 2)],
    }


def calculate_task(
    optimistic: float,
    most_likely: float,
    pessimistic: float,
    tags: list[InsightTag | tuple[InsightTag, float]] | None = None,
) -> dict:
    """Calculate PERT estimate for a single task, with optional reality adjustments.

    Args:
        optimistic: Best-case duration (O).
        most_likely: Most probable duration (M).
        pessimistic: Worst-case duration (P).
        tags: Optional list of InsightTags or (InsightTag, severity) tuples.

    Returns:
        dict with "input", "textbook", and "adjusted" (None if no tags).

    Raises:
        ValueError: If O > M, M > P, or any value < 0.
    """
    if optimistic < 0 or most_likely < 0 or pessimistic < 0:
        raise ValueError("All estimates must be non-negative")
    if optimistic > most_likely:
        raise ValueError(f"Optimistic ({optimistic}) cannot exceed most likely ({most_likely})")
    if most_likely > pessimistic:
        raise ValueError(f"Most likely ({most_likely}) cannot exceed pessimistic ({pessimistic})")

    textbook = _pert_stats(optimistic, most_likely, pessimistic)

    adjusted = None
    if tags:
        adjusted_p, tags_applied, combined_multiplier = _apply_tags(pessimistic, tags)
        adj_stats = _pert_stats(optimistic, most_likely, adjusted_p)
        adjusted = _round_stats(adj_stats)
        adjusted["pessimistic"] = round(adjusted_p, 2)
        adjusted["tags_applied"] = tags_applied
        adjusted["combined_multiplier"] = round(combined_multiplier, 4)

    return {
        "input": {
            "optimistic": optimistic,
            "most_likely": most_likely,
            "pessimistic": pessimistic,
        },
        "textbook": _round_stats(textbook),
        "adjusted": adjusted,
    }


def calculate_project(tasks: list[dict]) -> dict:
    """Aggregate PERT estimates across multiple tasks.

    Args:
        tasks: List of dicts, each with "name", "optimistic", "most_likely",
            "pessimistic", and optional "tags".

    Returns:
        dict with "tasks", "project" (textbook aggregate),
        and "adjusted_project" (aggregate with tags, None if no task has tags).

    Raises:
        ValueError: If tasks list is empty.
    """
    if not tasks:
        raise ValueError("Tasks list cannot be empty")

    task_results = []
    has_any_tags = False

    for task in tasks:
        result = calculate_task(
            optimistic=task["optimistic"],
            most_likely=task["most_likely"],
            pessimistic=task["pessimistic"],
            tags=task.get("tags"),
        )
        result["name"] = task["name"]
        task_results.append(result)
        if result["adjusted"] is not None:
            has_any_tags = True

    # Aggregate textbook stats (no mid-computation rounding)
    raw_results = []
    for task in tasks:
        raw_results.append(
            _pert_stats(task["optimistic"], task["most_likely"], task["pessimistic"])
        )

    project_expected = sum(r["expected"] for r in raw_results)
    project_variance = sum(r["variance"] for r in raw_results)
    project_std_dev = math.sqrt(project_variance)

    project = {
        "expected": round(project_expected, 2),
        "std_dev": round(project_std_dev, 2),
        "variance": round(project_variance, 2),
        "range_68": [
            round(project_expected - project_std_dev, 2),
            round(project_expected + project_std_dev, 2),
        ],
        "range_95": [
            round(project_expected - 2 * project_std_dev, 2),
            round(project_expected + 2 * project_std_dev, 2),
        ],
        "range_99": [
            round(project_expected - 3 * project_std_dev, 2),
            round(project_expected + 3 * project_std_dev, 2),
        ],
    }

    adjusted_project = None
    if has_any_tags:
        adj_raw_results = []
        for task in tasks:
            tags = task.get("tags")
            p = task["pessimistic"]
            if tags:
                p, _, _ = _apply_tags(p, tags)
            adj_raw_results.append(_pert_stats(task["optimistic"], task["most_likely"], p))

        adj_expected = sum(r["expected"] for r in adj_raw_results)
        adj_variance = sum(r["variance"] for r in adj_raw_results)
        adj_std_dev = math.sqrt(adj_variance)

        adjusted_project = {
            "expected": round(adj_expected, 2),
            "std_dev": round(adj_std_dev, 2),
            "variance": round(adj_variance, 2),
            "range_68": [
                round(adj_expected - adj_std_dev, 2),
                round(adj_expected + adj_std_dev, 2),
            ],
            "range_95": [
                round(adj_expected - 2 * adj_std_dev, 2),
                round(adj_expected + 2 * adj_std_dev, 2),
            ],
            "range_99": [
                round(adj_expected - 3 * adj_std_dev, 2),
                round(adj_expected + 3 * adj_std_dev, 2),
            ],
        }

    return {
        "tasks": task_results,
        "project": project,
        "adjusted_project": adjusted_project,
    }
