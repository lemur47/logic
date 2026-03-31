# test_montecarlo.py
"""Tests for the Monte Carlo schedule simulation standalone module.

Covers degenerate, typical, and skewed-input scenarios with deterministic
seeds for reproducibility. Expected ranges are derived from PERT formulae
and statistical reasoning about beta-PERT distributions.
"""

import numpy as np
import pytest
from montecarlo import (
    ScheduleNetwork,
    Task,
    compare_with_pert,
    probability_of_completion,
    sample_pert_duration,
    simulate_schedule,
)

# ── Single-Task Degenerate Cases ──────────────────────────────────────────


class TestSingleTaskDegenerate:
    """A single task is the simplest schedule — project duration equals task duration."""

    def test_single_task_deterministic(self):
        """When O == M == P, every simulation yields the same duration."""
        task = Task("Fixed", 5.0, 5.0, 5.0)
        result = simulate_schedule([task], n_simulations=1_000, seed=42)

        assert result.n_simulations == 1_000
        # All samples should be exactly 5.0
        np.testing.assert_array_equal(result.durations, 5.0)
        assert result.percentiles["P50"] == 5.0
        assert result.percentiles["P95"] == 5.0

    def test_single_task_symmetric(self):
        """A single symmetric task: MC mean should match PERT expected value closely."""
        task = Task("Sym", 4.0, 7.0, 10.0)
        result = simulate_schedule([task], n_simulations=50_000, seed=42)

        mc_mean = float(np.mean(result.durations))
        # PERT expected = (4 + 4*7 + 10) / 6 = 42/6 = 7.0
        assert abs(mc_mean - 7.0) < 0.1, f"MC mean {mc_mean} not close to PERT expected 7.0"

        # All samples must lie within [O, P]
        assert float(np.min(result.durations)) >= 4.0
        assert float(np.max(result.durations)) <= 10.0

    def test_single_task_critical_path(self):
        """A lone task is always on the critical path."""
        task = Task("Solo", 2.0, 5.0, 8.0)
        result = simulate_schedule([task], n_simulations=1_000, seed=42)

        assert result.critical_path_frequency["Solo"] == 1.0


# ── Three-Task Typical Project ───────────────────────────────────────────


class TestThreeTaskProject:
    """Three independent sequential tasks — the bread-and-butter scenario."""

    @pytest.fixture()
    def tasks(self):
        return [
            Task("Design", 3, 5, 10),
            Task("Build", 5, 8, 15),
            Task("Test", 2, 4, 8),
        ]

    def test_mc_mean_near_pert_expected(self, tasks):
        """MC mean should be within 2% of the PERT expected sum for sequential tasks."""
        pert_expected = sum(t.pert_expected for t in tasks)
        result = simulate_schedule(tasks, n_simulations=50_000, seed=42)
        mc_mean = float(np.mean(result.durations))

        tolerance = 0.02 * pert_expected
        assert abs(mc_mean - pert_expected) < tolerance, (
            f"MC mean {mc_mean:.2f} not within 2% of PERT expected {pert_expected:.2f}"
        )

    def test_percentile_ordering(self, tasks):
        """Percentiles must be monotonically increasing."""
        result = simulate_schedule(tasks, n_simulations=10_000, seed=42)

        assert result.percentiles["P50"] <= result.percentiles["P75"]
        assert result.percentiles["P75"] <= result.percentiles["P85"]
        assert result.percentiles["P85"] <= result.percentiles["P95"]

    def test_all_sequential_tasks_critical(self, tasks):
        """Without dependencies, tasks are sequential — all must be critical 100%."""
        result = simulate_schedule(tasks, n_simulations=5_000, seed=42)

        for task in tasks:
            assert result.critical_path_frequency[task.name] == 1.0

    def test_histogram_structure(self, tasks):
        """Histogram should have 50 bins (51 edges) and integer counts."""
        result = simulate_schedule(tasks, n_simulations=5_000, seed=42)

        assert len(result.histogram["bin_edges"]) == 51
        assert len(result.histogram["counts"]) == 50
        assert sum(result.histogram["counts"]) == 5_000

    def test_probability_of_completion(self, tasks):
        """Probability should be 0 below min possible and 1 above max possible."""
        result = simulate_schedule(tasks, n_simulations=10_000, seed=42)

        min_possible = sum(t.optimistic for t in tasks)
        max_possible = sum(t.pessimistic for t in tasks)

        assert probability_of_completion(result, min_possible - 1) == 0.0
        assert probability_of_completion(result, max_possible + 1) == 1.0

        # P50 target should yield roughly 50% probability
        p50_prob = probability_of_completion(result, result.percentiles["P50"])
        assert 0.45 <= p50_prob <= 0.55


