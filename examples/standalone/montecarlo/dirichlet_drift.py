"""
Dirichlet-Drift Monte Carlo Simulation

Extends plain Monte Carlo with calibrated drift derived from per-class
Bayesian posteriors and Dirichlet-distributed class-mix weights.

Per simulation iteration:

1. Sample beta-PERT duration D_j for each task as in plain MC.
2. Sample posterior delay factors mu_k ~ N(mu_k_posterior, sigma_k_posterior)
   for each risk class k.
3. Sample Dirichlet weights w ~ Dirichlet(alpha_1, ..., alpha_K) for the
   class-mix.
4. Compute per-task drift:
       d_j = mu_{class(j)}            (tasks with explicit risk_class)
       d_j = sum_k w_k * mu_k         (unclassified tasks — blended)
5. Apply drift multiplicatively: D'_j = d_j * D_j.
6. Run the standard forward pass on D'_j to compute project duration.

Degenerate reducibility — posteriors with mu=1.0, sigma=0 produce d_j = 1
identically, so the duration distribution converges to plain Monte Carlo
within statistical tolerance.

Caller-supplied posteriors. This module does NOT import the Bayesian
module — its sole interface is `dict[str, Posterior]` (or, equivalently,
posteriors carried on `RiskClass` objects). Risk classes without an
explicit posterior fall back to an uninformative N(1.0, 0.5) prior.

Drift horizon: across-MC-runs (within-project). Each run is a snapshot
at a point in time; re-run with updated posteriors as real tasks
complete. The simulation loop itself is stateless w.r.t. drift.

Cross-project carry-forward is free — start the next project with
prior_new = posterior_old. Demonstrated by test.

Usage:
    python dirichlet_drift.py

Dependencies: numpy, scipy. matplotlib optional.

Licence: MIT
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from montecarlo import (
    ScheduleNetwork,
    Task,
    _compute_critical_path_frequency,
    _topological_sort,
    sample_pert_duration,
    simulate_schedule,
)

# Uninformative fallback for risk classes with no posterior supplied.
# sigma=0.5 covers the range [0, 2] at ~95% confidence — wide enough
# to express "we have no idea" without permitting absurd negative
# delay factors at any meaningful frequency.
DEFAULT_UNINFORMATIVE_POSTERIOR_SIGMA = 0.5


# ── Core Data Structures ────────────────────────────────────────────────


@dataclass(frozen=True)
class Posterior:
    """Gaussian posterior on a risk class's delay factor.

    A delay factor of 1.0 means estimates are unbiased on average;
    1.3 means actual durations run ~30% over estimate; 0.8 means
    consistent under-estimation that finishes early.

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
    """A risk class with a Dirichlet concentration parameter and an
    optional Gaussian posterior on its delay factor.

    Args:
        name: Stable identifier referenced from `DriftTask.risk_class`.
        prior_alpha: Dirichlet concentration parameter for this class.
            Larger values pull the class-mix weight toward this class
            more strongly. Default 1.0 yields a uniform prior across
            all classes.
        posterior: Caller-supplied posterior on the delay factor. If
            None, an uninformative N(1.0, 0.5) is used as fallback.
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

    Inherits beta-PERT three-point estimates and dependencies from
    `Task`. Adds `risk_class`: when set, the task's drift comes from
    that class's posterior; when None, the drift is a Dirichlet-weighted
    blend across all configured classes.
    """

    risk_class: str | None = None


@dataclass(frozen=True)
class DriftConfig:
    """Configuration for a Dirichlet-drift simulation.

    Args:
        risk_classes: The set of risk classes available to tasks. The
            order is significant — it defines the index ordering of the
            Dirichlet weights and the per-class posterior draws.
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

    Attributes:
        durations: Project duration sample for every iteration.
        n_simulations: Number of iterations.
        percentiles: P50, P75, P85, P95.
        histogram: Bin edges and counts.
        critical_path_frequency: Per-task probability of being on the
            critical path.
        tasks: The DriftTasks that were simulated.
        class_contribution: Per-class diagnostic — mean Dirichlet
            weight, mean sampled posterior mu, and the count of tasks
            bound to that class.
        dirichlet_weights_used: Raw Dirichlet weight samples, shape
            (n_simulations, n_classes). Useful for downstream auditing.
    """

    durations: np.ndarray
    n_simulations: int
    percentiles: dict[str, float]
    histogram: dict[str, list[float]]
    critical_path_frequency: dict[str, float]
    tasks: list[DriftTask] = field(default_factory=list)
    class_contribution: dict[str, dict[str, float]] = field(default_factory=dict)
    dirichlet_weights_used: np.ndarray = field(default_factory=lambda: np.empty((0, 0)))

    class Config:
        arbitrary_types_allowed = True


# ── Core Function ───────────────────────────────────────────────────────


