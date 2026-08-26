"""
Monte Carlo core logic unit tests.

Covers: Task dataclass, ScheduleNetwork validation, beta-PERT sampler,
simulate_schedule, probability_of_completion, compare_with_pert,
and critical-path frequency analysis.
"""

import numpy as np
import pytest

from app.montecarlo.core import (
    ScheduleNetwork,
    Task,
    _topological_sort,
    compare_with_pert,
    probability_of_completion,
    sample_pert_duration,
    simulate_schedule,
)

# =============================================================================
# Task Dataclass
# =============================================================================


class TestTask:
    def test_defaults(self):
        t = Task("A", 2, 5, 10)
        assert t.name == "A"
        assert t.depends_on == ()

    def test_pert_expected(self):
        t = Task("A", 2, 5, 14)
        assert t.pert_expected == pytest.approx(6.0)

    def test_pert_std_dev(self):
        t = Task("A", 2, 5, 14)
        assert t.pert_std_dev == pytest.approx(2.0)

    def test_negative_optimistic_raises(self):
        with pytest.raises(ValueError, match="Optimistic must be >= 0"):
            Task("A", -1, 5, 10)

    def test_optimistic_exceeds_most_likely_raises(self):
        with pytest.raises(ValueError, match="cannot exceed most likely"):
            Task("A", 6, 5, 10)

    def test_most_likely_exceeds_pessimistic_raises(self):
        with pytest.raises(ValueError, match="cannot exceed pessimistic"):
            Task("A", 2, 11, 10)

    def test_degenerate_equal_estimates(self):
        t = Task("A", 5, 5, 5)
        assert t.pert_expected == pytest.approx(5.0)
        assert t.pert_std_dev == pytest.approx(0.0)

    def test_dependencies(self):
        t = Task("C", 3, 5, 9, depends_on=("A", "B"))
        assert t.depends_on == ("A", "B")


# =============================================================================
# ScheduleNetwork Validation
# =============================================================================


class TestScheduleNetwork:
    def test_valid_network(self):
        tasks = [
            Task("A", 2, 4, 6),
            Task("B", 1, 3, 8),
            Task("C", 3, 5, 9, depends_on=("A", "B")),
        ]
        network = ScheduleNetwork(tasks=tasks)
        assert len(network.tasks) == 3

    def test_duplicate_names_raises(self):
        tasks = [Task("A", 2, 4, 6), Task("A", 1, 3, 8)]
        with pytest.raises(ValueError, match="Duplicate task names"):
            ScheduleNetwork(tasks=tasks)

    def test_missing_dependency_raises(self):
        tasks = [Task("A", 2, 4, 6, depends_on=("X",))]
        with pytest.raises(ValueError, match="unknown task 'X'"):
            ScheduleNetwork(tasks=tasks)

    def test_circular_dependency_raises(self):
        tasks = [
            Task("A", 2, 4, 6, depends_on=("B",)),
            Task("B", 1, 3, 8, depends_on=("A",)),
        ]
        with pytest.raises(ValueError, match="Circular dependency"):
            ScheduleNetwork(tasks=tasks)


# =============================================================================
# Beta-PERT Sampler
# =============================================================================


class TestBetaPertSampler:
    def test_degenerate_case(self):
        """When O == M == P, all samples should equal that value."""
        samples = sample_pert_duration(5.0, 5.0, 5.0, size=100)
        assert np.all(samples == 5.0)

    def test_samples_within_bounds(self):
        """All samples must be within [O, P]."""
        samples = sample_pert_duration(2.0, 5.0, 14.0, size=10_000, rng=np.random.default_rng(42))
        assert np.all(samples >= 2.0)
        assert np.all(samples <= 14.0)

    def test_mean_close_to_pert_expected(self):
        """Sample mean should converge to PERT expected value."""
        samples = sample_pert_duration(2.0, 5.0, 14.0, size=100_000, rng=np.random.default_rng(42))
        pert_expected = (2 + 4 * 5 + 14) / 6  # 6.0
        assert float(np.mean(samples)) == pytest.approx(pert_expected, abs=0.1)

    def test_symmetric_distribution(self):
        """Symmetric estimates should produce a symmetric distribution."""
        samples = sample_pert_duration(2.0, 6.0, 10.0, size=50_000, rng=np.random.default_rng(42))
        mean = float(np.mean(samples))
        assert mean == pytest.approx(6.0, abs=0.1)

    def test_right_skewed_distribution(self):
        """Right-skewed estimates should produce a right-skewed distribution."""
        samples = sample_pert_duration(2.0, 4.0, 14.0, size=50_000, rng=np.random.default_rng(42))
        median = float(np.median(samples))
        mean = float(np.mean(samples))
        # Right-skewed: mean > median
        assert mean > median

    def test_reproducibility_with_seed(self):
        """Same rng seed should produce identical samples."""
        s1 = sample_pert_duration(2.0, 5.0, 10.0, size=100, rng=np.random.default_rng(42))
        s2 = sample_pert_duration(2.0, 5.0, 10.0, size=100, rng=np.random.default_rng(42))
        np.testing.assert_array_equal(s1, s2)


