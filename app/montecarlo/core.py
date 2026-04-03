"""
Monte Carlo Schedule Simulation — Core Logic.

Generates a probability distribution over total project duration by running
thousands of simulated schedules. Each task's duration is sampled from a
beta-PERT distribution parameterised by three-point estimates (optimistic,
most likely, pessimistic).

Ported from examples/standalone/montecarlo/montecarlo.py (WI#168).

License: MIT
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy import stats

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
        """Check for duplicate names, missing dependencies, and cycles."""
        task_names = {t.name for t in self.tasks}

        if len(task_names) != len(self.tasks):
            msg = "Duplicate task names detected"
            raise ValueError(msg)

        for task in self.tasks:
            for dep in task.depends_on:
                if dep not in task_names:
                    msg = f"Task '{task.name}' depends on unknown task '{dep}'"
                    raise ValueError(msg)

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
    the distribution concentrates around the mode. Standard PERT uses
    lambda = 4.

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
    samples = np.asarray(stats.beta.rvs(alpha, beta_param, size=size, random_state=rng))
    return optimistic + samples * range_


def simulate_schedule(
    tasks: list[Task],
    n_simulations: int = 10_000,
    seed: int | None = None,
) -> SimulationResult:
    """Run Monte Carlo simulation on a schedule of tasks.

    For each simulation iteration:
    1. Sample a duration for every task from its beta-PERT distribution.
    2. Compute task finish times respecting dependency constraints.
    3. Record the total project duration (max finish time).
    4. Identify which tasks are on the critical path.

    If no dependencies are specified, tasks are assumed sequential.

    Args:
        tasks: List of Task objects defining the schedule.
        n_simulations: Number of simulation iterations (default 10,000).
        seed: Random seed for reproducibility. None for non-deterministic.

    Returns:
        SimulationResult with duration samples, percentiles, histogram,
        and critical-path frequency analysis.
    """
    if not tasks:
        msg = "At least one task is required"
        raise ValueError(msg)

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
                pred_finishes = np.array([finish_times[task_index[dep]] for dep in task.depends_on])
                start_times[i] = np.max(pred_finishes, axis=0)
            finish_times[i] = start_times[i] + all_samples[i]
    else:
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


def compare_with_pert(tasks: list[Task], seed: int | None = 42) -> dict:
    """Compare textbook PERT aggregation with Monte Carlo simulation.

    PERT assumes task independence and sums expected values and variances.
    Monte Carlo captures the actual distribution shape, dependency effects,
    and path convergence.

    Args:
        tasks: List of Task objects.
        seed: Random seed for reproducibility.

    Returns:
        Dict with "pert" and "montecarlo" sub-dicts for comparison.
    """
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

    mc_result = simulate_schedule(tasks, n_simulations=10_000, seed=seed)
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
    total float. For sequential schedules, every task is always critical.

    Returns:
        Dict mapping task name to frequency (0.0 to 1.0).
    """
    n_sims = project_durations.shape[0]
    n_tasks = len(sorted_tasks)
    freq: dict[str, float] = {}

    if not has_dependencies:
        for task in sorted_tasks:
            freq[task.name] = 1.0
        return freq

    # Backward pass to compute latest start/finish times
    latest_finish = np.zeros((n_tasks, n_sims))
    latest_start = np.zeros((n_tasks, n_sims))

    successors: dict[int, list[int]] = {i: [] for i in range(n_tasks)}
    for i, task in enumerate(sorted_tasks):
        for dep in task.depends_on:
            successors[task_index[dep]].append(i)

    for i in range(n_tasks):
        if not successors[i]:
            latest_finish[i] = project_durations
        else:
            latest_finish[i] = np.full(n_sims, np.inf)

    for i in range(n_tasks - 1, -1, -1):
        if successors[i]:
            succ_starts = np.array([latest_finish[s] - durations[s] for s in successors[i]])
            latest_finish[i] = np.min(succ_starts, axis=0)
        latest_start[i] = latest_finish[i] - durations[i]

    tolerance = 1e-6
    for i, task in enumerate(sorted_tasks):
        total_float = latest_start[i] - start_times[i]
        critical_count = np.sum(np.abs(total_float) < tolerance)
        freq[task.name] = float(critical_count) / n_sims

    return freq
