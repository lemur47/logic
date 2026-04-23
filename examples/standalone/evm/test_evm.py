"""Tests for the EVM (Earned Value Management) standalone module.

Covers the four public functions — evm_metrics, health_signal,
create_baseline, evaluate_progress — plus data-class construction and the
optional visualize_progress helper. Hand-computed values use the
docstring examples in evm.py as ground truth.
"""

from pathlib import Path

import pytest
from evm import (
    Baseline,
    HealthStatus,
    HealthThresholds,
    WorkPackage,
    create_baseline,
    evaluate_progress,
    evm_metrics,
    health_signal,
    visualize_progress,
)

# ── evm_metrics: happy-path hand computations ────────────────────────────


def test_evm_metrics_docstring_example():
    """Hand-computed check mirroring evm.py::evm_metrics docstring example."""
    result = evm_metrics(pv=100, ev=90, ac=110, bac=500)

    # Schedule
    assert result["sv"] == -10.0  # 90 - 100
    assert result["spi"] == 0.9  # 90 / 100
    # Cost
    assert result["cv"] == -20.0  # 90 - 110
    assert result["cpi"] == 0.8182  # 90 / 110
    # Forecasting — EAC = BAC / CPI (computed from unrounded CPI = 90/110)
    assert result["eac"] == round(500 / (90 / 110), 2)  # 611.11
    # Progress
    assert result["percent_complete"] == 18.0  # 90 / 500 × 100
    assert result["percent_spent"] == 22.0  # 110 / 500 × 100


def test_evm_metrics_on_track_scenario():
    """When EV ≥ PV and EV ≥ AC the project is ahead-and-under (CPI, SPI ≥ 1)."""
    result = evm_metrics(pv=100, ev=110, ac=100, bac=500)
    assert result["sv"] == 10.0
    assert result["spi"] == 1.1
    assert result["cv"] == 10.0
    assert result["cpi"] == 1.1


def test_evm_metrics_off_track_scenario():
    """EV well below both PV and AC → poor SPI and CPI."""
    result = evm_metrics(pv=100, ev=60, ac=120, bac=500)
    assert result["spi"] == 0.6
    assert result["cpi"] == 0.5
    # Negative variances
    assert result["sv"] == -40.0
    assert result["cv"] == -60.0


def test_evm_metrics_zero_pv_yields_infinite_spi():
    """Division-by-zero guard: pv=0 collapses SPI to infinity."""
    result = evm_metrics(pv=0, ev=50, ac=40, bac=500)
    assert result["spi"] == float("inf")
    # SV is still well-defined (= EV - PV)
    assert result["sv"] == 50.0


def test_evm_metrics_zero_ac_yields_infinite_cpi():
    """Division-by-zero guard: ac=0 collapses CPI (and EAC) to infinity."""
    result = evm_metrics(pv=100, ev=50, ac=0, bac=500)
    assert result["cpi"] == float("inf")
    assert result["eac"] == 0.0  # BAC / inf → 0 after rounding


def test_evm_metrics_tcpi_matches_remaining_formula():
    """TCPI = (BAC - EV) / (BAC - AC) — the CPI required on remaining work."""
    # BAC 500, EV 200, AC 180 → remaining_work 300, remaining_budget 320 → 0.9375
    result = evm_metrics(pv=250, ev=200, ac=180, bac=500)
    assert result["tcpi"] == round(300 / 320, 4)


# ── evm_metrics: validation ──────────────────────────────────────────────


def test_evm_metrics_rejects_non_positive_bac():
    with pytest.raises(ValueError, match="BAC must be positive"):
        evm_metrics(pv=100, ev=100, ac=100, bac=0)
    with pytest.raises(ValueError, match="BAC must be positive"):
        evm_metrics(pv=100, ev=100, ac=100, bac=-1)


def test_evm_metrics_rejects_negative_inputs():
    with pytest.raises(ValueError, match="PV cannot be negative"):
        evm_metrics(pv=-1, ev=50, ac=50, bac=500)
    with pytest.raises(ValueError, match="EV cannot be negative"):
        evm_metrics(pv=100, ev=-1, ac=50, bac=500)
    with pytest.raises(ValueError, match="AC cannot be negative"):
        evm_metrics(pv=100, ev=50, ac=-1, bac=500)


# ── health_signal ────────────────────────────────────────────────────────


