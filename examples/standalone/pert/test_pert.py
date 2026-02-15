# test_pert.py
import pytest
from pert import (
    FRAGMENTED_COMMUNICATION,
    HIDDEN_DEPENDENCIES,
    MULTIPLE_STAKEHOLDERS,
    InsightTag,
    estimate_project,
    estimate_task,
    visualize_estimate,
)


def test_estimate_task_textbook():
    """Test classic PERT math with exact values."""
    result = estimate_task(5, 10, 20)

    assert result["input"] == {"optimistic": 5, "most_likely": 10, "pessimistic": 20}

    tb = result["textbook"]
    # E = (5 + 4*10 + 20) / 6 = 65/6 = 10.833...
    assert tb["expected"] == 10.83
    # σ = (20 - 5) / 6 = 15/6 = 2.5
    assert tb["std_dev"] == 2.5
    # σ² = 2.5² = 6.25
    assert tb["variance"] == 6.25
    # 68%: 10.83 ± 2.5
    assert tb["range_68"] == [8.33, 13.33]
    # 95%: 10.83 ± 5.0
    assert tb["range_95"] == [5.83, 15.83]
    # 99.7%: 10.83 ± 7.5
    assert tb["range_99"] == [3.33, 18.33]

    assert result["adjusted"] is None


def test_estimate_task_with_tags():
    """Test adjusted P, combined multiplier, and result structure."""
    result = estimate_task(5, 10, 20, tags=[FRAGMENTED_COMMUNICATION])

    assert result["adjusted"] is not None
    adj = result["adjusted"]

    # Default severity 0.5: effective = 1.1 + 0.5 * (1.5 - 1.1) = 1.3
    assert adj["tags_applied"][0]["name"] == "FRAGMENTED_COMMUNICATION"
    assert adj["tags_applied"][0]["severity"] == 0.5
    assert adj["tags_applied"][0]["multiplier"] == 1.3

    assert adj["combined_multiplier"] == 1.3
    # adjusted_P = 20 * 1.3 = 26
    assert adj["pessimistic"] == 26.0

    # E = (5 + 4*10 + 26) / 6 = 71/6 = 11.833...
    assert adj["expected"] == 11.83
    # σ = (26 - 5) / 6 = 21/6 = 3.5
    assert adj["std_dev"] == 3.5


def test_estimate_task_custom_severity():
    """Test severity interpolation between min/max."""
    # Severity 0.0 → min_multiplier
    result = estimate_task(5, 10, 20, tags=[(FRAGMENTED_COMMUNICATION, 0.0)])
    adj = result["adjusted"]
    assert adj["tags_applied"][0]["multiplier"] == 1.1
    assert adj["pessimistic"] == 22.0  # 20 * 1.1

    # Severity 1.0 → max_multiplier
    result = estimate_task(5, 10, 20, tags=[(FRAGMENTED_COMMUNICATION, 1.0)])
    adj = result["adjusted"]
    assert adj["tags_applied"][0]["multiplier"] == 1.5
    assert adj["pessimistic"] == 30.0  # 20 * 1.5

    # Two tags combined
    result = estimate_task(
        5,
        10,
        20,
        tags=[
            (FRAGMENTED_COMMUNICATION, 0.5),  # 1.3
            (MULTIPLE_STAKEHOLDERS, 0.0),  # 1.15
        ],
    )
    adj = result["adjusted"]
    assert adj["combined_multiplier"] == round(1.3 * 1.15, 4)
    assert adj["pessimistic"] == round(20 * 1.3 * 1.15, 2)


def test_estimate_task_validation():
    """Test ValueError for invalid inputs."""
    # O > M
    with pytest.raises(ValueError, match="Optimistic.*cannot exceed most likely"):
        estimate_task(15, 10, 20)

    # M > P
    with pytest.raises(ValueError, match="Most likely.*cannot exceed pessimistic"):
        estimate_task(5, 25, 20)

    # Negative values
    with pytest.raises(ValueError, match="non-negative"):
        estimate_task(-1, 10, 20)
    with pytest.raises(ValueError, match="non-negative"):
        estimate_task(5, -1, 20)
    with pytest.raises(ValueError, match="non-negative"):
        estimate_task(5, 10, -1)

    # Invalid severity
    with pytest.raises(ValueError, match="Severity"):
        estimate_task(5, 10, 20, tags=[(FRAGMENTED_COMMUNICATION, 1.5)])


