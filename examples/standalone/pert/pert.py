"""
PERT Estimator - Standalone Version

Reality-adjusted project estimation using PERT (Program Evaluation and Review Technique)
with composable insight tags that widen the pessimistic tail based on consulting experience.

Author: lemur47
License: MIT
Version: 1.0.0

Dependencies: matplotlib (optional for visualize_estimate)
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

    Args:
        name: Short identifier for the tag.
        description: Human-readable explanation of why this factor matters.
        min_multiplier: Multiplier at severity 0.0 (mild case).
        max_multiplier: Multiplier at severity 1.0 (severe case).

    Example:
        >>> tag = InsightTag("TECH_DEBT", "Legacy code drag", 1.1, 1.4)
        >>> # Use at default severity (0.5): effective multiplier = 1.25
    """

    name: str
    description: str
    min_multiplier: float
    max_multiplier: float


# ============================================================================
# Predefined Insight Tags
# ============================================================================

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


# ============================================================================
# Core Functions
# ============================================================================


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


def estimate_task(
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
            InsightTag alone uses default severity 0.5.
            Severity is a float between 0.0 (mild) and 1.0 (severe).

    Returns:
        dict: Contains "input", "textbook", and "adjusted" (None if no tags).

    Raises:
        ValueError: If O > M, M > P, or any value < 0.

    Example:
        >>> result = estimate_task(5, 10, 20)
        >>> print(f"Expected: {result['textbook']['expected']} days")
        Expected: 10.83 days
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


def estimate_project(tasks: list[dict]) -> dict:
    """Aggregate PERT estimates across multiple tasks.

    Uses standard PERT aggregation: project expected = sum of task expected values,
    project variance = sum of task variances. This assumes task independence.

    NOTE: Variance summation assumes tasks are independent. In practice, insight tags
    like FRAGMENTED_COMMUNICATION and MULTIPLE_STAKEHOLDERS often create correlated
    delays across tasks. Modelling covariance between tasks is a future enhancement.

    Args:
        tasks: List of dicts, each with "name", "optimistic", "most_likely",
            "pessimistic", and optional "tags".

    Returns:
        dict: Contains "tasks" (individual results), "project" (textbook aggregate),
            and "adjusted_project" (aggregate with tags, None if no task has tags).

    Raises:
        ValueError: If tasks list is empty.

    Example:
        >>> project = estimate_project([
        ...     {"name": "Design", "optimistic": 3, "most_likely": 5, "pessimistic": 10},
        ...     {"name": "Build", "optimistic": 10, "most_likely": 15, "pessimistic": 30},
        ... ])
        >>> print(f"Project expected: {project['project']['expected']} days")
    """
    if not tasks:
        raise ValueError("Tasks list cannot be empty")

    task_results = []
    has_any_tags = False

    for task in tasks:
        result = estimate_task(
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


def visualize_estimate(result: dict, save_path: str | None = None):
    """Create a horizontal range chart comparing textbook vs adjusted estimates.

    Shows optimistic, expected, and pessimistic as points with confidence bands.
    If adjusted data exists, displays both side by side for comparison.

    Args:
        result: Output from estimate_task() or estimate_project().
        save_path: Path to save figure. If None, displays interactively.

    Returns:
        matplotlib.figure.Figure: The created figure.

    Raises:
        ImportError: If matplotlib is not installed.

    Example:
        >>> result = estimate_task(5, 10, 20, tags=[FRAGMENTED_COMMUNICATION])
        >>> fig = visualize_estimate(result, save_path="pert_estimate.png")
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError(
            "matplotlib is required for visualize_estimate(). Install with: pip install matplotlib"
        ) from None

    # Determine if this is a single task or project result
    if "tasks" in result:
        return _visualize_project(result, save_path, plt)
    else:
        return _visualize_task(result, save_path, plt)


def _visualize_task(result, save_path, plt):
    """Visualize a single task estimate."""
    fig, ax = plt.subplots(figsize=(12, 4))

    y_positions = []
    y_labels = []
    y = 0

    textbook = result["textbook"]
    inp = result["input"]

    # Textbook estimate
    ax.barh(
        y,
        textbook["range_95"][1] - textbook["range_95"][0],
        left=textbook["range_95"][0],
        height=0.3,
        color="steelblue",
        alpha=0.3,
        label="95% CI",
    )
    ax.barh(
        y,
        textbook["range_68"][1] - textbook["range_68"][0],
        left=textbook["range_68"][0],
        height=0.3,
        color="steelblue",
        alpha=0.5,
        label="68% CI",
    )
    ax.plot(inp["optimistic"], y, "g^", markersize=10, label="Optimistic")
    ax.plot(textbook["expected"], y, "ko", markersize=8, label="Expected")
    ax.plot(inp["pessimistic"], y, "rv", markersize=10, label="Pessimistic")
    y_positions.append(y)
    y_labels.append("Textbook")

    if result["adjusted"]:
        y -= 1
        adjusted = result["adjusted"]
        ax.barh(
            y,
            adjusted["range_95"][1] - adjusted["range_95"][0],
            left=adjusted["range_95"][0],
            height=0.3,
            color="coral",
            alpha=0.3,
        )
        ax.barh(
            y,
            adjusted["range_68"][1] - adjusted["range_68"][0],
            left=adjusted["range_68"][0],
            height=0.3,
            color="coral",
            alpha=0.5,
        )
        ax.plot(inp["optimistic"], y, "g^", markersize=10)
        ax.plot(adjusted["expected"], y, "ko", markersize=8)
        ax.plot(adjusted["pessimistic"], y, "rv", markersize=10)
        y_positions.append(y)
        y_labels.append("Adjusted")

    ax.set_yticks(y_positions)
    ax.set_yticklabels(y_labels)
    ax.set_xlabel("Duration", fontsize=10)
    ax.set_title("PERT Estimate: Textbook vs Reality-Adjusted", fontsize=12, fontweight="bold")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(axis="x", alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"Figure saved to: {save_path}")
    else:
        plt.show()

    return fig


def _visualize_project(result, save_path, plt):
    """Visualize a project estimate with multiple tasks."""
    tasks = result["tasks"]
    has_adjusted = result["adjusted_project"] is not None

    fig, ax = plt.subplots(figsize=(14, max(4, len(tasks) * 1.5)))

    y = 0
    y_positions = []
    y_labels = []

    for task in reversed(tasks):
        textbook = task["textbook"]

        # Textbook
        ax.barh(
            y,
            textbook["range_95"][1] - textbook["range_95"][0],
            left=textbook["range_95"][0],
            height=0.3,
            color="steelblue",
            alpha=0.3,
        )
        ax.barh(
            y,
            textbook["range_68"][1] - textbook["range_68"][0],
            left=textbook["range_68"][0],
            height=0.3,
            color="steelblue",
            alpha=0.5,
        )
        ax.plot(textbook["expected"], y, "ko", markersize=6)
        y_positions.append(y)
        y_labels.append(f"{task['name']} (textbook)")

        if has_adjusted:
            y += 1
            adjusted = task["adjusted"] if task["adjusted"] else task["textbook"]
            ax.barh(
                y,
                adjusted["range_95"][1] - adjusted["range_95"][0],
                left=adjusted["range_95"][0],
                height=0.3,
                color="coral",
                alpha=0.3,
            )
            ax.barh(
                y,
                adjusted["range_68"][1] - adjusted["range_68"][0],
                left=adjusted["range_68"][0],
                height=0.3,
                color="coral",
                alpha=0.5,
            )
            ax.plot(adjusted["expected"], y, "ko", markersize=6)
            y_positions.append(y)
            y_labels.append(f"{task['name']} (adjusted)")

        y += 2

    ax.set_yticks(y_positions)
    ax.set_yticklabels(y_labels)
    ax.set_xlabel("Duration", fontsize=10)
    ax.set_title("PERT Project Estimate", fontsize=12, fontweight="bold")
    ax.grid(axis="x", alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"Figure saved to: {save_path}")
    else:
        plt.show()

    return fig


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("PERT Estimator - Standalone Version")
    print("=" * 70)

    # Example 1: Simple textbook PERT
    print("\n[Example 1] Single Task - Textbook PERT")
    print("-" * 70)

    result = estimate_task(5, 10, 20)
    tb = result["textbook"]

    print(f"Estimates:        O={5}, M={10}, P={20} days")
    print(f"\nExpected:         {tb['expected']} days")
    print(f"Std Deviation:    {tb['std_dev']} days")
    print(f"68% Confidence:   [{tb['range_68'][0]}, {tb['range_68'][1]}] days")
    print(f"95% Confidence:   [{tb['range_95'][0]}, {tb['range_95'][1]}] days")
    print(f"99.7% Confidence: [{tb['range_99'][0]}, {tb['range_99'][1]}] days")

    # Example 2: With reality adjustments
    print("\n\n[Example 2] Single Task - Reality Adjusted")
    print("-" * 70)

    result = estimate_task(
        5,
        10,
        20,
        tags=[
            (FRAGMENTED_COMMUNICATION, 0.8),
            (MULTIPLE_STAKEHOLDERS, 0.6),
        ],
    )
    tb = result["textbook"]
    adj = result["adjusted"]

    print(f"Estimates:        O={5}, M={10}, P={20} days")
    print(f"Tags applied:     {len(adj['tags_applied'])}")
    for tag in adj["tags_applied"]:
        print(f"  - {tag['name']} (severity={tag['severity']}, multiplier={tag['multiplier']})")
    print(f"Combined mult:    {adj['combined_multiplier']}")
    print(f"\n{'':18s} {'Textbook':>10s}  {'Adjusted':>10s}  {'Gap':>8s}")
    print(
        f"  Pessimistic:    {20:10.2f}  {adj['pessimistic']:10.2f}  {adj['pessimistic'] - 20:+8.2f}"
    )
    print(
        f"  Expected:       {tb['expected']:10.2f}  {adj['expected']:10.2f}  "
        f"{adj['expected'] - tb['expected']:+8.2f}"
    )
    print(
        f"  Std Dev:        {tb['std_dev']:10.2f}  {adj['std_dev']:10.2f}  "
        f"{adj['std_dev'] - tb['std_dev']:+8.2f}"
    )
    print(
        f"  95% range:      [{tb['range_95'][0]:.2f}, {tb['range_95'][1]:.2f}]"
        f"  [{adj['range_95'][0]:.2f}, {adj['range_95'][1]:.2f}]"
    )

    # Example 3: Project aggregation
    print("\n\n[Example 3] Project Aggregation")
    print("-" * 70)

    project = estimate_project(
        [
            {"name": "Design", "optimistic": 3, "most_likely": 5, "pessimistic": 10},
            {
                "name": "Build",
                "optimistic": 10,
                "most_likely": 15,
                "pessimistic": 30,
                "tags": [FRAGMENTED_COMMUNICATION],
            },
            {"name": "Test", "optimistic": 2, "most_likely": 4, "pessimistic": 8},
        ]
    )

    print("Tasks:")
    for task in project["tasks"]:
        tb = task["textbook"]
        tag_info = ""
        if task["adjusted"]:
            tag_info = f" [adjusted E={task['adjusted']['expected']}]"
        print(
            f"  {task['name']:12s}  O={task['input']['optimistic']}, "
            f"M={task['input']['most_likely']}, "
            f"P={task['input']['pessimistic']}  =>  E={tb['expected']}{tag_info}"
        )

    proj = project["project"]
    print("\nProject (textbook):")
    print(f"  Expected:       {proj['expected']} days")
    print(f"  Std Deviation:  {proj['std_dev']} days")
    print(f"  95% Confidence: [{proj['range_95'][0]}, {proj['range_95'][1]}] days")

    if project["adjusted_project"]:
        adj_proj = project["adjusted_project"]
        print("\nProject (adjusted):")
        print(f"  Expected:       {adj_proj['expected']} days")
        print(f"  Std Deviation:  {adj_proj['std_dev']} days")
        print(f"  95% Confidence: [{adj_proj['range_95'][0]}, {adj_proj['range_95'][1]}] days")
        gap = adj_proj["expected"] - proj["expected"]
        print(f"\n  Reality gap:    {gap:+.2f} days ({gap / proj['expected'] * 100:+.1f}%)")

    # Example 4: Visualization (optional)
    print("\n\n[Example 4] Visualization")
    print("-" * 70)

    try:
        print("Generating PERT estimate chart...")
        fig = visualize_estimate(project, save_path="pert_estimate.png")
        print("Chart saved as 'pert_estimate.png'")
    except ImportError as e:
        print(f"Skipping visualization: {e}")

    print("\n" + "=" * 70)
    print("Examples Complete!")
    print("=" * 70)
    print("\nTip: Import this module to use in your own scripts:")
    print("  from pert import estimate_task, estimate_project")
    print("  from pert import FRAGMENTED_COMMUNICATION, MULTIPLE_STAKEHOLDERS")
