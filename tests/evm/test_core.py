"""Unit tests for evm/core.py pure calculation functions."""

import math

import pytest

from app.evm.core import (
    HealthThresholds,
    WorkPackage,
    create_baseline,
    evaluate_progress,
    evm_metrics,
    health_signal,
)

# ── evm_metrics ───────────────────────────────────────────────────────────


class TestEvmMetrics:
    """Tests using the hand-calculated verification table."""

    def test_on_track(self, scenario_on_track):
        inp = scenario_on_track["input"]
        exp = scenario_on_track["expected"]
        result = evm_metrics(**inp)
        assert result["sv"] == exp["sv"]
        assert result["spi"] == pytest.approx(exp["spi"], abs=0.0001)
        assert result["cv"] == exp["cv"]
        assert result["cpi"] == pytest.approx(exp["cpi"], abs=0.0001)
        assert result["eac"] == pytest.approx(exp["eac"], abs=0.01)
        assert result["tcpi"] == pytest.approx(exp["tcpi"], abs=0.0001)
        assert result["percent_complete"] == exp["percent_complete"]
        assert result["percent_spent"] == exp["percent_spent"]

    def test_behind_and_over(self, scenario_behind_over):
        inp = scenario_behind_over["input"]
        exp = scenario_behind_over["expected"]
        result = evm_metrics(**inp)
        assert result["sv"] == exp["sv"]
        assert result["spi"] == pytest.approx(exp["spi"], abs=0.0001)
        assert result["cv"] == exp["cv"]
        assert result["cpi"] == pytest.approx(exp["cpi"], abs=0.0001)
        assert result["eac"] == pytest.approx(exp["eac"], abs=0.01)
        assert result["tcpi"] == pytest.approx(exp["tcpi"], abs=0.0001)
        assert result["percent_complete"] == exp["percent_complete"]
        assert result["percent_spent"] == exp["percent_spent"]

    def test_ahead_and_under(self, scenario_ahead_under):
        inp = scenario_ahead_under["input"]
        exp = scenario_ahead_under["expected"]
        result = evm_metrics(**inp)
        assert result["sv"] == exp["sv"]
        assert result["spi"] == pytest.approx(exp["spi"], abs=0.0001)
        assert result["cv"] == exp["cv"]
        assert result["cpi"] == pytest.approx(exp["cpi"], abs=0.0001)
        assert result["eac"] == pytest.approx(exp["eac"], abs=0.01)
        assert result["tcpi"] == pytest.approx(exp["tcpi"], abs=0.0001)
        assert result["percent_complete"] == exp["percent_complete"]
        assert result["percent_spent"] == exp["percent_spent"]

    def test_not_started(self, scenario_not_started):
        inp = scenario_not_started["input"]
        exp = scenario_not_started["expected"]
        result = evm_metrics(**inp)
        assert result["sv"] == exp["sv"]
        assert result["spi"] == exp["spi"]
        assert result["cv"] == exp["cv"]
        assert math.isinf(result["cpi"])
        assert result["percent_complete"] == exp["percent_complete"]
        assert result["percent_spent"] == exp["percent_spent"]

    def test_all_done(self, scenario_all_done):
        inp = scenario_all_done["input"]
        exp = scenario_all_done["expected"]
        result = evm_metrics(**inp)
        assert result["sv"] == exp["sv"]
        assert result["spi"] == pytest.approx(exp["spi"], abs=0.0001)
        assert result["cv"] == exp["cv"]
        assert result["cpi"] == pytest.approx(exp["cpi"], abs=0.0001)
        assert result["eac"] == pytest.approx(exp["eac"], abs=0.01)
        # TCPI = (BAC-EV)/(BAC-AC) = 0/0 → remaining_budget=0 → inf
        assert math.isinf(result["tcpi"])
        assert result["percent_complete"] == exp["percent_complete"]
        assert result["percent_spent"] == exp["percent_spent"]

    # Edge cases: inf handling

    def test_pv_zero_gives_inf_spi(self):
        result = evm_metrics(pv=0, ev=50, ac=50, bac=200)
        assert math.isinf(result["spi"])

    def test_ac_zero_gives_inf_cpi(self):
        result = evm_metrics(pv=100, ev=50, ac=0, bac=200)
        assert math.isinf(result["cpi"])

    def test_bac_equals_ac_gives_inf_tcpi(self):
        result = evm_metrics(pv=100, ev=80, ac=200, bac=200)
        assert math.isinf(result["tcpi"])

    def test_cpi_zero_gives_inf_eac(self):
        # CPI = EV/AC = 0/100 = 0 → EAC = BAC/0 = inf
        result = evm_metrics(pv=100, ev=0, ac=100, bac=200)
        assert math.isinf(result["eac"])

    # Validation errors

    def test_negative_bac_raises(self):
        with pytest.raises(ValueError, match="BAC must be positive"):
            evm_metrics(pv=100, ev=100, ac=100, bac=-1)

    def test_zero_bac_raises(self):
        with pytest.raises(ValueError, match="BAC must be positive"):
            evm_metrics(pv=100, ev=100, ac=100, bac=0)

    def test_negative_pv_raises(self):
        with pytest.raises(ValueError, match="PV cannot be negative"):
            evm_metrics(pv=-1, ev=100, ac=100, bac=200)

    def test_negative_ev_raises(self):
        with pytest.raises(ValueError, match="EV cannot be negative"):
            evm_metrics(pv=100, ev=-1, ac=100, bac=200)

    def test_negative_ac_raises(self):
        with pytest.raises(ValueError, match="AC cannot be negative"):
            evm_metrics(pv=100, ev=100, ac=-1, bac=200)

    # Rounding

    def test_currency_rounded_to_2dp(self):
        result = evm_metrics(pv=100, ev=90, ac=110, bac=500)
        for key in ("sv", "cv", "eac", "etc", "vac"):
            val_str = str(result[key])
            if "." in val_str:
                assert len(val_str.split(".")[1]) <= 2

    def test_ratios_rounded_to_4dp(self):
        result = evm_metrics(pv=100, ev=90, ac=110, bac=500)
        for key in ("spi", "cpi", "tcpi"):
            val_str = str(result[key])
            if "." in val_str:
                assert len(val_str.split(".")[1]) <= 4

    def test_percentages_rounded_to_2dp(self):
        result = evm_metrics(pv=100, ev=90, ac=110, bac=500)
        for key in ("percent_complete", "percent_spent"):
            val_str = str(result[key])
            if "." in val_str:
                assert len(val_str.split(".")[1]) <= 2


