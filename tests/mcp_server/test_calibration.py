"""
Calibration-memory tests (opt-in estimation log + Bayesian summary).

Covers: the registration flag contract (no PMORUN_DB → exactly the four classic
tools, byte-identical stateless behaviour; PMORUN_DB set → the four calibration
tools join), the record → actual → summarise round-trip, the Bayesian summary
maths against hand-computed conjugate updates, the log-grounded
``estimate_from_history`` re-enablement, and the structured-error contract.

Implementation-grade Bayesian maths sweeps live in tests/bayesian/ — not
duplicated here.
"""

import importlib

import pytest

from mcp_server import calibration_tools, storage
from mcp_server.errors import ToolComputationError, ToolValidationError

V01_TOOLS = {
    "estimate_task_duration",
    "identify_schedule_risk",
    "compare_investment_options",
    "evaluate_project_health",
}
CALIBRATION_TOOLS = {
    "record_estimate",
    "record_actual",
    "summarise_calibration",
    "estimate_from_history",
}


@pytest.fixture
def log_db(tmp_path, monkeypatch):
    """A live calibration log: PMORUN_DB pointing at a fresh temp SQLite file."""
    db = tmp_path / "calibration.db"
    monkeypatch.setenv(storage.ENV_VAR, str(db))
    return db


def _reload_server():
    import mcp_server.server as server_module

    return importlib.reload(server_module)


@pytest.fixture
def restore_server_module():
    """Re-import server.py after a registration test so later tests see the
    module in its default (stateless) state regardless of test order."""
    yield
    import os

    os.environ.pop(storage.ENV_VAR, None)
    _reload_server()


# =============================================================================
# Registration flag contract
# =============================================================================


class TestRegistrationFlag:
    async def test_default_is_stateless_with_exactly_four_tools(
        self, monkeypatch, restore_server_module
    ):
        monkeypatch.delenv(storage.ENV_VAR, raising=False)
        server = _reload_server()
        names = {t.name for t in await server.mcp.list_tools()}
        assert names == V01_TOOLS

    async def test_env_var_registers_the_calibration_tools(self, log_db, restore_server_module):
        server = _reload_server()
        names = {t.name for t in await server.mcp.list_tools()}
        assert names == V01_TOOLS | CALIBRATION_TOOLS

    async def test_calibration_descriptions_lead_with_decision_question(
        self, log_db, restore_server_module
    ):
        server = _reload_server()
        for tool in await server.mcp.list_tools():
            if tool.name in CALIBRATION_TOOLS:
                assert tool.description and "Use when:" in tool.description

    def test_tools_refuse_to_run_without_the_env_var(self, monkeypatch):
        monkeypatch.delenv(storage.ENV_VAR, raising=False)
        with pytest.raises(ToolValidationError, match="not enabled"):
            calibration_tools.record_estimate("infra", 1, 2, 3)


# =============================================================================
# Record → actual → summarise round-trip
# =============================================================================


class TestRoundTrip:
    def test_record_estimate_returns_id_and_pert_stats(self, log_db):
        result = calibration_tools.record_estimate(
            "module-dev", 1.0, 2.0, 3.0, description="calibration log WI"
        )
        assert result["estimate_id"] == 1
        assert result["pert_expected"] == 2.0  # (1 + 4*2 + 3) / 6
        assert result["unit"] == "sessions"
        assert result["estimated_at"].endswith("+00:00")

    def test_record_actual_computes_delay_factor(self, log_db):
        row = calibration_tools.record_estimate("module-dev", 1.0, 2.0, 3.0)
        done = calibration_tools.record_actual(row["estimate_id"], 3.0)
        assert done["actual"] == 3.0
        assert done["delay_factor"] == 1.5  # 3.0 / 2.0
        assert done["actual_recorded_at"] is not None

    def test_record_actual_overwrite_is_a_correction(self, log_db):
        row = calibration_tools.record_estimate("module-dev", 1.0, 2.0, 3.0)
        calibration_tools.record_actual(row["estimate_id"], 3.0)
        corrected = calibration_tools.record_actual(row["estimate_id"], 2.5)
        assert corrected["actual"] == 2.5

    def test_round_trip_reaches_the_summary(self, log_db):
        row = calibration_tools.record_estimate("module-dev", 1.0, 2.0, 3.0)
        calibration_tools.record_actual(row["estimate_id"], 3.0)
        summary = calibration_tools.summarise_calibration()
        assert summary["n_observations"] == 1
        assert summary["observations_by_category"] == {"module-dev": 1}
        # One r=1.5 observation pulls the N(1.0, 0.25) prior towards 1.5.
        assert 1.0 < summary["delay_factor"] < 1.5