# =============================================================================
# Simulate Schedule
# =============================================================================


class TestSimulateSchedule:
    def test_single_task(self):
        """Single degenerate task: all simulations should equal that value."""
        tasks = [Task("A", 5, 5, 5)]
        result = simulate_schedule(tasks, n_simulations=1000, seed=42)
        assert result.n_simulations == 1000
        assert float(np.mean(result.durations)) == pytest.approx(5.0)
        assert result.percentiles["P50"] == pytest.approx(5.0)

    def test_sequential_three_tasks(self):
        """Sequential tasks: MC mean should be close to PERT sum."""
        tasks = [
            Task("A", 2, 4, 8),
            Task("B", 3, 5, 10),
            Task("C", 1, 3, 7),
        ]
        pert_expected = sum(t.pert_expected for t in tasks)
        result = simulate_schedule(tasks, n_simulations=50_000, seed=42)
        mc_mean = float(np.mean(result.durations))
        assert mc_mean == pytest.approx(pert_expected, rel=0.02)

    def test_percentile_ordering(self):
        """Percentiles must be monotonically increasing."""
        tasks = [Task("A", 2, 5, 14), Task("B", 3, 6, 12)]
        result = simulate_schedule(tasks, n_simulations=10_000, seed=42)
        p = result.percentiles
        assert p["P50"] <= p["P75"] <= p["P85"] <= p["P95"]

    def test_histogram_structure(self):
        """Histogram should have 50 bins and counts summing to n_simulations."""
        tasks = [Task("A", 2, 5, 10)]
        result = simulate_schedule(tasks, n_simulations=5000, seed=42)
        assert len(result.histogram["counts"]) == 50
        assert len(result.histogram["bin_edges"]) == 51
        assert sum(result.histogram["counts"]) == 5000

    def test_empty_tasks_raises(self):
        with pytest.raises(ValueError, match="At least one task"):
            simulate_schedule([], n_simulations=100)

    def test_reproducibility(self):
        """Same seed should produce identical results."""
        tasks = [Task("A", 2, 5, 10), Task("B", 3, 6, 12)]
        r1 = simulate_schedule(tasks, n_simulations=1000, seed=42)
        r2 = simulate_schedule(tasks, n_simulations=1000, seed=42)
        assert r1.percentiles == r2.percentiles

    def test_dependency_network(self):
        """Tasks with dependencies: project duration < sum of all tasks."""
        tasks = [
            Task("A", 2, 4, 6),
            Task("B", 1, 3, 8),
            Task("C", 3, 5, 9, depends_on=("A", "B")),
        ]
        result = simulate_schedule(tasks, n_simulations=10_000, seed=42)
        # With parallel paths, project duration should be less than sequential sum
        sequential_sum = sum(t.pert_expected for t in tasks)
        mc_mean = float(np.mean(result.durations))
        assert mc_mean < sequential_sum


# =============================================================================
# Critical Path Frequency
# =============================================================================


class TestCriticalPathFrequency:
    def test_sequential_all_critical(self):
        """Sequential tasks: all should be 100% critical."""
        tasks = [
            Task("A", 2, 4, 8),
            Task("B", 3, 5, 10),
        ]
        result = simulate_schedule(tasks, n_simulations=1000, seed=42)
        for freq in result.critical_path_frequency.values():
            assert freq == 1.0

    def test_parallel_paths(self):
        """Terminal task should always be critical."""
        tasks = [
            Task("A", 2, 4, 6),
            Task("B", 1, 3, 8),
            Task("C", 3, 5, 9, depends_on=("A", "B")),
        ]
        result = simulate_schedule(tasks, n_simulations=50_000, seed=42)
        # C is always critical (terminal)
        assert result.critical_path_frequency["C"] > 0.99

    def test_parallel_paths_sum(self):
        """Parallel source tasks: critical frequencies should sum to ~1.0."""
        tasks = [
            Task("A", 2, 4, 6),
            Task("B", 1, 3, 8),
            Task("C", 3, 5, 9, depends_on=("A", "B")),
        ]
        result = simulate_schedule(tasks, n_simulations=50_000, seed=42)
        ab_sum = result.critical_path_frequency["A"] + result.critical_path_frequency["B"]
        assert ab_sum == pytest.approx(1.0, abs=0.05)

    def test_both_paths_appear(self):
        """Both parallel tasks should appear on critical path sometimes."""
        tasks = [
            Task("A", 2, 4, 6),
            Task("B", 1, 3, 8),
            Task("C", 3, 5, 9, depends_on=("A", "B")),
        ]
        result = simulate_schedule(tasks, n_simulations=50_000, seed=42)
        assert result.critical_path_frequency["A"] > 0.1
        assert result.critical_path_frequency["B"] > 0.1