def test_health_signal_on_track():
    """SPI ≥ 1.0 and CPI ≥ 1.0 — clean bill of health, no reasons."""
    signal = health_signal(spi=1.0, cpi=1.0)
    assert signal["status"] == HealthStatus.ON_TRACK.value
    assert signal["reasons"] == []
    assert "on track" in signal["summary"].lower()


def test_health_signal_at_risk_schedule_only():
    """SPI in (0.9, 1.0) tips schedule to at-risk; cost still good."""
    signal = health_signal(spi=0.95, cpi=1.0)
    assert signal["status"] == HealthStatus.AT_RISK.value
    assert len(signal["reasons"]) == 1
    assert "Schedule" in signal["reasons"][0]


def test_health_signal_off_track_overrides_at_risk():
    """One off-track dimension beats another at-risk dimension."""
    # SPI off-track (< 0.9), CPI at-risk only
    signal = health_signal(spi=0.85, cpi=0.95)
    assert signal["status"] == HealthStatus.OFF_TRACK.value
    # Both reasons recorded
    assert len(signal["reasons"]) == 2


def test_health_signal_custom_thresholds():
    """Strict thresholds flip a borderline project to off-track."""
    strict = HealthThresholds(
        spi_off_track=0.95,
        spi_at_risk=1.0,
        cpi_off_track=0.95,
        cpi_at_risk=1.0,
    )
    # SPI 0.92 < 0.95 (strict off_track), CPI 0.97 ∈ (0.95, 1.0) → at-risk
    signal = health_signal(spi=0.92, cpi=0.97, thresholds=strict)
    assert signal["status"] == HealthStatus.OFF_TRACK.value


# ── create_baseline ──────────────────────────────────────────────────────


def test_create_baseline_sums_bac():
    """BAC equals the sum of planned_value across all work packages."""
    baseline = create_baseline(
        [
            WorkPackage("Auth", 5000),
            WorkPackage("API", 8000),
            WorkPackage("Frontend", 7000),
        ]
    )
    assert baseline.bac == 20000.0
    assert len(baseline.work_packages) == 3


def test_create_baseline_auto_normalises_weights():
    """When WorkPackage.weight is None, weight = planned_value / BAC."""
    baseline = create_baseline(
        [
            WorkPackage("Auth", 5000),
            WorkPackage("API", 8000),
            WorkPackage("Frontend", 7000),
        ]
    )
    weights = [wp["weight"] for wp in baseline.work_packages]
    # 5000/20000, 8000/20000, 7000/20000
    assert weights == [0.25, 0.4, 0.35]
    # Weights sum to 1.0 (up to rounding)
    assert round(sum(weights), 4) == 1.0


def test_create_baseline_preserves_explicit_weights():
    """Explicit weights override auto-normalisation."""
    baseline = create_baseline(
        [
            WorkPackage("Auth", 5000, weight=0.5),
            WorkPackage("API", 5000, weight=0.5),
        ]
    )
    weights = [wp["weight"] for wp in baseline.work_packages]
    assert weights == [0.5, 0.5]


def test_create_baseline_rejects_empty():
    with pytest.raises(ValueError, match="At least one work package"):
        create_baseline([])


def test_create_baseline_rejects_negative_planned_value():
    with pytest.raises(ValueError, match="Planned value cannot be negative"):
        create_baseline([WorkPackage("Bad", -100)])


def test_create_baseline_rejects_zero_bac():
    """All-zero planned values → BAC = 0 → rejected."""
    with pytest.raises(ValueError, match="must be positive"):
        create_baseline([WorkPackage("Zero", 0)])


# ── evaluate_progress ────────────────────────────────────────────────────


def test_evaluate_progress_midway_scenario():
    """End-to-end: baseline + half-way checkpoint produces coherent metrics."""
    baseline = create_baseline(
        [
            WorkPackage("Requirements", 3000),
            WorkPackage("Auth", 5000),
            WorkPackage("API", 8000),
            WorkPackage("Frontend", 7000),
            WorkPackage("Testing", 4000),
            WorkPackage("Deploy", 3000),
        ]
    )

    result = evaluate_progress(
        baseline=baseline,
        percent_planned=50.0,
        actual_completions=[
            {"name": "Requirements", "percent_complete": 100.0},
            {"name": "Auth", "percent_complete": 80.0},
            {"name": "API", "percent_complete": 30.0},
            {"name": "Frontend", "percent_complete": 10.0},
            {"name": "Testing", "percent_complete": 0.0},
            {"name": "Deploy", "percent_complete": 0.0},
        ],
        actual_cost=14500,
    )

    # PV = BAC × 0.5 = 15000
    assert result["input"]["pv"] == 15000.0
    # EV = 3000×1.0 + 5000×0.8 + 8000×0.3 + 7000×0.1 + 0 + 0
    #    = 3000 + 4000 + 2400 + 700 = 10100
    assert result["input"]["ev"] == 10100.0
    assert result["input"]["ac"] == 14500

    # Per-work-package earned-value breakdown
    assert len(result["work_packages"]) == 6
    auth_wp = next(wp for wp in result["work_packages"] if wp["name"] == "Auth")
    assert auth_wp["earned_value"] == 4000.0  # 5000 × 0.8

    # Health signal should fire off-track (SPI = 10100/15000 ≈ 0.67 < 0.9)
    assert result["health"]["status"] == HealthStatus.OFF_TRACK.value


