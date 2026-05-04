"""
MCP server prototype tests.

Light coverage — registration check and one happy path per tool, plus a
couple of Layer 2 edge cases on the flagship. Implementation-grade
sweeps live in tests/{pert,montecarlo,tco,evm}/ already.
"""

import pytest

from mcp_server.server import mcp
from mcp_server.tools import (
    compare_investment_options,
    estimate_from_history,
    estimate_task_duration,
    evaluate_project_health,
    identify_schedule_risk,
)

# =============================================================================
# Registration
# =============================================================================


class TestServerRegistration:
    async def test_all_five_tools_registered(self):
        names = {t.name for t in await mcp.list_tools()}
        assert names == {
            "estimate_task_duration",
            "estimate_from_history",
            "identify_schedule_risk",
            "compare_investment_options",
            "evaluate_project_health",
        }

    async def test_tool_descriptions_state_decision_question(self):
        """Each tool's description should lead with 'Use when:' so the LLM
        picks the right tool for the right decision question (not by guessing
        from acronyms)."""
        for tool in await mcp.list_tools():
            assert tool.description, f"Tool {tool.name} has no description"
            assert "Use when:" in tool.description, (
                f"Tool {tool.name} description should start with 'Use when:'"
            )


# =============================================================================
# estimate_task_duration
# =============================================================================


class TestEstimateTaskDuration:
    def test_textbook_only(self):
        r = estimate_task_duration(2, 5, 14)
        assert r["textbook"]["expected"] == pytest.approx(6.0)
        assert r["adjusted"] is None

    def test_with_insight_tags_widens_pessimistic(self):
        r = estimate_task_duration(2, 5, 14, insight_tags={"FRAGMENTED_COMMUNICATION": 0.5})
        assert r["adjusted"] is not None
        assert r["adjusted"]["expected"] > r["textbook"]["expected"]

    def test_unknown_tag_raises(self):
        with pytest.raises(ValueError, match="Unknown insight tag 'nonesuch'"):
            estimate_task_duration(2, 5, 10, insight_tags={"nonesuch": 0.5})


# =============================================================================
# estimate_from_history (flagship v0.1)
# =============================================================================


class TestEstimateFromHistory:
    def test_happy_path_medium_quality(self):
        r = estimate_from_history(
            "auth-api",
            optimistic=4,
            past_actuals=[5.0, 6.5, 7.2, 5.8, 6.1],
            team_familiarity=0.5,
            complexity_factor=0.5,
            novelty_factor=0.5,
        )
        assert r["data_quality"] == "medium"
        assert r["calibration_version"] == "v0.1"
        assert r["derived_most_likely"] >= 4
        assert r["derived_pessimistic"] >= r["derived_most_likely"]

    def test_data_quality_buckets(self):
        low = estimate_from_history("x", 1, [5.0])
        mid = estimate_from_history("x", 1, [5.0, 6.0, 7.0])
        high = estimate_from_history("x", 1, [5.0] * 8)
        assert low["data_quality"] == "low"
        assert mid["data_quality"] == "medium"
        assert high["data_quality"] == "high"

    def test_complexity_lifts_most_likely(self):
        easy = estimate_from_history("x", 1, [5.0, 6.0, 7.0], complexity_factor=0.0)
        hard = estimate_from_history("x", 1, [5.0, 6.0, 7.0], complexity_factor=1.0)
        assert hard["derived_most_likely"] > easy["derived_most_likely"]

    def test_low_familiarity_widens_spread(self):
        familiar = estimate_from_history("x", 1, [5.0, 6.0, 7.0], team_familiarity=1.0)
        new = estimate_from_history("x", 1, [5.0, 6.0, 7.0], team_familiarity=0.0)
        familiar_spread = familiar["derived_pessimistic"] - familiar["derived_most_likely"]
        new_spread = new["derived_pessimistic"] - new["derived_most_likely"]
        assert new_spread > familiar_spread

    def test_novelty_lifts_pessimistic_only(self):
        """Novelty widens the tail without moving the central tendency."""
        familiar = estimate_from_history("x", 1, [5.0, 6.0, 7.0], novelty_factor=0.0)
        new = estimate_from_history("x", 1, [5.0, 6.0, 7.0], novelty_factor=1.0)
        assert new["derived_most_likely"] == familiar["derived_most_likely"]
        assert new["derived_pessimistic"] > familiar["derived_pessimistic"]

    def test_empty_history_raises(self):
        with pytest.raises(ValueError, match="at least one observation"):
            estimate_from_history("x", 1, [])

    def test_calibration_knob_out_of_range_raises(self):
        with pytest.raises(ValueError, match="team_familiarity"):
            estimate_from_history("x", 1, [5.0], team_familiarity=1.5)

    def test_layer1_tags_compose_with_layer2(self):
        without = estimate_from_history(
            "x", 1, [5.0, 6.0, 7.0], complexity_factor=0.5, novelty_factor=0.3
        )
        with_tags = estimate_from_history(
            "x",
            1,
            [5.0, 6.0, 7.0],
            complexity_factor=0.5,
            novelty_factor=0.3,
            insight_tags={"MULTIPLE_STAKEHOLDERS": 0.5},
        )
        # Same Layer 2 derivation; Layer 1 widens pessimistic only.
        assert with_tags["derived_most_likely"] == without["derived_most_likely"]
        assert with_tags["adjusted_estimate"] is not None
        assert without["adjusted_estimate"] is None


