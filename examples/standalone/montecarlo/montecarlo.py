"""
Monte Carlo Schedule Simulation

Generates a probability distribution over total project duration by running
thousands of simulated schedules. Each task's duration is sampled from a
beta-PERT distribution parameterised by three-point estimates (optimistic,
most likely, pessimistic) — the same inputs used by textbook PERT.

Where PERT gives you a single expected value and a Gaussian confidence band
(assuming independence), Monte Carlo gives you the full empirical distribution
plus critical-path frequency analysis when task dependencies are provided.

Usage:
    python montecarlo.py

Dependencies: scipy (for beta-PERT sampling), numpy. matplotlib optional for
visualisation.

License: MIT


Frozen teaching snapshot — NOT a mirror of the production core.

This module exists to make the maths readable on its own: a single file you can
open, run, and reason about without installing a web stack. It is deliberately
allowed to diverge in STRUCTURE from `app/montecarlo/core.py`, which is canonical and
is what the API, the MCP server and the site are built on.

So: do not sync this file field-for-field with the core, and do not treat a
structural difference here as a bug. Genuine defects — an unbounded allocation,
a wrong formula — are still fixed here, because this is public example code
someone may copy.

Canonical implementation: app/montecarlo/core.py
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import stats

# Monte Carlo allocates several (n_tasks, n_simulations) float64 arrays, so their
# product — not either factor alone — governs memory. 10_000_000 cells is ~80 MB
# per array and still admits a 1000-task network at the default 10_000 runs.
#
# Present here as well as in app/montecarlo/core.py because an unbounded
# allocation is a defect in its own right, not a sync obligation: this file is a
# public example someone may copy into their own code. Ported deliberately; the
# rest of this module is a frozen teaching snapshot (see the header note).
MAX_SIMULATION_CELLS = 10_000_000


def _check_allocation(n_tasks: int, n_simulations: int) -> None:
    """Reject over-large requests before any array is created."""
    if n_tasks * n_simulations > MAX_SIMULATION_CELLS:
        msg = (
            f"tasks × n_simulations ({n_tasks} × {n_simulations}) exceeds the "
            f"limit of {MAX_SIMULATION_CELLS}"
        )
        raise ValueError(msg)


# ── Core Data Structures ────────────────────────────────────────────────


@dataclass(frozen=True)
class Task:
    """A task with three-point duration estimates and optional dependencies.

    Args:
        name: Human-readable task identifier.
        optimistic: Best-case duration (O). Must be >= 0.
        most_likely: Most probable duration (M). Must be >= O.
        pessimistic: Worst-case duration (P). Must be >= M.
        depends_on: Names of tasks that must complete before this one starts.
    """

    name: str
    optimistic: float
    most_likely: float
    pessimistic: float
    depends_on: tuple[str, ...] = ()

    def __post_init__(self):
        if self.optimistic < 0:
            msg = f"Optimistic must be >= 0, got {self.optimistic}"
            raise ValueError(msg)
        if self.optimistic > self.most_likely:
            msg = f"Optimistic ({self.optimistic}) cannot exceed most likely ({self.most_likely})"
            raise ValueError(msg)
        if self.most_likely > self.pessimistic:
            msg = f"Most likely ({self.most_likely}) cannot exceed pessimistic ({self.pessimistic})"
            raise ValueError(msg)

    @property
    def pert_expected(self) -> float:
        """Textbook PERT expected value: (O + 4M + P) / 6."""
        return (self.optimistic + 4 * self.most_likely + self.pessimistic) / 6

    @property
    def pert_std_dev(self) -> float:
        """Textbook PERT standard deviation: (P - O) / 6."""
        return (self.pessimistic - self.optimistic) / 6


@dataclass(frozen=True)
class SimulationResult:
    """Output of a Monte Carlo schedule simulation.

    Contains the raw duration samples and pre-computed statistics for
    direct consumption by reports or downstream modules.
    """

    durations: np.ndarray
    n_simulations: int
    percentiles: dict[str, float]
    histogram: dict[str, list[float]]
    critical_path_frequency: dict[str, float]
    tasks: list[Task]

    class Config:
        arbitrary_types_allowed = True


@dataclass
class ScheduleNetwork:
    """A directed acyclic graph of tasks with dependency relationships.

    Validates the network topology on construction: checks for missing
    dependencies and circular references.
    """

    tasks: list[Task] = field(default_factory=list)

    def __post_init__(self):
        self._validate()

    def _validate(self):
        """Check for missing dependencies and cycles."""
        task_names = {t.name for t in self.tasks}

        # Check for duplicate names
        if len(task_names) != len(self.tasks):
            msg = "Duplicate task names detected"
            raise ValueError(msg)

        # Check for missing dependencies
        for task in self.tasks:
            for dep in task.depends_on:
                if dep not in task_names:
                    msg = f"Task '{task.name}' depends on unknown task '{dep}'"
                    raise ValueError(msg)

        # Check for cycles via topological sort
        _topological_sort(self.tasks)


# ── Core Functions ──────────────────────────────────────────────────────


def sample_pert_duration(
    optimistic: float,
    most_likely: float,
    pessimistic: float,
    size: int = 1,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Draw random samples from a beta-PERT distribution.

    The beta-PERT distribution is a beta distribution rescaled to [O, P]
    with the mode at M. The shape parameter lambda controls how strongly
    the distribution concentrates around the mode. The standard PERT
    convention uses lambda = 4.

    The alpha and beta parameters of the underlying Beta distribution:
        alpha = 1 + lambda * (M - O) / (P - O)
        beta  = 1 + lambda * (P - M) / (P - O)

    Args:
        optimistic: Best-case duration (O).
        most_likely: Most probable duration (M).
        pessimistic: Worst-case duration (P).
        size: Number of samples to draw.
        rng: NumPy random generator for reproducibility.

    Returns:
        Array of sampled durations in [O, P].
    """
    if rng is None:
        rng = np.random.default_rng()

    # Degenerate case: all three estimates are equal
    if optimistic == pessimistic:
        return np.full(size, optimistic)

    lam = 4  # Standard PERT shape parameter
    range_ = pessimistic - optimistic

    alpha = 1 + lam * (most_likely - optimistic) / range_
    beta_param = 1 + lam * (pessimistic - most_likely) / range_

    # Sample from Beta(alpha, beta) and rescale to [O, P]
    samples = stats.beta.rvs(alpha, beta_param, size=size, random_state=rng)
    return optimistic + samples * range_


