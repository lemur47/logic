"""Golden-value and degenerate-guard tests for the shared simulation pipeline.

Two jobs:

1. **Parity.** simulate_schedule and simulate_with_drift were collapsed onto one
   forward pass and one summariser. That is a pure refactor, so fixed-seed output
   must be bit-identical to the pre-refactor baseline captured in
   fixtures/pipeline-golden.json. Regenerate with
   `uv run python tests/montecarlo/generate_pipeline_fixtures.py` only with a
   recorded reason — an unexplained diff here is a regression, not a fixture that
   needs updating.

2. **The degenerate-histogram guard.** It previously existed only on the drift
   path. On a zero-variance schedule the plain path fabricated a +/-0.5 spread
   (50 bins over 4.5..5.5 for a constant 5.0), which misrepresents a point mass
   as a distribution. Sharing the summariser gives both paths the guard.
"""

import json
from pathlib import Path

import numpy as np
import pytest

from app.montecarlo.core import (
    DriftConfig,
    DriftTask,
    Posterior,
    RiskClass,
    Task,
    simulate_schedule,
    simulate_with_drift,
)

from .generate_pipeline_fixtures import (  # noqa: F401 — reuse the generator's scenarios
    N_SIMS,
    SEED,
    _capture,
    _drift_config,
    _drift_dependent,
    _drift_independent,
    _plain_dependent,
    _plain_independent,
)

FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "pipeline-golden.json").read_text())


def _run(case: str):
    if case == "plain_independent":
        return simulate_schedule(_plain_independent(), n_simulations=N_SIMS, seed=SEED)
    if case == "plain_dependent":
        return simulate_schedule(_plain_dependent(), n_simulations=N_SIMS, seed=SEED)
    if case == "drift_independent":
        return simulate_with_drift(_drift_independent(), _drift_config(), n_simulations=N_SIMS)
    if case == "drift_dependent":
        return simulate_with_drift(_drift_dependent(), _drift_config(), n_simulations=N_SIMS)
    raise AssertionError(f"unknown case {case}")


class TestPipelineParity:
    """Fixed seeds must produce byte-identical output across the refactor."""

    @pytest.mark.parametrize(
        "case",
        ["plain_independent", "plain_dependent", "drift_independent", "drift_dependent"],
    )
    def test_matches_golden(self, case: str):
        assert _capture(_run(case)) == FIXTURES[case]

    def test_fixtures_cover_both_paths(self):
        """Guard against a future edit quietly dropping a path from the net."""
        cases = {k for k in FIXTURES if not k.startswith("_")}
        assert any(c.startswith("plain") for c in cases)
        assert any(c.startswith("drift") for c in cases)


class TestDegenerateHistogramGuard:
    """A zero-variance schedule is a point mass and must be reported as one.

    Before the shared summariser, only the drift path handled this. The plain
    path returned 50 bins spanning 4.5..5.5 for a constant 5.0 — inventing
    uncertainty that the data does not contain.
    """

    @staticmethod
    def _degenerate_tasks():
        return [Task("A", 5.0, 5.0, 5.0)]

    @staticmethod
    def _degenerate_drift():
        tasks = [DriftTask("A", 5.0, 5.0, 5.0)]
        cfg = DriftConfig(
            risk_classes=(RiskClass(name="x", posterior=Posterior(mu=1.0, sigma=0.0)),),
            seed=SEED,
        )
        return tasks, cfg

    def test_plain_path_collapses_to_single_spike_bin(self):
        """WOULD HAVE FAILED before the refactor — the plain path had no guard."""
        result = simulate_schedule(self._degenerate_tasks(), n_simulations=1000, seed=SEED)

        assert float(np.ptp(result.durations)) == 0.0, "precondition: zero variance"
        assert result.histogram["counts"] == [1000]
        assert result.histogram["bin_edges"] == [5.0, 5.0]

    def test_plain_path_invents_no_spread(self):
        """The specific old defect: edges must not straddle a value with no range."""
        result = simulate_schedule(self._degenerate_tasks(), n_simulations=1000, seed=SEED)
        edges = result.histogram["bin_edges"]

        assert min(edges) == max(edges) == 5.0
        assert len(result.histogram["counts"]) == 1, "50 bins here means the guard regressed"

    def test_both_paths_agree_on_degenerate_shape(self):
        """The whole point of one summariser: no path-dependent behaviour."""
        plain = simulate_schedule(self._degenerate_tasks(), n_simulations=1000, seed=SEED)
        tasks, cfg = self._degenerate_drift()
        drift = simulate_with_drift(tasks, cfg, n_simulations=1000)

        assert plain.histogram == drift.histogram

    def test_counts_still_sum_to_simulation_count(self):
        """The spike bin must account for every sample, not collapse them away."""
        result = simulate_schedule(self._degenerate_tasks(), n_simulations=777, seed=SEED)
        assert sum(result.histogram["counts"]) == 777


class TestNonDegenerateUnaffected:
    """The guard must not fire on ordinary input."""

    def test_normal_schedule_keeps_full_histogram(self):
        result = simulate_schedule(_plain_independent(), n_simulations=1000, seed=SEED)
        assert len(result.histogram["counts"]) == 50
        assert len(result.histogram["bin_edges"]) == 51
        assert sum(result.histogram["counts"]) == 1000
