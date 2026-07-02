"""
Monte Carlo Schedule Simulation — Core Logic.

Generates a probability distribution over total project duration by running
thousands of simulated schedules. Each task's duration is sampled from a
beta-PERT distribution parameterised by three-point estimates (optimistic,
most likely, pessimistic).

Drift extension (`simulate_with_drift`): applies a per-task drift multiplier
sampled from per-class Bayesian posteriors and Dirichlet-distributed class-mix
weights. Caller-supplied posteriors — does NOT import app.bayesian.

License: MIT
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy import stats

# Monte Carlo allocates several (n_tasks, n_simulations) float64 arrays (up to ~7
# on the drift path). Cap their product so a single call cannot over-allocate,
# regardless of how the caller splits it between task count and simulation count.
# 10_000_000 cells → ~80 MB per array, and still admits a 1000-task network at
# the default 10_000 simulations. Kept here (the layer that allocates) so the
# pure core enforces its own safety ceiling; the API schema imports it too.
MAX_SIMULATION_CELLS = 10_000_000


def _check_allocation(n_tasks: int, n_simulations: int) -> None:
    """Guard against over-allocation before any array is created.

    Defence in depth: the API schema rejects oversized requests at the boundary,
    but this also covers the crud-update, MCP and direct-call paths.
    """
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


# ── Drift Extension ─────────────────────────────────────────────────────

DEFAULT_UNINFORMATIVE_POSTERIOR_SIGMA = 0.5


@dataclass(frozen=True)
class Posterior:
    """Gaussian posterior on a risk class's delay factor.

    A delay factor of 1.0 means estimates are unbiased on average; 1.3 means
    actual durations run ~30% over estimate; 0.8 means consistent
    under-estimation that finishes early.

    Args:
        mu: Posterior mean delay factor. Must be >= 0.
        sigma: Posterior standard deviation. Must be >= 0. sigma=0 is a
            degenerate point mass at mu — useful for testing reducibility.
    """

    mu: float
    sigma: float

    def __post_init__(self):
        if self.mu < 0:
            msg = f"Posterior mu must be >= 0, got {self.mu}"
            raise ValueError(msg)
        if self.sigma < 0:
            msg = f"Posterior sigma must be >= 0, got {self.sigma}"
            raise ValueError(msg)


@dataclass(frozen=True)
class RiskClass:
    """A risk class with a Dirichlet concentration parameter and an optional
    Gaussian posterior on its delay factor.

    Args:
        name: Stable identifier referenced from `DriftTask.risk_class`.
        prior_alpha: Dirichlet concentration parameter for this class.
            Larger values pull the class-mix weight toward this class more
            strongly. Default 1.0 yields a uniform prior across all classes.
        posterior: Caller-supplied posterior on the delay factor. If None,
            an uninformative N(1.0, 0.5) is used as fallback.
    """

    name: str
    prior_alpha: float = 1.0
    posterior: Posterior | None = None

    def __post_init__(self):
        if not self.name:
            msg = "RiskClass name must be a non-empty string"
            raise ValueError(msg)
        if self.prior_alpha <= 0:
            msg = (
                f"RiskClass prior_alpha must be > 0 (Dirichlet requirement), got {self.prior_alpha}"
            )
            raise ValueError(msg)

    @property
    def effective_posterior(self) -> Posterior:
        """Posterior to use for sampling — caller's, or the uninformative
        fallback when none was supplied."""
        if self.posterior is not None:
            return self.posterior
        return Posterior(mu=1.0, sigma=DEFAULT_UNINFORMATIVE_POSTERIOR_SIGMA)


@dataclass(frozen=True)
class DriftTask(Task):
    """A Task that may be bound to a named risk class.

    Inherits beta-PERT three-point estimates and dependencies from `Task`.
    Adds `risk_class`: when set, the task's drift comes from that class's
    posterior; when None, the drift is a Dirichlet-weighted blend across
    all configured classes.
    """

    risk_class: str | None = None


@dataclass(frozen=True)
class DriftConfig:
    """Configuration for a Dirichlet-drift simulation.

    Args:
        risk_classes: The set of risk classes available to tasks. The order
            is significant — it defines the index ordering of the Dirichlet
            weights and the per-class posterior draws.
        seed: Random seed for reproducibility. None for non-deterministic.
    """

    risk_classes: tuple[RiskClass, ...]
    seed: int | None = None

    def __post_init__(self):
        if not self.risk_classes:
            msg = "DriftConfig requires at least one risk_class"
            raise ValueError(msg)
        names = [rc.name for rc in self.risk_classes]
        if len(set(names)) != len(names):
            msg = f"Duplicate risk class names: {names}"
            raise ValueError(msg)


@dataclass(frozen=True)
class DriftResult:
    """Output of a Dirichlet-drift Monte Carlo simulation.

    Mirrors `SimulationResult` and adds class-mix diagnostics.
    """

    durations: np.ndarray
    n_simulations: int
    percentiles: dict[str, float]
    histogram: dict[str, list[float]]
    critical_path_frequency: dict[str, float]
    tasks: list[DriftTask]
    class_contribution: dict[str, dict[str, float]]
    dirichlet_weights_used: np.ndarray

    class Config:
        arbitrary_types_allowed = True


def simulate_with_drift(
    tasks: list[DriftTask],
    config: DriftConfig,
    n_simulations: int = 10_000,
) -> DriftResult:
    """Run Dirichlet-drift Monte Carlo simulation on a schedule.

    Each iteration applies a per-task drift multiplier on top of the
    beta-PERT-sampled duration. The drift comes from the configured risk
    classes — directly for tasks bound to a class, or via a
    Dirichlet-weighted blend for unclassified tasks.

    Args:
        tasks: List of DriftTask objects defining the schedule.
        config: DriftConfig with the risk class definitions and seed.
        n_simulations: Number of simulation iterations (default 10,000).

    Returns:
        DriftResult containing the duration distribution, percentiles,
        critical-path frequency, and class-mix diagnostics.

    Raises:
        ValueError: if any task references an unknown risk class, if
            DriftConfig validation fails, or if the schedule network is
            malformed.
    """
    if not tasks:
        msg = "At least one task is required"
        raise ValueError(msg)

    _check_allocation(len(tasks), n_simulations)

    rng = np.random.default_rng(config.seed)
    classes = list(config.risk_classes)
    n_classes = len(classes)
    class_names = [c.name for c in classes]
    class_index = {name: i for i, name in enumerate(class_names)}

    for t in tasks:
        if t.risk_class is not None and t.risk_class not in class_index:
            msg = f"Task '{t.name}' references unknown risk_class '{t.risk_class}'"
            raise ValueError(msg)

    posterior_mus = np.array([c.effective_posterior.mu for c in classes])
    posterior_sigmas = np.array([c.effective_posterior.sigma for c in classes])

    if np.all(posterior_sigmas == 0):
        mu_draws = np.broadcast_to(posterior_mus, (n_simulations, n_classes)).copy()
    else:
        mu_draws = rng.normal(
            loc=posterior_mus,
            scale=posterior_sigmas,
            size=(n_simulations, n_classes),
        )

    alphas = np.array([c.prior_alpha for c in classes])
    weights = rng.dirichlet(alphas, size=n_simulations)

    n_tasks = len(tasks)
    drift = np.empty((n_tasks, n_simulations))
    for i, task in enumerate(tasks):
        if task.risk_class is None:
            drift[i] = np.einsum("sk,sk->s", weights, mu_draws)
        else:
            k = class_index[task.risk_class]
            drift[i] = mu_draws[:, k]

    drift = np.maximum(drift, 0.0)

    has_dependencies = any(t.depends_on for t in tasks)
    if has_dependencies:
        ScheduleNetwork(tasks=list(tasks))
        sorted_tasks: list[DriftTask] = _topological_sort(list(tasks))  # type: ignore[arg-type]
    else:
        sorted_tasks = list(tasks)

    name_to_orig_index = {t.name: i for i, t in enumerate(tasks)}
    sort_idx = [name_to_orig_index[t.name] for t in sorted_tasks]
    drift = drift[sort_idx]

    base_samples = np.zeros((n_tasks, n_simulations))
    for i, task in enumerate(sorted_tasks):
        base_samples[i] = sample_pert_duration(
            task.optimistic,
            task.most_likely,
            task.pessimistic,
            size=n_simulations,
            rng=rng,
        )

    drifted = base_samples * drift

    task_index = {t.name: i for i, t in enumerate(sorted_tasks)}
    finish_times = np.zeros((n_tasks, n_simulations))
    start_times = np.zeros((n_tasks, n_simulations))

    if has_dependencies:
        for i, task in enumerate(sorted_tasks):
            if task.depends_on:
                pred_finishes = np.array([finish_times[task_index[dep]] for dep in task.depends_on])
                start_times[i] = np.max(pred_finishes, axis=0)
            finish_times[i] = start_times[i] + drifted[i]
    else:
        for i in range(n_tasks):
            if i == 0:
                finish_times[i] = drifted[i]
            else:
                finish_times[i] = finish_times[i - 1] + drifted[i]
            start_times[i] = finish_times[i] - drifted[i]

    project_durations = np.max(finish_times, axis=0)

    critical_path_freq = _compute_critical_path_frequency(
        sorted_tasks,  # type: ignore[arg-type]
        task_index,
        finish_times,
        start_times,
        drifted,
        project_durations,
        has_dependencies,
    )

    percentiles = {
        "P50": float(np.percentile(project_durations, 50)),
        "P75": float(np.percentile(project_durations, 75)),
        "P85": float(np.percentile(project_durations, 85)),
        "P95": float(np.percentile(project_durations, 95)),
    }

    # Degenerate distributions (constant or near-constant durations) have zero
    # range, which np.histogram with a fixed bin count rejects. Collapse to a
    # single spike bin in that case.
    if np.ptp(project_durations) < 1e-10:
        val = float(np.mean(project_durations))
        histogram: dict[str, list[float]] = {
            "bin_edges": [round(val, 2), round(val, 2)],
            "counts": [int(n_simulations)],
        }
    else:
        counts, bin_edges = np.histogram(project_durations, bins=50)
        histogram = {
            "bin_edges": [round(float(e), 2) for e in bin_edges],
            "counts": [int(c) for c in counts],
        }

    class_contribution: dict[str, dict[str, float]] = {}
    for k, name in enumerate(class_names):
        n_bound = sum(1 for t in tasks if t.risk_class == name)
        class_contribution[name] = {
            "mean_weight": round(float(np.mean(weights[:, k])), 4),
            "mean_mu": round(float(np.mean(mu_draws[:, k])), 4),
            "n_tasks_bound": n_bound,
        }

    return DriftResult(
        durations=project_durations,
        n_simulations=n_simulations,
        percentiles={k: round(v, 2) for k, v in percentiles.items()},
        histogram=histogram,
        critical_path_frequency={k: round(v, 4) for k, v in critical_path_freq.items()},
        tasks=list(tasks),
        class_contribution=class_contribution,
        dirichlet_weights_used=weights,
    )


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