def simulate_schedule(
    tasks: list[Task],
    n_simulations: int = 10_000,
    seed: int | None = None,
) -> SimulationResult:
    """Run Monte Carlo simulation on a schedule of tasks.

    For each simulation iteration:
    1. Sample a duration for every task from its beta-PERT distribution.
    2. Compute task finish times respecting dependency constraints
       (forward pass through the network).
    3. Record the total project duration (max finish time).
    4. Identify which tasks are on the critical path.

    If no dependencies are specified, tasks are assumed to be sequential
    (total = sum of durations) for backward compatibility with simple
    PERT aggregation.

    Args:
        tasks: List of Task objects defining the schedule.
        n_simulations: Number of simulation iterations (default 10,000).
        seed: Random seed for reproducibility. None for non-deterministic.

    Returns:
        SimulationResult with duration samples, percentiles, histogram,
        and critical-path frequency analysis.

    Raises:
        ValueError: if tasks x n_simulations would exceed MAX_SIMULATION_CELLS.
    """
    _check_allocation(len(tasks), n_simulations)

    rng = np.random.default_rng(seed)

    has_dependencies = any(t.depends_on for t in tasks)

    if has_dependencies:
        network = ScheduleNetwork(tasks=tasks)
        sorted_tasks = _topological_sort(network.tasks)
    else:
        sorted_tasks = tasks

    task_index = {t.name: i for i, t in enumerate(sorted_tasks)}
    n_tasks = len(sorted_tasks)

    # Pre-sample all durations: shape (n_tasks, n_simulations)
    all_samples = np.zeros((n_tasks, n_simulations))
    for i, task in enumerate(sorted_tasks):
        all_samples[i] = sample_pert_duration(
            task.optimistic,
            task.most_likely,
            task.pessimistic,
            size=n_simulations,
            rng=rng,
        )

    # Forward pass: compute finish times
    finish_times = np.zeros((n_tasks, n_simulations))
    start_times = np.zeros((n_tasks, n_simulations))

    if has_dependencies:
        for i, task in enumerate(sorted_tasks):
            if task.depends_on:
                # Start time = max finish time of all predecessors
                pred_finishes = np.array([finish_times[task_index[dep]] for dep in task.depends_on])
                start_times[i] = np.max(pred_finishes, axis=0)
            # else: start_times[i] remains 0
            finish_times[i] = start_times[i] + all_samples[i]
    else:
        # No dependencies: assume sequential execution
        for i in range(n_tasks):
            if i == 0:
                finish_times[i] = all_samples[i]
            else:
                finish_times[i] = finish_times[i - 1] + all_samples[i]
            start_times[i] = finish_times[i] - all_samples[i]

    # Project duration = max finish time across all tasks per simulation
    project_durations = np.max(finish_times, axis=0)

    # Critical-path frequency analysis
    critical_path_freq = _compute_critical_path_frequency(
        sorted_tasks,
        task_index,
        finish_times,
        start_times,
        all_samples,
        project_durations,
        has_dependencies,
    )

    # Compute percentiles
    percentiles = {
        "P50": float(np.percentile(project_durations, 50)),
        "P75": float(np.percentile(project_durations, 75)),
        "P85": float(np.percentile(project_durations, 85)),
        "P95": float(np.percentile(project_durations, 95)),
    }

    # Histogram data
    counts, bin_edges = np.histogram(project_durations, bins=50)
    histogram = {
        "bin_edges": [round(float(e), 2) for e in bin_edges],
        "counts": [int(c) for c in counts],
    }

    return SimulationResult(
        durations=project_durations,
        n_simulations=n_simulations,
        percentiles={k: round(v, 2) for k, v in percentiles.items()},
        histogram=histogram,
        critical_path_frequency={k: round(v, 4) for k, v in critical_path_freq.items()},
        tasks=tasks,
    )