# =============================================================================
# Summary maths and filtering
# =============================================================================


class TestSummariseCalibration:
    def _seed(self, category: str, ratio: float, n: int) -> None:
        for _ in range(n):
            row = calibration_tools.record_estimate(category, 1.0, 2.0, 3.0)
            calibration_tools.record_actual(row["estimate_id"], 2.0 * ratio)

    def test_consistent_bias_converges_on_the_true_factor(self, log_db):
        """Five r=2.0 observations against the N(1.0, 0.25) prior with sigma=0.15:
        tau = 4 + 5/0.0225; mean = (4*1 + (5/0.0225)*2) / tau ≈ 1.982."""
        self._seed("infra", ratio=2.0, n=5)
        summary = calibration_tools.summarise_calibration()
        assert summary["n_observations"] == 5
        assert summary["delay_factor"] == pytest.approx(1.982, abs=0.005)
        assert "converging" in summary["confidence"] or "strong" in summary["confidence"]

    def test_empty_log_returns_the_prior(self, log_db):
        summary = calibration_tools.summarise_calibration()
        assert summary["n_observations"] == 0
        assert summary["delay_factor"] == 1.0
        assert summary["confidence"] == "no data — using prior"

    def test_category_filter_learns_from_that_category_only(self, log_db):
        self._seed("infra", ratio=2.0, n=3)
        self._seed("content", ratio=1.0, n=3)
        infra = calibration_tools.summarise_calibration("infra")
        assert infra["observations_by_category"] == {"infra": 3}
        assert infra["delay_factor"] > 1.5
        content = calibration_tools.summarise_calibration("content")
        assert content["delay_factor"] < 1.2

    def test_pert_expected_yields_adjusted_estimate(self, log_db):
        self._seed("infra", ratio=2.0, n=5)
        summary = calibration_tools.summarise_calibration("infra", pert_expected=10.0)
        adjusted = summary["adjusted_estimate"]
        assert adjusted["pert_expected"] == 10.0
        assert adjusted["adjusted_expected"] == pytest.approx(
            10.0 * summary["delay_factor"], abs=0.05
        )

    def test_invalid_pert_expected_is_a_validation_error(self, log_db):
        with pytest.raises(ToolValidationError):
            calibration_tools.summarise_calibration(pert_expected=0.0)


# =============================================================================
# estimate_from_history — unparked, grounded in the log
# =============================================================================


class TestEstimateFromHistory:
    def test_reads_past_actuals_from_the_log(self, log_db):
        for actual in (2.0, 3.0, 4.0):
            row = calibration_tools.record_estimate("auth-api", 1.0, 2.0, 3.0)
            calibration_tools.record_actual(row["estimate_id"], actual)
        result = calibration_tools.estimate_from_history(
            "auth-api", optimistic=1.0, complexity_factor=0.0
        )
        # Layer 2 base M is the median of the logged actuals (complexity 0 → no uplift).
        assert result["derived_most_likely"] == 3.0
        assert result["data_quality"] == "medium"

    def test_explicit_past_actuals_override_the_log(self, log_db):
        result = calibration_tools.estimate_from_history(
            "auth-api", optimistic=1.0, complexity_factor=0.0, past_actuals=[5.0]
        )
        assert result["derived_most_likely"] == 5.0

    def test_empty_category_is_a_validation_error(self, log_db):
        with pytest.raises(ToolValidationError, match="No recorded actuals"):
            calibration_tools.estimate_from_history("never-logged", optimistic=1.0)


# =============================================================================
# Structured-error contract
# =============================================================================


class TestErrors:
    def test_unknown_estimate_id_is_a_computation_error(self, log_db):
        with pytest.raises(ToolComputationError, match="No estimate with id"):
            calibration_tools.record_actual(999, 1.0)

    def test_inconsistent_three_point_estimate_is_structured(self, log_db):
        with pytest.raises(ToolComputationError):
            calibration_tools.record_estimate("infra", 5.0, 2.0, 3.0)

    def test_negative_actual_is_a_validation_error(self, log_db):
        row = calibration_tools.record_estimate("infra", 1.0, 2.0, 3.0)
        with pytest.raises(ToolValidationError):
            calibration_tools.record_actual(row["estimate_id"], -1.0)