# ── health_signal ─────────────────────────────────────────────────────────


class TestHealthSignal:
    def test_on_track(self):
        result = health_signal(spi=1.0, cpi=1.0)
        assert result["status"] == "on_track"
        assert result["reasons"] == []

    def test_at_risk_schedule(self):
        result = health_signal(spi=0.95, cpi=1.0)
        assert result["status"] == "at_risk"
        assert len(result["reasons"]) == 1
        assert "Schedule" in result["reasons"][0]

    def test_at_risk_cost(self):
        result = health_signal(spi=1.0, cpi=0.95)
        assert result["status"] == "at_risk"
        assert len(result["reasons"]) == 1
        assert "Cost" in result["reasons"][0]

    def test_off_track_schedule(self):
        result = health_signal(spi=0.85, cpi=1.0)
        assert result["status"] == "off_track"
        assert len(result["reasons"]) == 1

    def test_off_track_cost(self):
        result = health_signal(spi=1.0, cpi=0.85)
        assert result["status"] == "off_track"
        assert len(result["reasons"]) == 1

    def test_off_track_both(self):
        result = health_signal(spi=0.85, cpi=0.85)
        assert result["status"] == "off_track"
        assert len(result["reasons"]) == 2

    def test_boundary_exact_0_9_is_at_risk(self):
        """SPI = 0.9 exactly: >= 0.9 so NOT off_track, but < 1.0 so at_risk."""
        result = health_signal(spi=0.9, cpi=1.0)
        assert result["status"] == "at_risk"

    def test_boundary_just_below_0_9(self):
        result = health_signal(spi=0.89999, cpi=1.0)
        assert result["status"] == "off_track"

    def test_boundary_just_above_0_9(self):
        result = health_signal(spi=0.90001, cpi=1.0)
        assert result["status"] == "at_risk"

    def test_custom_thresholds(self):
        strict = HealthThresholds(
            spi_off_track=0.95,
            spi_at_risk=1.0,
            cpi_off_track=0.95,
            cpi_at_risk=1.0,
        )
        result = health_signal(spi=0.92, cpi=1.0, thresholds=strict)
        assert result["status"] == "off_track"

    def test_summary_on_track(self):
        result = health_signal(spi=1.0, cpi=1.0)
        assert "on track" in result["summary"]

    def test_summary_at_risk(self):
        result = health_signal(spi=0.95, cpi=1.0)
        assert "at risk" in result["summary"]

    def test_summary_off_track(self):
        result = health_signal(spi=0.85, cpi=1.0)
        assert "off track" in result["summary"]


# ── create_baseline ───────────────────────────────────────────────────────