def probability_of_completion(result: SimulationResult, target_duration: float) -> float:
    """Calculate the probability of completing within a target duration.

    Args:
        result: Output from simulate_schedule().
        target_duration: The deadline or target total duration.

    Returns:
        Probability (0.0 to 1.0) that the project finishes within
        the target duration.
    """
    return float(round(np.mean(result.durations <= target_duration), 4))


def compare_with_pert(tasks: list[Task]) -> dict:
    """Compare textbook PERT aggregation with Monte Carlo simulation.

    PERT assumes task independence and sums expected values and variances.
    Monte Carlo captures the actual distribution shape, dependency effects,
    and path convergence. This function runs both and returns them
    side-by-side for comparison.

    Args:
        tasks: List of Task objects.

    Returns:
        Dict with "pert" and "montecarlo" sub-dicts for comparison.
    """
    import math

    # Textbook PERT aggregation
    pert_expected = sum(t.pert_expected for t in tasks)
    pert_variance = sum(t.pert_std_dev**2 for t in tasks)
    pert_std_dev = math.sqrt(pert_variance)

    pert_result = {
        "expected": round(pert_expected, 2),
        "std_dev": round(pert_std_dev, 2),
        "range_68": [
            round(pert_expected - pert_std_dev, 2),
            round(pert_expected + pert_std_dev, 2),
        ],
        "range_95": [
            round(pert_expected - 2 * pert_std_dev, 2),
            round(pert_expected + 2 * pert_std_dev, 2),
        ],
    }

    # Monte Carlo
    mc_result = simulate_schedule(tasks, n_simulations=10_000, seed=42)
    mc_mean = round(float(np.mean(mc_result.durations)), 2)
    mc_std = round(float(np.std(mc_result.durations)), 2)

    mc_output = {
        "mean": mc_mean,
        "std_dev": mc_std,
        "percentiles": mc_result.percentiles,
        "critical_path_frequency": mc_result.critical_path_frequency,
    }

    return {
        "pert": pert_result,
        "montecarlo": mc_output,
        "n_tasks": len(tasks),
    }