# =============================================================================
# identify_schedule_risk
# =============================================================================


class TestIdentifyScheduleRisk:
    def test_returns_ranked_risks(self):
        r = identify_schedule_risk(
            [
                {"name": "A", "optimistic": 2, "most_likely": 5, "pessimistic": 12},
                {
                    "name": "B",
                    "optimistic": 3,
                    "most_likely": 6,
                    "pessimistic": 8,
                    "depends_on": ["A"],
                },
            ],
            num_simulations=500,
            seed=42,
        )
        assert len(r["ranked_risks"]) == 2
        assert r["ranked_risks"][0]["rank"] == 1
        assert r["ranked_risks"][0]["risk_score"] >= r["ranked_risks"][1]["risk_score"]
        assert "P50" in r["project_percentiles"]

    def test_empty_tasks_raises(self):
        with pytest.raises(ValueError, match="at least one task"):
            identify_schedule_risk([], num_simulations=100)


# =============================================================================
# compare_investment_options
# =============================================================================


class TestCompareInvestmentOptions:
    def test_ranks_by_annual_cost(self):
        r = compare_investment_options(
            [
                {
                    "name": "A",
                    "initial_price": 1000,
                    "useful_life_years": 5,
                    "annual_maintenance": 100,
                },
                {
                    "name": "B",
                    "initial_price": 800,
                    "useful_life_years": 5,
                    "annual_maintenance": 200,
                },
            ]
        )
        assert r["ranked_options"][0]["name"] == "A"
        assert "Cheapest" in r["summary"]

    def test_single_option_raises(self):
        with pytest.raises(ValueError, match="at least 2"):
            compare_investment_options(
                [{"name": "A", "initial_price": 100, "useful_life_years": 1}]
            )


# =============================================================================
# evaluate_project_health
# =============================================================================


class TestEvaluateProjectHealth:
    def test_off_track_when_under_budget_threshold(self):
        r = evaluate_project_health(
            planned_value=1000,
            earned_value=900,
            actual_cost=1100,
            budget_at_completion=5000,
        )
        assert r["health"]["status"] == "off_track"
        assert r["metrics"]["spi"] == pytest.approx(0.9)
        assert r["metrics"]["cpi"] < 1.0

    def test_on_track_when_at_or_above_thresholds(self):
        r = evaluate_project_health(
            planned_value=1000,
            earned_value=1000,
            actual_cost=950,
            budget_at_completion=5000,
        )
        assert r["health"]["status"] == "on_track"

    def test_zero_bac_raises(self):
        with pytest.raises(ValueError, match="BAC must be positive"):
            evaluate_project_health(100, 100, 100, 0)