# =============================================================================
# Probability of Completion
# =============================================================================


class TestProbabilityOfCompletion:
    def test_certain_completion(self):
        """Target well above max should give probability ~1.0."""
        tasks = [Task("A", 2, 5, 10)]
        result = simulate_schedule(tasks, n_simulations=5000, seed=42)
        prob = probability_of_completion(result, 100.0)
        assert prob == pytest.approx(1.0)

    def test_impossible_completion(self):
        """Target well below min should give probability ~0.0."""
        tasks = [Task("A", 5, 8, 15)]
        result = simulate_schedule(tasks, n_simulations=5000, seed=42)
        prob = probability_of_completion(result, 1.0)
        assert prob == pytest.approx(0.0)

    def test_median_gives_approximately_50_percent(self):
        """Target at P50 should give probability ~50%."""
        tasks = [Task("A", 2, 5, 14), Task("B", 3, 6, 12)]
        result = simulate_schedule(tasks, n_simulations=10_000, seed=42)
        prob = probability_of_completion(result, result.percentiles["P50"])
        assert prob == pytest.approx(0.5, abs=0.05)


# =============================================================================
# Compare with PERT
# =============================================================================


class TestCompareWithPert:
    def test_structure(self):
        """Comparison result should contain both pert and montecarlo sections."""
        tasks = [Task("A", 2, 5, 10), Task("B", 3, 6, 12)]
        result = compare_with_pert(tasks, seed=42)
        assert "pert" in result
        assert "montecarlo" in result
        assert "n_tasks" in result
        assert result["n_tasks"] == 2

    def test_pert_section(self):
        """PERT section should have expected, std_dev, ranges."""
        tasks = [Task("A", 2, 5, 10)]
        result = compare_with_pert(tasks, seed=42)
        pert = result["pert"]
        assert "expected" in pert
        assert "std_dev" in pert
        assert "range_68" in pert
        assert "range_95" in pert

    def test_montecarlo_section(self):
        """Monte Carlo section should have mean, std_dev, percentiles."""
        tasks = [Task("A", 2, 5, 10)]
        result = compare_with_pert(tasks, seed=42)
        mc = result["montecarlo"]
        assert "mean" in mc
        assert "std_dev" in mc
        assert "percentiles" in mc
        assert "critical_path_frequency" in mc

    def test_pert_expected_matches_formula(self):
        """PERT expected should match the textbook formula."""
        tasks = [Task("A", 2, 5, 14), Task("B", 3, 6, 12)]
        result = compare_with_pert(tasks, seed=42)
        expected = sum(t.pert_expected for t in tasks)
        assert result["pert"]["expected"] == pytest.approx(expected, abs=0.01)

    def test_mc_mean_close_to_pert_for_sequential(self):
        """For independent sequential tasks, MC mean ≈ PERT expected."""
        tasks = [
            Task("A", 4, 7, 10),
            Task("B", 3, 6, 9),
        ]
        result = compare_with_pert(tasks, seed=42)
        assert result["montecarlo"]["mean"] == pytest.approx(result["pert"]["expected"], rel=0.05)


# =============================================================================
# Topological Sort
# =============================================================================


class TestTopologicalSort:
    def test_linear_chain(self):
        tasks = [
            Task("A", 1, 2, 3),
            Task("B", 1, 2, 3, depends_on=("A",)),
            Task("C", 1, 2, 3, depends_on=("B",)),
        ]
        sorted_tasks = _topological_sort(tasks)
        names = [t.name for t in sorted_tasks]
        assert names.index("A") < names.index("B") < names.index("C")

    def test_diamond_network(self):
        tasks = [
            Task("A", 1, 2, 3),
            Task("B", 1, 2, 3, depends_on=("A",)),
            Task("C", 1, 2, 3, depends_on=("A",)),
            Task("D", 1, 2, 3, depends_on=("B", "C")),
        ]
        sorted_tasks = _topological_sort(tasks)
        names = [t.name for t in sorted_tasks]
        assert names.index("A") < names.index("B")
        assert names.index("A") < names.index("C")
        assert names.index("B") < names.index("D")
        assert names.index("C") < names.index("D")

    def test_cycle_detection(self):
        tasks = [
            Task("A", 1, 2, 3, depends_on=("C",)),
            Task("B", 1, 2, 3, depends_on=("A",)),
            Task("C", 1, 2, 3, depends_on=("B",)),
        ]
        with pytest.raises(ValueError, match="Circular dependency"):
            _topological_sort(tasks)


