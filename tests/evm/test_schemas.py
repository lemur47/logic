"""Tests for EVM Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from app.evm.schemas import (
    ActualCompletion,
    BaselineCreate,
    EvaluateInput,
    EvmCalculateInput,
    EvmMetricsResult,
    HealthInput,
    HealthThresholdsInput,
    SnapshotResponse,
    WorkPackageInput,
)

# ── EvmCalculateInput ─────────────────────────────────────────────────────


class TestEvmCalculateInput:
    def test_valid(self):
        inp = EvmCalculateInput(pv=100, ev=90, ac=110, bac=500)
        assert inp.pv == 100

    def test_negative_pv_rejected(self):
        with pytest.raises(ValidationError):
            EvmCalculateInput(pv=-1, ev=90, ac=110, bac=500)

    def test_zero_bac_rejected(self):
        with pytest.raises(ValidationError):
            EvmCalculateInput(pv=100, ev=90, ac=110, bac=0)

    def test_missing_fields_rejected(self):
        with pytest.raises(ValidationError):
            EvmCalculateInput(pv=100)


# ── EvmMetricsResult ──────────────────────────────────────────────────────


class TestEvmMetricsResult:
    def test_inf_converted_to_none(self):
        result = EvmMetricsResult(
            sv=0,
            spi=float("inf"),
            cv=0,
            cpi=float("inf"),
            eac=float("inf"),
            etc=float("inf"),
            vac=float("inf"),
            tcpi=float("inf"),
            percent_complete=0,
            percent_spent=0,
        )
        assert result.spi is None
        assert result.cpi is None
        assert result.eac is None
        assert result.etc is None
        assert result.vac is None
        assert result.tcpi is None

    def test_finite_values_preserved(self):
        result = EvmMetricsResult(
            sv=-20,
            spi=0.8,
            cv=-30,
            cpi=0.7273,
            eac=275.0,
            etc=165.0,
            vac=-75.0,
            tcpi=1.3333,
            percent_complete=40.0,
            percent_spent=55.0,
        )
        assert result.spi == 0.8
        assert result.cpi == 0.7273

    def test_none_stays_none(self):
        result = EvmMetricsResult(
            sv=0,
            spi=None,
            cv=0,
            cpi=None,
            eac=None,
            etc=None,
            vac=None,
            tcpi=None,
            percent_complete=0,
            percent_spent=0,
        )
        assert result.spi is None


# ── HealthInput ───────────────────────────────────────────────────────────


class TestHealthInput:
    def test_valid_minimal(self):
        inp = HealthInput(spi=1.0, cpi=1.0)
        assert inp.thresholds is None

    def test_valid_with_thresholds(self):
        inp = HealthInput(
            spi=0.9,
            cpi=0.9,
            thresholds=HealthThresholdsInput(spi_off_track=0.85),
        )
        assert inp.thresholds.spi_off_track == 0.85

    def test_missing_spi_rejected(self):
        with pytest.raises(ValidationError):
            HealthInput(cpi=1.0)


# ── WorkPackageInput ──────────────────────────────────────────────────────


class TestWorkPackageInput:
    def test_valid(self):
        wp = WorkPackageInput(name="Auth", planned_value=5000)
        assert wp.weight is None

    def test_with_weight(self):
        wp = WorkPackageInput(name="Auth", planned_value=5000, weight=0.3)
        assert wp.weight == 0.3

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            WorkPackageInput(name="", planned_value=5000)

    def test_zero_planned_value_rejected(self):
        with pytest.raises(ValidationError):
            WorkPackageInput(name="Auth", planned_value=0)

    def test_negative_planned_value_rejected(self):
        with pytest.raises(ValidationError):
            WorkPackageInput(name="Auth", planned_value=-100)

    def test_weight_above_one_rejected(self):
        with pytest.raises(ValidationError):
            WorkPackageInput(name="Auth", planned_value=5000, weight=1.1)


# ── BaselineCreate ────────────────────────────────────────────────────────


class TestBaselineCreate:
    def test_valid(self):
        bl = BaselineCreate(
            name="Project",
            work_packages=[WorkPackageInput(name="A", planned_value=1000)],
        )
        assert len(bl.work_packages) == 1

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            BaselineCreate(
                name="",
                work_packages=[WorkPackageInput(name="A", planned_value=1000)],
            )

    def test_empty_work_packages_rejected(self):
        with pytest.raises(ValidationError):
            BaselineCreate(name="Project", work_packages=[])

    def test_with_description(self):
        bl = BaselineCreate(
            name="Project",
            description="A description",
            work_packages=[WorkPackageInput(name="A", planned_value=1000)],
        )
        assert bl.description == "A description"


# ── ActualCompletion ──────────────────────────────────────────────────────


class TestActualCompletion:
    def test_valid(self):
        ac = ActualCompletion(name="Auth", percent_complete=50.0)
        assert ac.percent_complete == 50.0

    def test_above_100_rejected(self):
        with pytest.raises(ValidationError):
            ActualCompletion(name="Auth", percent_complete=101)

    def test_below_zero_rejected(self):
        with pytest.raises(ValidationError):
            ActualCompletion(name="Auth", percent_complete=-1)


# ── EvaluateInput ─────────────────────────────────────────────────────────


class TestEvaluateInput:
    def test_valid(self):
        inp = EvaluateInput(
            percent_planned=50.0,
            actual_completions=[ActualCompletion(name="A", percent_complete=80)],
            actual_cost=5000,
        )
        assert inp.percent_planned == 50.0

    def test_percent_planned_above_100_rejected(self):
        with pytest.raises(ValidationError):
            EvaluateInput(percent_planned=101, actual_cost=1000)

    def test_negative_actual_cost_rejected(self):
        with pytest.raises(ValidationError):
            EvaluateInput(percent_planned=50, actual_cost=-1)

    def test_empty_completions_defaults_to_list(self):
        inp = EvaluateInput(percent_planned=50, actual_cost=1000)
        assert inp.actual_completions == []


# ── SnapshotResponse ──────────────────────────────────────────────────────


class TestSnapshotResponse:
    def test_inf_converted_to_none(self):
        from datetime import datetime

        snap = SnapshotResponse(
            id=1,
            baseline_id=1,
            percent_planned=50.0,
            actual_cost=100,
            pv=100,
            ev=0,
            sv=-100,
            spi=0.0,
            cv=-100,
            cpi=float("inf"),
            eac=float("inf"),
            etc=float("inf"),
            vac=float("inf"),
            tcpi=float("inf"),
            percent_complete=0,
            percent_spent=50,
            health_status="off_track",
            health_summary="Project off track",
            created_at=datetime(2024, 1, 1),
        )
        assert snap.cpi is None
        assert snap.eac is None