# ── Skewed-Input Edge Cases ──────────────────────────────────────────────


class TestSkewedInputs:
    """Tasks with heavily right-skewed distributions reveal risk that PERT hides."""

    @pytest.fixture()
    def skewed_tasks(self):
        """Tasks where pessimistic is much further from M than optimistic."""
        return [
            Task("Skew-A", 4, 5, 20),  # M close to O, long right tail
            Task("Skew-B", 3, 4, 18),
            Task("Skew-C", 5, 6, 22),
        ]

    def test_mc_mean_exceeds_pert_mode_sum(self, skewed_tasks):
        """For right-skewed distributions, MC mean should exceed the sum of modes."""
        mode_sum = sum(t.most_likely for t in skewed_tasks)
        result = simulate_schedule(skewed_tasks, n_simulations=50_000, seed=42)
        mc_mean = float(np.mean(result.durations))

        assert mc_mean > mode_sum, (
            f"MC mean {mc_mean:.2f} should exceed mode sum {mode_sum:.2f} for skewed tasks"
        )

    def test_p50_within_5pct_of_pert_expected(self, skewed_tasks):
        """P50 should be within ±5% of the PERT expected value for symmetric-ish cases.

        For right-skewed distributions, P50 can be slightly below PERT expected
        because the mean is pulled up by the tail. We allow ±5% tolerance.
        """
        pert_expected = sum(t.pert_expected for t in skewed_tasks)
        result = simulate_schedule(skewed_tasks, n_simulations=50_000, seed=42)

        tolerance = 0.05 * pert_expected
        assert abs(result.percentiles["P50"] - pert_expected) < tolerance, (
            f"P50 {result.percentiles['P50']:.2f} not within 5% of "
            f"PERT expected {pert_expected:.2f}"
        )

    def test_p95_p50_gap_wider_than_symmetric(self):
        """Skewed tasks should produce a wider P95-P50 gap than symmetric ones."""
        symmetric = [
            Task("Sym-A", 4, 7, 10),
            Task("Sym-B", 3, 6, 9),
            Task("Sym-C", 5, 8, 11),
        ]
        skewed = [
            Task("Skew-A", 4, 7, 16),
            Task("Skew-B", 3, 6, 15),
            Task("Skew-C", 5, 8, 17),
        ]

        sym_result = simulate_schedule(symmetric, n_simulations=50_000, seed=42)
        skew_result = simulate_schedule(skewed, n_simulations=50_000, seed=42)

        sym_gap = sym_result.percentiles["P95"] - sym_result.percentiles["P50"]
        skew_gap = skew_result.percentiles["P95"] - skew_result.percentiles["P50"]

        assert skew_gap > sym_gap, (
            f"Skewed gap {skew_gap:.2f} should exceed symmetric gap {sym_gap:.2f}"
        )

    def test_near_zero_optimistic(self):
        """Edge case: optimistic very close to zero."""
        task = Task("Near-zero", 0.1, 5.0, 20.0)
        result = simulate_schedule([task], n_simulations=10_000, seed=42)

        assert float(np.min(result.durations)) >= 0.1
        assert float(np.max(result.durations)) <= 20.0


# ── Dependency Network ───────────────────────────────────────────────────