# =============================================================================
# Skewed Input Edge Cases
# =============================================================================


class TestSkewedInputs:
    def test_right_skewed_p95_higher(self):
        """Right-skewed tasks should have P95 further from mean than symmetric."""
        symmetric = [Task("A", 4, 7, 10), Task("B", 3, 6, 9)]
        skewed = [Task("A", 4, 7, 16), Task("B", 3, 6, 15)]

        sym_result = simulate_schedule(symmetric, n_simulations=50_000, seed=42)
        skew_result = simulate_schedule(skewed, n_simulations=50_000, seed=42)

        assert skew_result.percentiles["P95"] > sym_result.percentiles["P95"]

    def test_skewed_mean_greater_than_median(self):
        """Right-skewed tasks should have mean > P50."""
        tasks = [Task("A", 2, 4, 16), Task("B", 1, 3, 14)]
        result = simulate_schedule(tasks, n_simulations=50_000, seed=42)
        mc_mean = float(np.mean(result.durations))
        assert mc_mean > result.percentiles["P50"]


# =============================================================================
# Dependency-Edge Budget (2026-08-21 audit, finding confirmed 2026-08-25)
# =============================================================================


class TestDependencyEdgeBudget:
    """The allocation guard bounded tasks and risk classes but never edges.

    `_forward_pass` materialises one `(len(depends_on), n_simulations)` array
    per task, so the sum of dependency-list lengths is an allocation dimension
    in its own right. Measured at 200 tasks x 2,000 simulations: 199,000
    repeated edges peaked at 6.4 GB against 22 MB once de-duplicated.

    Memory is the metric these assert on, and deliberately so — it is
    deterministic to the decimal across runs, while wall-clock for the same
    input spans 1.9x and would flake.
    """

    def test_repeated_dependencies_are_de_duplicated(self):
        """Repeated names are semantic no-ops; keeping them is pure cost."""
        t = Task("B", 1, 2, 3, depends_on=("A", "A", "A"))
        assert t.depends_on == ("A",)

    def test_de_duplication_preserves_first_occurrence_order(self):
        t = Task("C", 1, 2, 3, depends_on=("B", "A", "B"))
        assert t.depends_on == ("B", "A")

    def test_de_duplication_does_not_change_the_result(self):
        """Dedup is output-preserving, which is what makes it safe as the fix."""
        repeated = [
            Task("A", 1, 2, 3),
            Task("B", 1, 2, 3, depends_on=("A",) * 500),
        ]
        single = [
            Task("A", 1, 2, 3),
            Task("B", 1, 2, 3, depends_on=("A",)),
        ]
        assert (
            simulate_schedule(repeated, n_simulations=2_000, seed=42).percentiles
            == simulate_schedule(single, n_simulations=2_000, seed=42).percentiles
        )

    def test_edge_budget_rejects_a_dense_distinct_graph(self):
        """Dedup closes repeated edges; distinct ones need their own bound."""
        tasks = [Task("t0", 1, 2, 3)] + [
            Task(f"t{i}", 1, 2, 3, depends_on=tuple(f"t{j}" for j in range(i)))
            for i in range(1, 700)
        ]
        with pytest.raises(ValueError, match="dependency_edges"):
            simulate_schedule(tasks, n_simulations=10_000)

    def test_edge_budget_still_admits_a_realistic_network(self):
        """A 1000-task chain at the default 10,000 runs is legitimate input."""
        tasks = [Task("t0", 1, 2, 3)] + [
            Task(f"t{i}", 1, 2, 3, depends_on=(f"t{i - 1}",)) for i in range(1, 1_000)
        ]
        simulate_schedule(tasks, n_simulations=10, seed=42)  # must not raise

    def test_the_confirmed_denial_of_service_input_stays_bounded(self):
        """The exact reproduction from the audit, asserted on peak memory."""
        import tracemalloc

        tasks = [Task("t0", 1, 2, 3)] + [
            Task(f"t{i}", 1, 2, 3, depends_on=("t0",) * 1_000) for i in range(1, 200)
        ]
        tracemalloc.start()
        try:
            simulate_schedule(tasks, n_simulations=2_000, seed=42)
            peak_mb = tracemalloc.get_traced_memory()[1] / 1e6
        finally:
            tracemalloc.stop()

        # Measured 6416 MB before the fix, 22.4 MB after. Any ceiling in
        # between distinguishes them; 200 MB leaves ~9x margin on both sides.
        assert peak_mb < 200, f"peak {peak_mb:.1f} MB — the edge cost is back"