def simulate_with_drift(
    tasks: list[DriftTask],
    config: DriftConfig,
    n_simulations: int = 10_000,
) -> DriftResult:
    """Run Dirichlet-drift Monte Carlo simulation on a schedule.

    Each iteration applies a per-task drift multiplier on top of the
    beta-PERT-sampled duration. The drift comes from the configured
    risk classes — directly for tasks bound to a class, or via a
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
            DriftConfig validation fails, or if the schedule network
            is malformed.
    """
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

    # Per-iteration posterior draws: mu_k ~ N(mu_k_posterior, sigma_k_posterior).
    # When all sigmas are zero, broadcast the means rather than calling
    # rng.normal — keeps the rng stream tight in the degenerate case.
    if np.all(posterior_sigmas == 0):
        mu_draws = np.broadcast_to(posterior_mus, (n_simulations, n_classes)).copy()
    else:
        mu_draws = rng.normal(
            loc=posterior_mus,
            scale=posterior_sigmas,
            size=(n_simulations, n_classes),
        )

    # Per-iteration Dirichlet weights: w ~ Dir(alpha_1, ..., alpha_K).
    alphas = np.array([c.prior_alpha for c in classes])
    weights = rng.dirichlet(alphas, size=n_simulations)

    # Per-task drift multiplier d_j(t).
    n_tasks = len(tasks)
    drift = np.empty((n_tasks, n_simulations))
    for i, task in enumerate(tasks):
        if task.risk_class is None:
            # Blended: d_j = sum_k w_k * mu_k (per simulation).
            drift[i] = np.einsum("sk,sk->s", weights, mu_draws)
        else:
            k = class_index[task.risk_class]
            drift[i] = mu_draws[:, k]

    # Clip drift to non-negative — protects against the rare case where
    # a wide-sigma posterior draw goes below zero (would produce a
    # nonsensical negative duration).
    drift = np.maximum(drift, 0.0)

    # Topological sort if dependencies are present.
    has_dependencies = any(t.depends_on for t in tasks)
    if has_dependencies:
        ScheduleNetwork(tasks=list(tasks))  # validates topology
        sorted_tasks: list[DriftTask] = _topological_sort(list(tasks))  # type: ignore[arg-type]
    else:
        sorted_tasks = list(tasks)

    # Re-index drift to match the sorted task order.
    name_to_orig_index = {t.name: i for i, t in enumerate(tasks)}
    sort_idx = [name_to_orig_index[t.name] for t in sorted_tasks]
    drift = drift[sort_idx]

    # Beta-PERT duration samples in sorted order.
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

    # Forward pass — same logic as plain simulate_schedule.
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

    # Degenerate distributions (constant or near-constant durations,
    # e.g. tasks with O==M==P) have zero range, which np.histogram with
    # a fixed bin count rejects. Collapse to a single spike bin.
    if np.ptp(project_durations) < 1e-10:
        val = float(np.mean(project_durations))
        histogram = {
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


# ── Worked Examples (Self-Check) ────────────────────────────────────────


def _verify_degenerate_reducibility():
    """With neutral posteriors (mu=1, sigma=0), drift collapses to 1.0
    and the result distribution should match plain Monte Carlo within
    statistical tolerance."""
    print("=" * 60)
    print("VERIFICATION: Degenerate Reducibility")
    print("=" * 60)

    plain_tasks = [
        Task("Design", 3, 5, 10),
        Task("Build", 5, 8, 15),
        Task("Test", 2, 4, 8),
    ]
    drift_tasks = [
        DriftTask("Design", 3, 5, 10),
        DriftTask("Build", 5, 8, 15),
        DriftTask("Test", 2, 4, 8),
    ]
    config = DriftConfig(
        risk_classes=(
            RiskClass("c1", prior_alpha=1.0, posterior=Posterior(mu=1.0, sigma=0.0)),
            RiskClass("c2", prior_alpha=1.0, posterior=Posterior(mu=1.0, sigma=0.0)),
        ),
        seed=42,
    )

    plain = simulate_schedule(plain_tasks, n_simulations=50_000, seed=42)
    drift = simulate_with_drift(drift_tasks, config, n_simulations=50_000)

    plain_mean = float(np.mean(plain.durations))
    drift_mean = float(np.mean(drift.durations))

    print(f"\n  Plain MC mean : {plain_mean:.3f}")
    print(f"  Drift mean    : {drift_mean:.3f}")
    print(f"  Relative error: {abs(plain_mean - drift_mean) / plain_mean:.4%}")
    print(f"  Plain P85: {plain.percentiles['P85']:.2f}, Drift P85: {drift.percentiles['P85']:.2f}")

    assert abs(plain_mean - drift_mean) / plain_mean < 0.01
    print("  PASS")


def _verify_mean_shift():
    """Posterior mu=1.3 shifts the duration distribution by ~30%."""
    print("\n" + "=" * 60)
    print("VERIFICATION: Mean Shift (mu=1.3 → ~30% longer)")
    print("=" * 60)

    base_tasks = [
        DriftTask("A", 3, 5, 10, risk_class="overrun"),
        DriftTask("B", 5, 8, 15, risk_class="overrun"),
    ]

    neutral = DriftConfig(
        risk_classes=(RiskClass("overrun", posterior=Posterior(mu=1.0, sigma=0.0)),),
        seed=42,
    )
    shifted = DriftConfig(
        risk_classes=(RiskClass("overrun", posterior=Posterior(mu=1.3, sigma=0.0)),),
        seed=42,
    )

    n = simulate_with_drift(base_tasks, neutral, n_simulations=50_000)
    s = simulate_with_drift(base_tasks, shifted, n_simulations=50_000)

    n_mean = float(np.mean(n.durations))
    s_mean = float(np.mean(s.durations))
    ratio = s_mean / n_mean

    print(f"\n  Neutral mean : {n_mean:.3f}")
    print(f"  Shifted mean : {s_mean:.3f}")
    print(f"  Ratio        : {ratio:.4f} (expected 1.30)")

    assert 1.28 < ratio < 1.32
    print("  PASS")


def _verify_variance_propagation():
    """Posterior sigma > 0 widens the duration distribution."""
    print("\n" + "=" * 60)
    print("VERIFICATION: Variance Propagation")
    print("=" * 60)

    tasks = [
        DriftTask("A", 3, 5, 10, risk_class="x"),
        DriftTask("B", 5, 8, 15, risk_class="x"),
    ]

    sharp = DriftConfig(
        risk_classes=(RiskClass("x", posterior=Posterior(mu=1.0, sigma=0.0)),), seed=42
    )
    diffuse = DriftConfig(
        risk_classes=(RiskClass("x", posterior=Posterior(mu=1.0, sigma=0.4)),), seed=42
    )

    sharp_r = simulate_with_drift(tasks, sharp, n_simulations=50_000)
    diff_r = simulate_with_drift(tasks, diffuse, n_simulations=50_000)

    sharp_std = float(np.std(sharp_r.durations))
    diff_std = float(np.std(diff_r.durations))

    print(f"\n  Sharp posterior std  : {sharp_std:.3f}")
    print(f"  Diffuse posterior std: {diff_std:.3f}")
    print(f"  Spread ratio         : {diff_std / sharp_std:.3f}")

    assert diff_std > sharp_std * 1.5
    print("  PASS")


def _verify_dirichlet_blending():
    """Unclassified tasks get a Dirichlet-weighted blend across classes."""
    print("\n" + "=" * 60)
    print("VERIFICATION: Dirichlet Blending for Unclassified Tasks")
    print("=" * 60)

    tasks = [DriftTask("Mystery", 4, 6, 10)]  # risk_class=None
    config = DriftConfig(
        risk_classes=(
            RiskClass("low", prior_alpha=1.0, posterior=Posterior(mu=1.0, sigma=0.0)),
            RiskClass("high", prior_alpha=1.0, posterior=Posterior(mu=2.0, sigma=0.0)),
        ),
        seed=42,
    )

    result = simulate_with_drift(tasks, config, n_simulations=50_000)
    pert_expected = (4 + 4 * 6 + 10) / 6
    expected_drift = 1.5  # uniform Dirichlet → 0.5*1.0 + 0.5*2.0
    expected_mean = pert_expected * expected_drift
    actual_mean = float(np.mean(result.durations))

    print(f"\n  PERT expected base : {pert_expected:.3f}")
    print(f"  Expected drift     : {expected_drift:.3f} (uniform Dirichlet over 1.0 / 2.0)")
    print(f"  Expected MC mean   : {expected_mean:.3f}")
    print(f"  Actual MC mean     : {actual_mean:.3f}")
    print(f"  Class contribution : {result.class_contribution}")

    assert abs(actual_mean - expected_mean) / expected_mean < 0.02
    print("  PASS")


def _verify_re_estimation_monotonicity():
    """Smaller posterior sigma should not increase the result spread."""
    print("\n" + "=" * 60)
    print("VERIFICATION: Re-estimation Monotonicity")
    print("=" * 60)

    tasks = [
        DriftTask("A", 3, 5, 10, risk_class="x"),
        DriftTask("B", 5, 8, 15, risk_class="x"),
    ]
    sigmas = [0.4, 0.2, 0.1, 0.0]
    stds = []
    for sigma in sigmas:
        config = DriftConfig(
            risk_classes=(RiskClass("x", posterior=Posterior(mu=1.0, sigma=sigma)),),
            seed=42,
        )
        r = simulate_with_drift(tasks, config, n_simulations=50_000)
        stds.append(float(np.std(r.durations)))

    print(f"\n  sigma → std dev: {list(zip(sigmas, [round(s, 3) for s in stds], strict=True))}")

    for a, b in zip(stds, stds[1:], strict=False):
        assert a >= b * 0.99  # weak monotonicity, allow 1% noise per step
    print("  PASS (monotonic non-increasing as sigma → 0)")


def _verify_cross_project_carry_forward():
    """prior_new = posterior_old should give identical results when
    seeds match — proves there's no hidden state between runs."""
    print("\n" + "=" * 60)
    print("VERIFICATION: Cross-Project Carry-Forward")
    print("=" * 60)

    tasks = [
        DriftTask("A", 3, 5, 10, risk_class="auth"),
        DriftTask("B", 5, 8, 15, risk_class="auth"),
    ]
    project_one = DriftConfig(
        risk_classes=(RiskClass("auth", posterior=Posterior(mu=1.2, sigma=0.15)),), seed=99
    )
    project_two = DriftConfig(
        risk_classes=(RiskClass("auth", posterior=Posterior(mu=1.2, sigma=0.15)),), seed=99
    )

    r1 = simulate_with_drift(tasks, project_one, n_simulations=20_000)
    r2 = simulate_with_drift(tasks, project_two, n_simulations=20_000)

    print(f"\n  Project 1 mean: {float(np.mean(r1.durations)):.4f}")
    print(f"  Project 2 mean: {float(np.mean(r2.durations)):.4f}")
    print(f"  Project 1 P85 : {r1.percentiles['P85']:.2f}")
    print(f"  Project 2 P85 : {r2.percentiles['P85']:.2f}")

    np.testing.assert_array_equal(r1.durations, r2.durations)
    print("  PASS (identical inputs → identical outputs, no hidden state)")


def _demo_worked_example():
    """A six-task project with two risk classes and one unclassified task.

    'auth' tasks have a tight, slightly-pessimistic posterior (we've
    learned auth runs ~15% over). 'infra' has a wide, near-neutral
    posterior (we don't have much data yet). 'Discovery' is unclassified
    — its drift is blended.
    """
    print("\n" + "=" * 60)
    print("DEMO: Worked Example (6 tasks, 2 classes, 1 unclassified)")
    print("=" * 60)

    tasks = [
        DriftTask("Discovery", 3, 5, 10),  # unclassified
        DriftTask("Auth API", 4, 7, 14, risk_class="auth", depends_on=("Discovery",)),
        DriftTask("Auth UI", 3, 5, 10, risk_class="auth", depends_on=("Discovery",)),
        DriftTask("Infra setup", 5, 8, 18, risk_class="infra", depends_on=("Discovery",)),
        DriftTask(
            "Integration",
            3,
            5,
            10,
            risk_class="infra",
            depends_on=("Auth API", "Auth UI", "Infra setup"),
        ),
        DriftTask("Hardening", 2, 4, 8, depends_on=("Integration",)),
    ]
    config = DriftConfig(
        risk_classes=(
            RiskClass("auth", prior_alpha=1.0, posterior=Posterior(mu=1.15, sigma=0.10)),
            RiskClass("infra", prior_alpha=1.0, posterior=Posterior(mu=1.05, sigma=0.30)),
        ),
        seed=42,
    )

    plain_result = simulate_schedule(
        [Task(t.name, t.optimistic, t.most_likely, t.pessimistic, t.depends_on) for t in tasks],
        n_simulations=20_000,
        seed=42,
    )
    drift_result = simulate_with_drift(tasks, config, n_simulations=20_000)

    print(f"\n  {'':16s} {'Plain MC':>10s}  {'Drift MC':>10s}")
    print(f"  {'─' * 40}")
    print(
        f"  {'Mean':16s} {float(np.mean(plain_result.durations)):10.2f}  "
        f"{float(np.mean(drift_result.durations)):10.2f}"
    )
    print(
        f"  {'Std dev':16s} {float(np.std(plain_result.durations)):10.2f}  "
        f"{float(np.std(drift_result.durations)):10.2f}"
    )
    for p in ["P50", "P75", "P85", "P95"]:
        print(f"  {p:16s} {plain_result.percentiles[p]:10.2f}  {drift_result.percentiles[p]:10.2f}")

    print("\n  Class contribution diagnostics:")
    for name, info in drift_result.class_contribution.items():
        print(
            f"    {name:8s} weight={info['mean_weight']:.3f}  "
            f"mu={info['mean_mu']:.3f}  tasks_bound={info['n_tasks_bound']:.0f}"
        )


if __name__ == "__main__":
    _verify_degenerate_reducibility()
    _verify_mean_shift()
    _verify_variance_propagation()
    _verify_dirichlet_blending()
    _verify_re_estimation_monotonicity()
    _verify_cross_project_carry_forward()
    _demo_worked_example()
