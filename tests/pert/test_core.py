"""Unit tests for pert/core.py pure calculation functions."""

import math

import pytest

from app.pert.core import (
    DEFAULT_TAGS,
    FRAGMENTED_COMMUNICATION,
    HIDDEN_DEPENDENCIES,
    MULTIPLE_STAKEHOLDERS,
    calculate_project,
    calculate_task,
)

# ── calculate_task ──────────────────────────────────────────────────────────


class TestCalculateTask:
    def test_basic(self):
        result = calculate_task(5, 10, 20)
        tb = result["textbook"]
        assert tb["expected"] == pytest.approx(10.83, abs=0.01)
        assert tb["std_dev"] == 2.5
        assert tb["variance"] == pytest.approx(6.25, abs=0.01)
        assert result["adjusted"] is None

    def test_range_68(self):
        result = calculate_task(5, 10, 20)
        tb = result["textbook"]
        assert tb["range_68"][0] == pytest.approx(tb["expected"] - tb["std_dev"], abs=0.01)
        assert tb["range_68"][1] == pytest.approx(tb["expected"] + tb["std_dev"], abs=0.01)

    def test_range_95(self):
        result = calculate_task(5, 10, 20)
        tb = result["textbook"]
        assert tb["range_95"][0] == pytest.approx(tb["expected"] - 2 * tb["std_dev"], abs=0.01)
        assert tb["range_95"][1] == pytest.approx(tb["expected"] + 2 * tb["std_dev"], abs=0.01)

    def test_input_echo(self):
        result = calculate_task(5, 10, 20)
        assert result["input"] == {
            "optimistic": 5,
            "most_likely": 10,
            "pessimistic": 20,
        }

    def test_equal_estimates(self):
        result = calculate_task(10, 10, 10)
        tb = result["textbook"]
        assert tb["expected"] == 10.0
        assert tb["std_dev"] == 0.0
        assert tb["variance"] == 0.0

    def test_with_single_tag(self):
        result = calculate_task(5, 10, 20, tags=[FRAGMENTED_COMMUNICATION])
        assert result["adjusted"] is not None
        adj = result["adjusted"]
        assert adj["expected"] > result["textbook"]["expected"]
        assert adj["pessimistic"] > 20
        assert len(adj["tags_applied"]) == 1
        assert adj["tags_applied"][0]["name"] == "FRAGMENTED_COMMUNICATION"
        assert adj["tags_applied"][0]["severity"] == 0.5

    def test_with_tag_and_severity(self):
        result = calculate_task(5, 10, 20, tags=[(FRAGMENTED_COMMUNICATION, 0.8)])
        adj = result["adjusted"]
        assert adj is not None
        assert adj["tags_applied"][0]["severity"] == 0.8

    def test_with_multiple_tags(self):
        result = calculate_task(
            5, 10, 20, tags=[(FRAGMENTED_COMMUNICATION, 0.8), (MULTIPLE_STAKEHOLDERS, 0.6)]
        )
        adj = result["adjusted"]
        assert len(adj["tags_applied"]) == 2
        assert adj["combined_multiplier"] > 1.0

    def test_combined_multiplier_is_product(self):
        result = calculate_task(
            5, 10, 20, tags=[(FRAGMENTED_COMMUNICATION, 0.0), (HIDDEN_DEPENDENCIES, 0.0)]
        )
        adj = result["adjusted"]
        expected_mult = FRAGMENTED_COMMUNICATION.min_multiplier * HIDDEN_DEPENDENCIES.min_multiplier
        assert adj["combined_multiplier"] == pytest.approx(expected_mult, abs=0.001)

    def test_negative_optimistic_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            calculate_task(-1, 10, 20)

    def test_negative_most_likely_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            calculate_task(5, -1, 20)

    def test_negative_pessimistic_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            calculate_task(5, 10, -1)

    def test_optimistic_exceeds_most_likely_raises(self):
        with pytest.raises(ValueError, match="Optimistic.*cannot exceed most likely"):
            calculate_task(15, 10, 20)

    def test_most_likely_exceeds_pessimistic_raises(self):
        with pytest.raises(ValueError, match="Most likely.*cannot exceed pessimistic"):
            calculate_task(5, 25, 20)

    def test_severity_below_zero_raises(self):
        with pytest.raises(ValueError, match="Severity must be between"):
            calculate_task(5, 10, 20, tags=[(FRAGMENTED_COMMUNICATION, -0.1)])

    def test_severity_above_one_raises(self):
        with pytest.raises(ValueError, match="Severity must be between"):
            calculate_task(5, 10, 20, tags=[(FRAGMENTED_COMMUNICATION, 1.1)])

    def test_severity_boundary_zero(self):
        result = calculate_task(5, 10, 20, tags=[(FRAGMENTED_COMMUNICATION, 0.0)])
        adj = result["adjusted"]
        assert adj["tags_applied"][0]["multiplier"] == pytest.approx(
            FRAGMENTED_COMMUNICATION.min_multiplier, abs=0.001
        )

    def test_severity_boundary_one(self):
        result = calculate_task(5, 10, 20, tags=[(FRAGMENTED_COMMUNICATION, 1.0)])
        adj = result["adjusted"]
        assert adj["tags_applied"][0]["multiplier"] == pytest.approx(
            FRAGMENTED_COMMUNICATION.max_multiplier, abs=0.001
        )