# ── Internal Helpers ────────────────────────────────────────────────────


def _topological_sort(tasks: list[Task]) -> list[Task]:
    """Kahn's algorithm for topological sorting. Detects cycles."""
    task_map = {t.name: t for t in tasks}
    in_degree = {t.name: len(t.depends_on) for t in tasks}
    queue = [name for name, deg in in_degree.items() if deg == 0]
    sorted_names: list[str] = []

    # Build adjacency list (successors)
    successors: dict[str, list[str]] = {t.name: [] for t in tasks}
    for t in tasks:
        for dep in t.depends_on:
            successors[dep].append(t.name)

    while queue:
        name = queue.pop(0)
        sorted_names.append(name)
        for succ in successors[name]:
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                queue.append(succ)

    if len(sorted_names) != len(tasks):
        msg = "Circular dependency detected in task network"
        raise ValueError(msg)

    return [task_map[name] for name in sorted_names]


def _compute_critical_path_frequency(
    sorted_tasks: list[Task],
    task_index: dict[str, int],
    finish_times: np.ndarray,
    start_times: np.ndarray,
    durations: np.ndarray,
    project_durations: np.ndarray,
    has_dependencies: bool,
) -> dict[str, float]:
    """Determine how often each task appears on the critical path.

    A task is on the critical path in a given simulation if it has zero
    total float — i.e. delaying it would delay the project. For networks
    without dependencies (sequential), every task is always critical.

    Returns:
        Dict mapping task name to frequency (0.0 to 1.0).
    """
    n_sims = project_durations.shape[0]
    n_tasks = len(sorted_tasks)
    freq: dict[str, float] = {}

    if not has_dependencies:
        # Sequential: all tasks are always on the critical path
        for task in sorted_tasks:
            freq[task.name] = 1.0
        return freq

    # Backward pass to compute latest start/finish times
    latest_finish = np.zeros((n_tasks, n_sims))
    latest_start = np.zeros((n_tasks, n_sims))

    # Build successor map by index
    successors: dict[int, list[int]] = {i: [] for i in range(n_tasks)}
    for i, task in enumerate(sorted_tasks):
        for dep in task.depends_on:
            successors[task_index[dep]].append(i)

    # Initialise: tasks with no successors have latest_finish = project_duration
    for i in range(n_tasks):
        if not successors[i]:
            latest_finish[i] = project_durations
        else:
            latest_finish[i] = np.full(n_sims, np.inf)

    # Backward pass (reverse topological order)
    for i in range(n_tasks - 1, -1, -1):
        if successors[i]:
            succ_starts = np.array([latest_finish[s] - durations[s] for s in successors[i]])
            latest_finish[i] = np.min(succ_starts, axis=0)
        latest_start[i] = latest_finish[i] - durations[i]

    # Total float = latest_start - earliest_start
    # A task is critical if its total float is approximately zero
    tolerance = 1e-6
    for i, task in enumerate(sorted_tasks):
        total_float = latest_start[i] - start_times[i]
        critical_count = np.sum(np.abs(total_float) < tolerance)
        freq[task.name] = float(critical_count) / n_sims

    return freq


# ── Visualisation (optional, requires matplotlib) ───────────────────────