def test_evaluate_progress_missing_wp_treated_as_zero_percent():
    """Work packages absent from actual_completions default to 0% complete."""
    baseline = create_baseline(
        [
            WorkPackage("Done", 1000),
            WorkPackage("Forgotten", 1000),
        ]
    )
    result = evaluate_progress(
        baseline=baseline,
        percent_planned=50.0,
        actual_completions=[{"name": "Done", "percent_complete": 100.0}],
        actual_cost=800,
    )
    # Only "Done" contributes 1000 to EV; "Forgotten" contributes 0
    assert result["input"]["ev"] == 1000.0

    # Breakdown still lists both
    names = [wp["name"] for wp in result["work_packages"]]
    assert names == ["Done", "Forgotten"]
    forgotten = next(wp for wp in result["work_packages"] if wp["name"] == "Forgotten")
    assert forgotten["percent_complete"] == 0.0
    assert forgotten["earned_value"] == 0.0


def test_evaluate_progress_rejects_percent_planned_out_of_range():
    baseline = create_baseline([WorkPackage("Only", 1000)])
    with pytest.raises(ValueError, match="percent_planned must be 0"):
        evaluate_progress(baseline, percent_planned=150.0, actual_completions=[], actual_cost=0)
    with pytest.raises(ValueError, match="percent_planned must be 0"):
        evaluate_progress(baseline, percent_planned=-1.0, actual_completions=[], actual_cost=0)


def test_evaluate_progress_rejects_negative_actual_cost():
    baseline = create_baseline([WorkPackage("Only", 1000)])
    with pytest.raises(ValueError, match="actual_cost cannot be negative"):
        evaluate_progress(baseline, percent_planned=50.0, actual_completions=[], actual_cost=-1)


def test_evaluate_progress_rejects_invalid_wp_completion():
    baseline = create_baseline([WorkPackage("Only", 1000)])
    with pytest.raises(ValueError, match="percent_complete must be 0"):
        evaluate_progress(
            baseline,
            percent_planned=50.0,
            actual_completions=[{"name": "Only", "percent_complete": 150.0}],
            actual_cost=500,
        )


# ── visualize_progress ───────────────────────────────────────────────────


def test_visualize_progress_saves_png(tmp_path):
    """The helper writes a PNG to save_path when given one."""
    baseline = create_baseline(
        [
            WorkPackage("A", 5000),
            WorkPackage("B", 5000),
        ]
    )
    result = evaluate_progress(
        baseline=baseline,
        percent_planned=50.0,
        actual_completions=[
            {"name": "A", "percent_complete": 100.0},
            {"name": "B", "percent_complete": 50.0},
        ],
        actual_cost=6000,
    )

    out = tmp_path / "evm_snapshot.png"
    visualize_progress(result, save_path=str(out))

    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


# ── HealthStatus + HealthThresholds ──────────────────────────────────────


def test_health_status_has_three_states():
    """Three states, not five — by design."""
    statuses = {s.value for s in HealthStatus}
    assert statuses == {"on_track", "at_risk", "off_track"}


def test_health_thresholds_defaults():
    """PMI/PMBOK guidance defaults."""
    t = HealthThresholds()
    assert t.spi_off_track == 0.9
    assert t.spi_at_risk == 1.0
    assert t.cpi_off_track == 0.9
    assert t.cpi_at_risk == 1.0


def test_baseline_dataclass_is_frozen():
    """Baseline is frozen — re-baselining is a governance decision, not a mutation."""
    baseline = Baseline(bac=1000.0, work_packages=[])
    with pytest.raises((AttributeError, TypeError)):
        baseline.bac = 2000.0  # type: ignore[misc]