# ── calculate_project ──────────────────────────────────────────────────────


class TestCalculateProject:
    def test_basic_aggregation(self):
        tasks = [
            {"name": "A", "optimistic": 3, "most_likely": 5, "pessimistic": 10},
            {"name": "B", "optimistic": 10, "most_likely": 15, "pessimistic": 30},
        ]
        result = calculate_project(tasks)

        assert len(result["tasks"]) == 2
        assert result["tasks"][0]["name"] == "A"
        assert result["tasks"][1]["name"] == "B"

        # Project expected = sum of task expecteds
        a_expected = (3 + 4 * 5 + 10) / 6
        b_expected = (10 + 4 * 15 + 30) / 6
        assert result["project"]["expected"] == pytest.approx(a_expected + b_expected, abs=0.01)

    def test_variance_summation(self):
        tasks = [
            {"name": "A", "optimistic": 3, "most_likely": 5, "pessimistic": 10},
            {"name": "B", "optimistic": 10, "most_likely": 15, "pessimistic": 30},
        ]
        result = calculate_project(tasks)

        a_var = ((10 - 3) / 6) ** 2
        b_var = ((30 - 10) / 6) ** 2
        assert result["project"]["variance"] == pytest.approx(a_var + b_var, abs=0.01)
        assert result["project"]["std_dev"] == pytest.approx(math.sqrt(a_var + b_var), abs=0.01)

    def test_no_adjusted_when_no_tags(self):
        tasks = [
            {"name": "A", "optimistic": 3, "most_likely": 5, "pessimistic": 10},
        ]
        result = calculate_project(tasks)
        assert result["adjusted_project"] is None

    def test_adjusted_project_with_tags(self):
        tasks = [
            {"name": "A", "optimistic": 3, "most_likely": 5, "pessimistic": 10},
            {
                "name": "B",
                "optimistic": 10,
                "most_likely": 15,
                "pessimistic": 30,
                "tags": [FRAGMENTED_COMMUNICATION],
            },
        ]
        result = calculate_project(tasks)
        assert result["adjusted_project"] is not None
        assert result["adjusted_project"]["expected"] > result["project"]["expected"]

    def test_empty_tasks_raises(self):
        with pytest.raises(ValueError, match="Tasks list cannot be empty"):
            calculate_project([])

    def test_single_task(self):
        tasks = [{"name": "Only", "optimistic": 5, "most_likely": 10, "pessimistic": 20}]
        result = calculate_project(tasks)
        single = calculate_task(5, 10, 20)
        assert result["project"]["expected"] == single["textbook"]["expected"]
        assert result["project"]["variance"] == single["textbook"]["variance"]

    def test_default_tags_dict(self):
        """Verify the DEFAULT_TAGS dict has the expected 3 entries."""
        assert len(DEFAULT_TAGS) == 3
        assert "FRAGMENTED_COMMUNICATION" in DEFAULT_TAGS
        assert "MULTIPLE_STAKEHOLDERS" in DEFAULT_TAGS
        assert "HIDDEN_DEPENDENCIES" in DEFAULT_TAGS