def visualise_distribution(
    result: SimulationResult,
    target_duration: float | None = None,
    save_path: str | None = None,
):
    """Plot the Monte Carlo duration distribution as a histogram.

    Shows percentile lines (P50, P75, P85, P95) and optionally a target
    deadline for visual comparison.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed — skipping visualisation.")
        return None

    fig, ax = plt.subplots(1, 1, figsize=(10, 5))

    ax.hist(result.durations, bins=50, color="#534AB7", alpha=0.7, edgecolor="white")

    # Percentile lines
    colours = {"P50": "#2196F3", "P75": "#FF9800", "P85": "#F44336", "P95": "#9C27B0"}
    for label, value in result.percentiles.items():
        ax.axvline(
            value, color=colours[label], linewidth=2, linestyle="--", label=f"{label}: {value:.1f}"
        )

    if target_duration is not None:
        prob = probability_of_completion(result, target_duration)
        ax.axvline(
            target_duration,
            color="#4CAF50",
            linewidth=2,
            linestyle="-",
            label=f"Target: {target_duration:.1f} ({prob:.0%} prob)",
        )

    ax.set_xlabel("Total project duration")
    ax.set_ylabel("Frequency")
    ax.set_title(f"Monte Carlo schedule simulation ({result.n_simulations:,} iterations)")
    ax.legend(loc="upper right")

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved to {save_path}")
    return fig


# ── Worked Examples (Self-Check) ────────────────────────────────────────


def _verify_beta_pert_distribution():
    """Verify that the beta-PERT sampler produces expected statistics.

    For a PERT distribution with O=2, M=5, P=14:
        Expected value = (2 + 4*5 + 14) / 6 = 6.0
        Std dev = (14 - 2) / 6 = 2.0

    With 100,000 samples, the sample mean should be close to 6.0.
    """
    print("=" * 60)
    print("VERIFICATION: Beta-PERT Distribution Sampling")
    print("=" * 60)

    samples = sample_pert_duration(2.0, 5.0, 14.0, size=100_000, rng=np.random.default_rng(42))

    sample_mean = float(np.mean(samples))
    sample_std = float(np.std(samples))
    sample_min = float(np.min(samples))
    sample_max = float(np.max(samples))

    pert_expected = (2 + 4 * 5 + 14) / 6  # 6.0

    print("\n  Input: O=2, M=5, P=14")
    print(f"  PERT expected: {pert_expected:.2f}")
    print(f"  Sample mean:   {sample_mean:.4f} (error: {abs(sample_mean - pert_expected):.4f})")
    print(f"  Sample std:    {sample_std:.4f}")
    print(f"  Sample range:  [{sample_min:.4f}, {sample_max:.4f}]")

    assert abs(sample_mean - pert_expected) < 0.1, f"Mean too far from expected: {sample_mean}"
    assert sample_min >= 2.0, f"Sample below optimistic: {sample_min}"
    assert sample_max <= 14.0, f"Sample above pessimistic: {sample_max}"
    print("  PASS")


def _verify_sequential_schedule():
    """Verify Monte Carlo on independent sequential tasks.

    Three tasks, no dependencies (sequential by default):
        Task A: O=2, M=4, P=8   → E=4.33
        Task B: O=3, M=5, P=10  → E=5.50
        Task C: O=1, M=3, P=7   → E=3.33

    PERT project expected = 4.33 + 5.50 + 3.33 = 13.17
    Monte Carlo mean should be close to this.
    """
    print("\n" + "=" * 60)
    print("VERIFICATION: Sequential Schedule (No Dependencies)")
    print("=" * 60)

    tasks = [
        Task("A", 2, 4, 8),
        Task("B", 3, 5, 10),
        Task("C", 1, 3, 7),
    ]

    pert_expected = sum(t.pert_expected for t in tasks)
    result = simulate_schedule(tasks, n_simulations=50_000, seed=42)
    mc_mean = float(np.mean(result.durations))

    print(f"\n  PERT expected total: {pert_expected:.2f}")
    print(f"  MC mean ({result.n_simulations:,} sims): {mc_mean:.2f}")
    print(f"  Error: {abs(mc_mean - pert_expected):.4f}")
    print(f"  Percentiles: {result.percentiles}")

    assert abs(mc_mean - pert_expected) < 0.2, f"MC mean too far: {mc_mean} vs {pert_expected}"

    # All tasks should be critical (sequential)
    for task_name, freq in result.critical_path_frequency.items():
        assert freq == 1.0, f"Task {task_name} should always be critical, got {freq}"
    print("  Critical path: all tasks at 100% (correct for sequential)")
    print("  PASS")


def _verify_dependency_network():
    """Verify Monte Carlo with task dependencies.

    Network:
        A (O=2, M=4, P=6)  ─┐
                              ├→ C (O=3, M=5, P=9)
        B (O=1, M=3, P=8)  ─┘

    C depends on both A and B. C starts when the slower of A/B finishes.
    Project duration = max(A, B) + C.

    Since B has wider variance and can be longer, B should appear on the
    critical path more often than a pure expected-value analysis suggests.
    """
    print("\n" + "=" * 60)
    print("VERIFICATION: Dependency Network")
    print("=" * 60)

    tasks = [
        Task("A", 2, 4, 6),
        Task("B", 1, 3, 8),
        Task("C", 3, 5, 9, depends_on=("A", "B")),
    ]

    result = simulate_schedule(tasks, n_simulations=50_000, seed=42)
    mc_mean = float(np.mean(result.durations))

    print("\n  Network: A ──┐")
    print("               ├→ C")
    print("          B ──┘")
    print(f"  MC mean ({result.n_simulations:,} sims): {mc_mean:.2f}")
    print(f"  Percentiles: {result.percentiles}")
    print("  Critical path frequency:")
    for name, freq in result.critical_path_frequency.items():
        print(f"    {name}: {freq:.1%}")

    # C should always be critical (it is the terminal task)
    assert result.critical_path_frequency["C"] > 0.99, (
        f"C should always be critical, got {result.critical_path_frequency['C']}"
    )

    # Both A and B should appear on the critical path sometimes
    assert result.critical_path_frequency["A"] > 0.1, "A should sometimes be critical"
    assert result.critical_path_frequency["B"] > 0.1, "B should sometimes be critical"

    # A + B frequencies should sum to approximately 1.0 (one is always critical)
    ab_sum = result.critical_path_frequency["A"] + result.critical_path_frequency["B"]
    assert abs(ab_sum - 1.0) < 0.05, f"A + B frequency should be ~1.0, got {ab_sum}"
    print(f"  A + B critical frequency sum: {ab_sum:.4f} (expected ~1.0)")
    print("  PASS")


def _demo_pert_vs_montecarlo():
    """Side-by-side comparison of PERT and Monte Carlo for a real project."""
    print("\n" + "=" * 60)
    print("DEMO: PERT vs Monte Carlo Comparison")
    print("=" * 60)

    tasks = [
        Task("Requirements", 3, 5, 10),
        Task("Design", 4, 7, 12, depends_on=("Requirements",)),
        Task("Backend", 8, 14, 25, depends_on=("Design",)),
        Task("Frontend", 6, 10, 18, depends_on=("Design",)),
        Task("Integration", 3, 5, 10, depends_on=("Backend", "Frontend")),
        Task("Testing", 4, 7, 14, depends_on=("Integration",)),
    ]

    comparison = compare_with_pert(tasks)

    pert = comparison["pert"]
    mc = comparison["montecarlo"]

    print(f"\n  {'':20s} {'PERT':>10s}  {'Monte Carlo':>12s}")
    print(f"  {'─' * 46}")
    print(f"  {'Expected/Mean':20s} {pert['expected']:10.2f}  {mc['mean']:12.2f}")
    print(f"  {'Std dev':20s} {pert['std_dev']:10.2f}  {mc['std_dev']:12.2f}")
    print(f"  {'68% low':20s} {pert['range_68'][0]:10.2f}  {'—':>12s}")
    print(f"  {'68% high':20s} {pert['range_68'][1]:10.2f}  {'—':>12s}")
    print(f"  {'95% low':20s} {pert['range_95'][0]:10.2f}  {'—':>12s}")
    print(f"  {'95% high':20s} {pert['range_95'][1]:10.2f}  {'—':>12s}")
    print(f"  {'P50':20s} {'—':>10s}  {mc['percentiles']['P50']:12.2f}")
    print(f"  {'P75':20s} {'—':>10s}  {mc['percentiles']['P75']:12.2f}")
    print(f"  {'P85':20s} {'—':>10s}  {mc['percentiles']['P85']:12.2f}")
    print(f"  {'P95':20s} {'—':>10s}  {mc['percentiles']['P95']:12.2f}")

    print("\n  Critical path frequency:")
    for name, freq in mc["critical_path_frequency"].items():
        bar = "#" * int(freq * 30)
        print(f"    {name:20s} {freq:6.1%}  {bar}")

    # Target date analysis
    print("\n  Target date analysis:")
    result = simulate_schedule(tasks, n_simulations=10_000, seed=42)
    for target in [45, 50, 55, 60, 65]:
        prob = probability_of_completion(result, float(target))
        print(f"    Complete within {target} days: {prob:.1%}")

    # Visualise if matplotlib available
    visualise_distribution(result, target_duration=55.0, save_path="montecarlo_histogram.png")


def _demo_risk_scenario():
    """Demonstrate how Monte Carlo reveals hidden risk in skewed estimates."""
    print("\n" + "=" * 60)
    print("DEMO: Hidden Risk in Skewed Estimates")
    print("=" * 60)

    # Symmetric tasks: O and P equally distant from M
    symmetric_tasks = [
        Task("Sym-A", 4, 7, 10),
        Task("Sym-B", 3, 6, 9),
        Task("Sym-C", 5, 8, 11),
    ]

    # Skewed tasks: same M but much wider pessimistic tail
    skewed_tasks = [
        Task("Skew-A", 4, 7, 16),
        Task("Skew-B", 3, 6, 15),
        Task("Skew-C", 5, 8, 17),
    ]

    sym_result = simulate_schedule(symmetric_tasks, n_simulations=50_000, seed=42)
    skew_result = simulate_schedule(skewed_tasks, n_simulations=50_000, seed=42)

    sym_pert = sum(t.pert_expected for t in symmetric_tasks)
    skew_pert = sum(t.pert_expected for t in skewed_tasks)

    print(f"\n  {'':20s} {'Symmetric':>12s}  {'Skewed':>12s}")
    print(f"  {'─' * 48}")
    print(f"  {'PERT expected':20s} {sym_pert:12.2f}  {skew_pert:12.2f}")
    print(
        f"  {'MC mean':20s} {float(np.mean(sym_result.durations)):12.2f}  {float(np.mean(skew_result.durations)):12.2f}"
    )
    print(
        f"  {'MC std dev':20s} {float(np.std(sym_result.durations)):12.2f}  {float(np.std(skew_result.durations)):12.2f}"
    )
    print(
        f"  {'P50':20s} {sym_result.percentiles['P50']:12.2f}  {skew_result.percentiles['P50']:12.2f}"
    )
    print(
        f"  {'P85':20s} {sym_result.percentiles['P85']:12.2f}  {skew_result.percentiles['P85']:12.2f}"
    )
    print(
        f"  {'P95':20s} {sym_result.percentiles['P95']:12.2f}  {skew_result.percentiles['P95']:12.2f}"
    )

    gap = skew_result.percentiles["P95"] - sym_result.percentiles["P95"]
    print(f"\n  P95 gap: {gap:.1f} days — skewed tasks carry {gap:.0f} days more risk")
    print("  This is the risk that PERT's Gaussian assumption hides.")


if __name__ == "__main__":
    _verify_beta_pert_distribution()
    _verify_sequential_schedule()
    _verify_dependency_network()
    _demo_pert_vs_montecarlo()
    _demo_risk_scenario()