class TestCreateBaseline:
    def test_basic_creation(self):
        baseline = create_baseline(
            [
                WorkPackage("A", 5000),
                WorkPackage("B", 3000),
                WorkPackage("C", 2000),
            ]
        )
        assert baseline.bac == 10000.0
        assert len(baseline.work_packages) == 3

    def test_weight_normalization(self):
        baseline = create_baseline(
            [
                WorkPackage("A", 5000),
                WorkPackage("B", 5000),
            ]
        )
        for wp in baseline.work_packages:
            assert wp["weight"] == pytest.approx(0.5, abs=0.0001)

    def test_explicit_weight_respected(self):
        baseline = create_baseline(
            [
                WorkPackage("A", 5000, weight=0.7),
                WorkPackage("B", 5000),
            ]
        )
        assert baseline.work_packages[0]["weight"] == 0.7
        assert baseline.work_packages[1]["weight"] == pytest.approx(0.5, abs=0.0001)

    def test_bac_is_sum(self):
        baseline = create_baseline(
            [
                WorkPackage("X", 1234.56),
                WorkPackage("Y", 7890.12),
            ]
        )
        assert baseline.bac == pytest.approx(9124.68, abs=0.01)

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="At least one work package"):
            create_baseline([])

    def test_negative_planned_value_raises(self):
        with pytest.raises(ValueError, match="Planned value cannot be negative"):
            create_baseline([WorkPackage("Bad", -100)])

    def test_zero_total_raises(self):
        with pytest.raises(ValueError, match="BAC.*must be positive"):
            create_baseline([WorkPackage("Zero", 0)])

    def test_single_work_package(self):
        baseline = create_baseline([WorkPackage("Only", 1000)])
        assert baseline.bac == 1000.0
        assert baseline.work_packages[0]["weight"] == pytest.approx(1.0, abs=0.0001)


# ── evaluate_progress ─────────────────────────────────────────────────────


class TestEvaluateProgress:
    def _make_baseline(self):
        return create_baseline(
            [
                WorkPackage("A", 5000),
                WorkPackage("B", 3000),
                WorkPackage("C", 2000),
            ]
        )

    def test_pv_computed_from_percent_planned(self):
        baseline = self._make_baseline()
        result = evaluate_progress(
            baseline,
            percent_planned=50.0,
            actual_completions=[{"name": "A", "percent_complete": 50.0}],
            actual_cost=3000,
        )
        assert result["input"]["pv"] == pytest.approx(5000.0, abs=0.01)

    def test_ev_computed_from_completions(self):
        baseline = self._make_baseline()
        result = evaluate_progress(
            baseline,
            percent_planned=50.0,
            actual_completions=[
                {"name": "A", "percent_complete": 100.0},
                {"name": "B", "percent_complete": 50.0},
            ],
            actual_cost=6000,
        )
        # EV = 5000*1.0 + 3000*0.5 + 2000*0.0 = 6500
        assert result["input"]["ev"] == pytest.approx(6500.0, abs=0.01)

    def test_missing_wp_defaults_to_zero(self):
        baseline = self._make_baseline()
        result = evaluate_progress(
            baseline,
            percent_planned=50.0,
            actual_completions=[{"name": "A", "percent_complete": 100.0}],
            actual_cost=5000,
        )
        # Only A is 100%, B and C default to 0%
        assert result["input"]["ev"] == pytest.approx(5000.0, abs=0.01)

    def test_work_package_breakdown(self):
        baseline = self._make_baseline()
        result = evaluate_progress(
            baseline,
            percent_planned=50.0,
            actual_completions=[
                {"name": "A", "percent_complete": 80.0},
                {"name": "B", "percent_complete": 40.0},
            ],
            actual_cost=5000,
        )
        assert len(result["work_packages"]) == 3
        wp_a = result["work_packages"][0]
        assert wp_a["name"] == "A"
        assert wp_a["earned_value"] == pytest.approx(4000.0, abs=0.01)

    def test_includes_metrics_and_health(self):
        baseline = self._make_baseline()
        result = evaluate_progress(
            baseline,
            percent_planned=50.0,
            actual_completions=[{"name": "A", "percent_complete": 50.0}],
            actual_cost=3000,
        )
        assert "metrics" in result
        assert "health" in result
        assert "spi" in result["metrics"]
        assert "status" in result["health"]

    def test_percent_planned_below_zero_raises(self):
        baseline = self._make_baseline()
        with pytest.raises(ValueError, match="percent_planned must be 0–100"):
            evaluate_progress(baseline, -1, [], 0)

    def test_percent_planned_above_100_raises(self):
        baseline = self._make_baseline()
        with pytest.raises(ValueError, match="percent_planned must be 0–100"):
            evaluate_progress(baseline, 101, [], 0)

    def test_negative_actual_cost_raises(self):
        baseline = self._make_baseline()
        with pytest.raises(ValueError, match="actual_cost cannot be negative"):
            evaluate_progress(baseline, 50, [], -1)

    def test_completion_out_of_range_raises(self):
        baseline = self._make_baseline()
        with pytest.raises(ValueError, match="percent_complete must be 0–100"):
            evaluate_progress(
                baseline,
                50.0,
                [{"name": "A", "percent_complete": 150.0}],
                1000,
            )

    def test_custom_thresholds_passed_through(self):
        baseline = self._make_baseline()
        strict = HealthThresholds(
            spi_off_track=0.95,
            spi_at_risk=1.0,
            cpi_off_track=0.95,
            cpi_at_risk=1.0,
        )
        result = evaluate_progress(
            baseline,
            percent_planned=50.0,
            actual_completions=[{"name": "A", "percent_complete": 40.0}],
            actual_cost=5000,
            thresholds=strict,
        )
        # With strict thresholds, even small deviations trigger off_track
        assert result["health"]["status"] in ("at_risk", "off_track")