def test_estimate_project():
    """Test aggregation math: sum of means, sum of variances."""
    project = estimate_project(
        [
            {"name": "A", "optimistic": 2, "most_likely": 4, "pessimistic": 6},
            {"name": "B", "optimistic": 4, "most_likely": 8, "pessimistic": 12},
        ]
    )

    assert len(project["tasks"]) == 2
    assert project["tasks"][0]["name"] == "A"
    assert project["tasks"][1]["name"] == "B"

    # Task A: E = (2+16+6)/6 = 4.0, σ = (6-2)/6 = 0.667, σ² = 0.444
    # Task B: E = (4+32+12)/6 = 8.0, σ = (12-4)/6 = 1.333, σ² = 1.778
    # Project: E = 12.0, σ² = 2.222, σ = 1.491
    proj = project["project"]
    assert proj["expected"] == 12.0
    assert proj["variance"] == 2.22
    assert proj["std_dev"] == 1.49

    assert project["adjusted_project"] is None


def test_estimate_project_with_tags():
    """Test mixed tags across tasks in project aggregation."""
    project = estimate_project(
        [
            {"name": "A", "optimistic": 2, "most_likely": 4, "pessimistic": 6},
            {
                "name": "B",
                "optimistic": 4,
                "most_likely": 8,
                "pessimistic": 12,
                "tags": [HIDDEN_DEPENDENCIES],
            },
        ]
    )

    # Task A has no adjustment
    assert project["tasks"][0]["adjusted"] is None
    # Task B is adjusted
    assert project["tasks"][1]["adjusted"] is not None

    # Adjusted project should exist since at least one task has tags
    assert project["adjusted_project"] is not None
    adj_proj = project["adjusted_project"]

    # Task B adjusted P = 12 * 1.3 = 15.6
    # Task B adj E = (4 + 32 + 15.6) / 6 = 51.6 / 6 = 8.6
    # Task A E = 4.0 (unchanged)
    # Project adj E = 4.0 + 8.6 = 12.6
    assert adj_proj["expected"] == 12.6

    # Adjusted expected should be larger than textbook
    assert adj_proj["expected"] > project["project"]["expected"]


def test_estimate_project_empty():
    """Test ValueError for empty tasks list."""
    with pytest.raises(ValueError, match="empty"):
        estimate_project([])


def test_visualize_estimate():
    """Test that visualize_estimate returns a Figure."""
    import matplotlib.pyplot as plt

    result = estimate_task(5, 10, 20, tags=[FRAGMENTED_COMMUNICATION])
    fig = visualize_estimate(result)

    assert fig is not None
    assert isinstance(fig, plt.Figure)

    plt.close(fig)


def test_visualize_project():
    """Test visualization with project-level data."""
    import matplotlib.pyplot as plt

    project = estimate_project(
        [
            {"name": "A", "optimistic": 2, "most_likely": 4, "pessimistic": 6},
            {
                "name": "B",
                "optimistic": 4,
                "most_likely": 8,
                "pessimistic": 12,
                "tags": [HIDDEN_DEPENDENCIES],
            },
        ]
    )
    fig = visualize_estimate(project)

    assert fig is not None
    assert isinstance(fig, plt.Figure)

    plt.close(fig)


def test_custom_insight_tag():
    """Test that users can create custom InsightTag instances."""
    tech_debt = InsightTag("TECH_DEBT", "Legacy code drag", 1.1, 1.4)
    result = estimate_task(5, 10, 20, tags=[(tech_debt, 0.5)])

    adj = result["adjusted"]
    assert adj["tags_applied"][0]["name"] == "TECH_DEBT"
    # 1.1 + 0.5 * (1.4 - 1.1) = 1.25
    assert adj["tags_applied"][0]["multiplier"] == 1.25
    assert adj["pessimistic"] == 25.0  # 20 * 1.25