class TestDependencyNetwork:
    """Tasks with explicit dependencies form a DAG; critical path varies."""

    def test_parallel_paths_critical_frequency(self):
        """Two parallel predecessors feeding a single successor.

        Both A and B should appear on the critical path, and C (terminal)
        should be critical in every simulation.
        """
        tasks = [
            Task("A", 2, 4, 6),
            Task("B", 1, 3, 8),
            Task("C", 3, 5, 9, depends_on=("A", "B")),
        ]
        result = simulate_schedule(tasks, n_simulations=50_000, seed=42)

        assert result.critical_path_frequency["C"] > 0.99
        assert result.critical_path_frequency["A"] > 0.1
        assert result.critical_path_frequency["B"] > 0.1

        # A and B frequencies should sum to approximately 1.0
        ab_sum = result.critical_path_frequency["A"] + result.critical_path_frequency["B"]
        assert abs(ab_sum - 1.0) < 0.05

    def test_parallel_shorter_than_sequential(self):
        """Parallel execution should yield shorter project duration than sequential."""
        tasks_seq = [
            Task("X", 3, 5, 8),
            Task("Y", 3, 5, 8),
        ]

        tasks_par = [
            Task("X", 3, 5, 8),
            Task("Y", 3, 5, 8, depends_on=()),  # No dependency — but we need a joiner
            Task("Join", 0, 0, 0, depends_on=("X", "Y")),
        ]

        seq_result = simulate_schedule(tasks_seq, n_simulations=10_000, seed=42)
        par_result = simulate_schedule(tasks_par, n_simulations=10_000, seed=42)

        seq_mean = float(np.mean(seq_result.durations))
        par_mean = float(np.mean(par_result.durations))

        assert par_mean < seq_mean, (
            f"Parallel mean {par_mean:.2f} should be less than sequential {seq_mean:.2f}"
        )


# ── Validation and Error Handling ────────────────────────────────────────


class TestValidation:
    """Input validation and error conditions."""

    def test_task_invalid_ordering(self):
        """O > M or M > P should raise ValueError."""
        with pytest.raises(ValueError, match="cannot exceed most likely"):
            Task("Bad", 10, 5, 20)

        with pytest.raises(ValueError, match="cannot exceed pessimistic"):
            Task("Bad", 5, 25, 20)

    def test_task_negative_optimistic(self):
        """Negative optimistic should raise ValueError."""
        with pytest.raises(ValueError, match="must be >= 0"):
            Task("Neg", -1, 5, 10)

    def test_duplicate_task_names(self):
        """Duplicate names in a network should raise ValueError."""
        tasks = [
            Task("A", 1, 2, 3),
            Task("A", 4, 5, 6),
        ]
        with pytest.raises(ValueError, match="Duplicate"):
            ScheduleNetwork(tasks=tasks)

    def test_missing_dependency(self):
        """Referencing a non-existent dependency should raise ValueError."""
        tasks = [
            Task("A", 1, 2, 3, depends_on=("Ghost",)),
        ]
        with pytest.raises(ValueError, match="unknown task"):
            ScheduleNetwork(tasks=tasks)

    def test_circular_dependency(self):
        """Circular references should raise ValueError."""
        tasks = [
            Task("A", 1, 2, 3, depends_on=("B",)),
            Task("B", 1, 2, 3, depends_on=("A",)),
        ]
        with pytest.raises(ValueError, match="Circular"):
            ScheduleNetwork(tasks=tasks)


# ── Compare With PERT ────────────────────────────────────────────────────


class TestCompareWithPert:
    """The compare_with_pert helper should return both PERT and MC results."""

    def test_comparison_structure(self):
        tasks = [
            Task("A", 2, 4, 8),
            Task("B", 3, 5, 10),
        ]
        result = compare_with_pert(tasks)

        assert "pert" in result
        assert "montecarlo" in result
        assert "n_tasks" in result
        assert result["n_tasks"] == 2

        assert "expected" in result["pert"]
        assert "mean" in result["montecarlo"]
        assert "percentiles" in result["montecarlo"]


# ── Beta-PERT Sampler ────────────────────────────────────────────────────


class TestBetaPertSampler:
    """Direct tests of the sample_pert_duration function."""

    def test_samples_within_bounds(self):
        """All samples must lie within [O, P]."""
        samples = sample_pert_duration(2.0, 5.0, 14.0, size=10_000, rng=np.random.default_rng(42))
        assert float(np.min(samples)) >= 2.0
        assert float(np.max(samples)) <= 14.0

    def test_mean_near_pert_expected(self):
        """Sample mean should converge to PERT expected value."""
        samples = sample_pert_duration(2.0, 5.0, 14.0, size=100_000, rng=np.random.default_rng(42))
        pert_expected = (2 + 4 * 5 + 14) / 6  # 6.0
        assert abs(float(np.mean(samples)) - pert_expected) < 0.1

    def test_degenerate_all_equal(self):
        """When O == M == P, all samples equal that value."""
        samples = sample_pert_duration(7.0, 7.0, 7.0, size=100)
        np.testing.assert_array_equal(samples, 7.0)
