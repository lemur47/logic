"""
Bayesian Updating for PMO Estimation Calibration

Learns systematic estimation bias from (estimated, actual) duration pairs
using conjugate normal-normal Bayesian inference. No LLM reasoning — this
is deterministic maths that compounds knowledge from every observation.

Architecture constraint (Decision #166): this module MUST be pure Python.
LLMs cannot do sequential belief updating (Qiu et al. 2026, Nature Comms).
The two-tier design: deterministic Bayesian math here, LLM interprets the
structured output at the boundary.

Validated against the Stanford FOMC dual-track framework (Decision #265)
which uses the same conjugate normal-normal updating for policy rate beliefs.

Usage:
    python bayesian.py

Dependencies: None (stdlib only). matplotlib optional for visualisation.

License: MIT
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# ── Core Data Structures ────────────────────────────────────────────────


@dataclass(frozen=True)
class Prior:
    """A Gaussian prior belief about the delay factor.

    mean: expected delay factor (1.0 = no systematic bias)
    variance: uncertainty (larger = less confident)

    The uninformative default N(1.0, 0.25) says "we think estimates are
    roughly right, but we're not very sure." σ=0.5 covers the range
    [0.0, 2.0] at 95% confidence — wide enough for most PMO contexts.
    """

    mean: float = 1.0
    variance: float = 0.25

    def __post_init__(self):
        if self.variance <= 0:
            msg = f"Variance must be positive, got {self.variance}"
            raise ValueError(msg)

    @property
    def std_dev(self) -> float:
        return math.sqrt(self.variance)

    @property
    def precision(self) -> float:
        """τ = 1/σ² — the conjugate parameterisation."""
        return 1.0 / self.variance


@dataclass(frozen=True)
class Observation:
    """A single (estimated, actual) duration pair.

    The delay factor r = actual / estimated is the signal we observe.
    Context tags enable per-category priors (e.g. "auth", "infra").
    """

    estimated: float
    actual: float
    context: str = "default"

    def __post_init__(self):
        if self.estimated <= 0:
            msg = f"Estimated duration must be positive, got {self.estimated}"
            raise ValueError(msg)
        if self.actual < 0:
            msg = f"Actual duration must be non-negative, got {self.actual}"
            raise ValueError(msg)

    @property
    def delay_factor(self) -> float:
        """r = actual / estimated."""
        return self.actual / self.estimated


@dataclass(frozen=True)
class Posterior:
    """The result of Bayesian updating — our refined belief.

    Contains the posterior distribution parameters plus pre-computed
    credible intervals for direct use by consuming modules.
    """

    mean: float
    variance: float
    n_observations: int
    observations: tuple[float, ...]  # delay factors used

    @property
    def std_dev(self) -> float:
        return math.sqrt(self.variance)

    @property
    def precision(self) -> float:
        return 1.0 / self.variance

    @property
    def credible_interval_68(self) -> tuple[float, float]:
        """68% credible interval (±1σ)."""
        return (
            round(self.mean - self.std_dev, 4),
            round(self.mean + self.std_dev, 4),
        )

    @property
    def credible_interval_95(self) -> tuple[float, float]:
        """95% credible interval (±1.96σ)."""
        z = 1.96
        return (
            round(self.mean - z * self.std_dev, 4),
            round(self.mean + z * self.std_dev, 4),
        )

    @property
    def credible_interval_99(self) -> tuple[float, float]:
        """99.7% credible interval (±3σ)."""
        z = 3.0
        return (
            round(self.mean - z * self.std_dev, 4),
            round(self.mean + z * self.std_dev, 4),
        )


@dataclass
class EstimationLog:
    """Accumulates observations and tracks belief evolution.

    This is the stateful container that would map to D1's estimation_log
    table in the FastAPI integration. The standalone PoC keeps it in memory.
    """

    prior: Prior = field(default_factory=Prior)
    observation_noise: float = 0.15
    observations: list[Observation] = field(default_factory=list)
    history: list[Posterior] = field(default_factory=list)

    def __post_init__(self):
        if self.observation_noise <= 0:
            msg = f"Observation noise must be positive, got {self.observation_noise}"
            raise ValueError(msg)


# ── Core Functions ──────────────────────────────────────────────────────


def update_belief(
    prior: Prior,
    observations: list[Observation],
    observation_noise: float = 0.15,
) -> Posterior:
    """Sequential Bayesian update of delay factor belief.

    Uses conjugate normal-normal updating (FOMC paper, equations 1-4):

        τ_prior = 1 / σ²_prior
        τ_obs   = 1 / σ²_obs

    For each observation with delay factor r:
        τ_post  = τ_prior + τ_obs        (precisions ADD)
        μ_post  = (τ_prior × μ + τ_obs × r) / τ_post
        σ²_post = 1 / τ_post

    This is mathematically equivalent to processing all observations at
    once (batch) or one at a time (sequential). The sequential form makes
    the belief evolution visible — critical for the blog post and for
    demonstrating what LLMs cannot do.

    Args:
        prior: Gaussian prior belief about the delay factor.
        observations: List of (estimated, actual) duration pairs.
        observation_noise: σ_obs — assumed noise in each observation.
            Default 0.15 means observed delay factors scatter ±15% around
            the true systematic bias.

    Returns:
        Posterior distribution after processing all observations.
    """
    if observation_noise <= 0:
        msg = f"Observation noise must be positive, got {observation_noise}"
        raise ValueError(msg)

    if not observations:
        return Posterior(
            mean=prior.mean,
            variance=prior.variance,
            n_observations=0,
            observations=(),
        )

    noise_variance = observation_noise**2
    tau_obs = 1.0 / noise_variance

    # Sequential update — process one observation at a time
    mu = prior.mean
    tau = prior.precision

    delay_factors = []
    for obs in observations:
        r = obs.delay_factor
        delay_factors.append(r)

        # Conjugate normal-normal update
        tau_new = tau + tau_obs
        mu_new = (tau * mu + tau_obs * r) / tau_new

        tau = tau_new
        mu = mu_new

    return Posterior(
        mean=round(mu, 6),
        variance=round(1.0 / tau, 6),
        n_observations=len(observations),
        observations=tuple(round(d, 4) for d in delay_factors),
    )


def update_belief_with_history(
    log: EstimationLog,
    new_observations: list[Observation],
) -> list[Posterior]:
    """Update belief and record the evolution at each step.

    Returns the list of intermediate posteriors — one per observation.
    This is the function that powers the "belief narrowing" visualisation
    and demonstrates sequential updating for the blog post.
    """
    noise_variance = log.observation_noise**2
    tau_obs = 1.0 / noise_variance

    mu = log.prior.mean if not log.observations else log.history[-1].mean
    tau = log.prior.precision if not log.observations else log.history[-1].precision

    new_posteriors = []
    all_delay_factors = [o.delay_factor for o in log.observations]

    for obs in new_observations:
        r = obs.delay_factor
        all_delay_factors.append(r)

        tau_new = tau + tau_obs
        mu_new = (tau * mu + tau_obs * r) / tau_new

        tau = tau_new
        mu = mu_new

        posterior = Posterior(
            mean=round(mu, 6),
            variance=round(1.0 / tau, 6),
            n_observations=len(all_delay_factors),
            observations=tuple(round(d, 4) for d in all_delay_factors),
        )
        new_posteriors.append(posterior)
        log.history.append(posterior)
        log.observations.append(obs)

    return new_posteriors


def adjust_estimate(pert_expected: float, posterior: Posterior) -> dict:
    """Apply Bayesian calibration to a PERT estimate.

    The posterior mean IS the calibrated delay factor. Multiply the PERT
    expected duration by it to get the adjusted estimate. The posterior
    uncertainty propagates into the adjusted confidence intervals.

    Args:
        pert_expected: Expected duration from PERT (textbook formula).
        posterior: Current belief about the delay factor.

    Returns:
        Dict with adjusted estimate and confidence bands.
    """
    adjusted = round(pert_expected * posterior.mean, 2)
    ci_68 = posterior.credible_interval_68
    ci_95 = posterior.credible_interval_95

    return {
        "pert_expected": pert_expected,
        "delay_factor": round(posterior.mean, 4),
        "adjusted_expected": adjusted,
        "adjusted_range_68": [
            round(pert_expected * ci_68[0], 2),
            round(pert_expected * ci_68[1], 2),
        ],
        "adjusted_range_95": [
            round(pert_expected * ci_95[0], 2),
            round(pert_expected * ci_95[1], 2),
        ],
        "n_observations": posterior.n_observations,
        "confidence": _confidence_label(posterior),
    }


def _confidence_label(posterior: Posterior) -> str:
    """Human-readable confidence assessment."""
    if posterior.n_observations == 0:
        return "no data — using prior"
    if posterior.n_observations < 3:
        return "low — fewer than 3 observations"
    if posterior.std_dev > 0.15:
        return "moderate — high variance in observations"
    if posterior.std_dev > 0.05:
        return "good — converging"
    return "high — well-calibrated"


# ── Visualisation (optional, requires matplotlib) ───────────────────────


def visualise_belief_evolution(
    log: EstimationLog,
    save_path: str | None = None,
):
    """Plot the prior and all intermediate posteriors.

    Shows how the belief narrows with each observation — the visual proof
    that sequential Bayesian updating works and LLMs can't replicate it.
    """
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("matplotlib/numpy not installed — skipping visualisation.")
        return None

    fig, ax = plt.subplots(1, 1, figsize=(10, 5))

    x = np.linspace(0.2, 2.2, 500)

    # Prior
    prior_y = _normal_pdf(x, log.prior.mean, log.prior.variance)
    ax.plot(x, prior_y, color="#B4B2A9", linewidth=1.5, alpha=0.6, label="Prior")
    ax.fill_between(x, prior_y, alpha=0.08, color="#B4B2A9")

    # Intermediate posteriors (fading)
    n = len(log.history)
    for i, post in enumerate(log.history):
        alpha = 0.15 + 0.85 * (i / max(n - 1, 1))
        y = _normal_pdf(x, post.mean, post.variance)
        colour = "#534AB7"
        if i == n - 1:
            ax.plot(
                x, y, color=colour, linewidth=2, alpha=1.0, label=f"After {post.n_observations} obs"
            )
            ax.fill_between(x, y, alpha=0.15, color=colour)
        else:
            ax.plot(x, y, color=colour, linewidth=1, alpha=alpha * 0.5)

    # Observation markers
    for obs in log.observations:
        ax.axvline(obs.delay_factor, color="#D85A30", linewidth=1, alpha=0.4, ymin=0, ymax=0.05)

    ax.set_xlabel("Delay factor (r = actual / estimated)")
    ax.set_ylabel("Probability density")
    ax.set_title("Bayesian belief evolution: estimation calibration")
    ax.legend(loc="upper right")
    ax.set_xlim(0.2, 2.2)
    ax.set_ylim(bottom=0)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved to {save_path}")
    return fig


def _normal_pdf(x, mean: float, variance: float):
    """Vectorised normal PDF for numpy arrays."""
    import numpy as np

    std = np.sqrt(variance)
    return np.exp(-0.5 * ((x - mean) / std) ** 2) / (std * np.sqrt(2 * np.pi))


# ── Worked Examples (Self-Check) ────────────────────────────────────────


def _verify_worked_examples():
    """Hand-computed verification of the conjugate update formulas.

    Example A: Single observation
    ─────────────────────────────
    Prior: N(1.0, 0.25)    → τ_prior = 4.0
    Obs:   r = 1.3          → τ_obs = 1/(0.15²) = 44.444...
    ─────────────────────────────
    τ_post = 4.0 + 44.444 = 48.444
    μ_post = (4.0 × 1.0 + 44.444 × 1.3) / 48.444
           = (4.0 + 57.778) / 48.444
           = 61.778 / 48.444
           = 1.27521...
    σ²_post = 1 / 48.444 = 0.02064...

    Example B: Two observations (sequential)
    ─────────────────────────────────────────
    After obs 1 (r=1.3): μ=1.27521, τ=48.444
    Obs 2: r = 1.1
    ─────────────────────────────────────────
    τ_post = 48.444 + 44.444 = 92.889
    μ_post = (48.444 × 1.27521 + 44.444 × 1.1) / 92.889
           = (61.778 + 48.889) / 92.889
           = 110.667 / 92.889
           = 1.19133...
    σ²_post = 1 / 92.889 = 0.01077...
    """
    print("=" * 60)
    print("WORKED EXAMPLE VERIFICATION")
    print("=" * 60)

    prior = Prior(mean=1.0, variance=0.25)
    noise = 0.15

    # Example A: single observation
    obs_a = [Observation(estimated=10.0, actual=13.0)]  # r = 1.3
    post_a = update_belief(prior, obs_a, observation_noise=noise)

    print("\nExample A — single observation (r = 1.3)")
    print(f"  Prior:     N({prior.mean}, {prior.variance})")
    print(f"  Posterior: N({post_a.mean}, {post_a.variance})")
    print(f"  Expected μ ≈ 1.27521, got {post_a.mean}")
    print(f"  Expected σ² ≈ 0.02064, got {post_a.variance}")

    assert abs(post_a.mean - 1.27521) < 0.001, f"Mean check failed: {post_a.mean}"
    assert abs(post_a.variance - 0.02064) < 0.001, f"Variance check failed: {post_a.variance}"
    print("  ✓ PASS")

    # Example B: two observations (sequential = batch)
    obs_b = [
        Observation(estimated=10.0, actual=13.0),  # r = 1.3
        Observation(estimated=20.0, actual=22.0),  # r = 1.1
    ]
    post_b = update_belief(prior, obs_b, observation_noise=noise)

    print("\nExample B — two observations (r = 1.3, r = 1.1)")
    print(f"  Posterior: N({post_b.mean}, {post_b.variance})")
    print(f"  Expected μ ≈ 1.19133, got {post_b.mean}")
    print(f"  Expected σ² ≈ 0.01077, got {post_b.variance}")

    assert abs(post_b.mean - 1.19133) < 0.001, f"Mean check failed: {post_b.mean}"
    assert abs(post_b.variance - 0.01077) < 0.001, f"Variance check failed: {post_b.variance}"
    print("  ✓ PASS")

    # Verify sequential = batch
    post_seq = update_belief(prior, obs_b[:1], observation_noise=noise)
    post_seq2 = update_belief(
        Prior(mean=post_seq.mean, variance=post_seq.variance),
        obs_b[1:],
        observation_noise=noise,
    )

    assert abs(post_seq2.mean - post_b.mean) < 1e-6, "Sequential ≠ batch!"
    assert abs(post_seq2.variance - post_b.variance) < 1e-6, "Sequential ≠ batch!"
    print("\n  Sequential == Batch: ✓ PASS")


def _demo_full_scenario():
    """Realistic PMO scenario: SIer auth module estimation."""
    print("\n" + "=" * 60)
    print("DEMO — SIer Auth Module Estimation History")
    print("=" * 60)

    log = EstimationLog(
        prior=Prior(mean=1.0, variance=0.25),
        observation_noise=0.15,
    )

    # Historical data: auth tasks consistently take longer than estimated
    auth_history = [
        Observation(estimated=5, actual=7, context="auth"),  # r = 1.40
        Observation(estimated=10, actual=13, context="auth"),  # r = 1.30
        Observation(estimated=3, actual=4, context="auth"),  # r = 1.33
        Observation(estimated=8, actual=10, context="auth"),  # r = 1.25
        Observation(estimated=15, actual=19, context="auth"),  # r = 1.27
        Observation(estimated=6, actual=8, context="auth"),  # r = 1.33
    ]

    posteriors = update_belief_with_history(log, auth_history)

    print(f"\nPrior: N({log.prior.mean:.2f}, {log.prior.variance:.2f})")
    print(f"{'─' * 56}")

    for i, (obs, post) in enumerate(zip(auth_history, posteriors, strict=True)):
        print(
            f"  Obs {i + 1}: est={obs.estimated:5.1f}d, act={obs.actual:5.1f}d, "
            f"r={obs.delay_factor:.2f}  →  "
            f"μ={post.mean:.4f}, σ={post.std_dev:.4f}, "
            f"95% CI=[{post.credible_interval_95[0]:.2f}, {post.credible_interval_95[1]:.2f}]"
        )

    final = posteriors[-1]
    print(f"{'─' * 56}")
    print(f"Final belief: delay factor = {final.mean:.3f} (σ = {final.std_dev:.3f})")
    print(f"Interpretation: auth tasks take ~{final.mean:.0%} of the PERT estimate")
    print(f"95% CI: [{final.credible_interval_95[0]:.2f}, {final.credible_interval_95[1]:.2f}]")

    # Apply to a new estimate
    print(f"\n{'─' * 56}")
    print("Applying calibration to a new PERT estimate of 12 days:")
    result = adjust_estimate(12.0, final)
    print(f"  PERT expected:     {result['pert_expected']:.1f} days")
    print(f"  Delay factor:      {result['delay_factor']:.3f}")
    print(f"  Adjusted estimate: {result['adjusted_expected']:.1f} days")
    print(f"  68% range:         {result['adjusted_range_68']} days")
    print(f"  95% range:         {result['adjusted_range_95']} days")
    print(f"  Confidence:        {result['confidence']}")

    # Visualise if matplotlib available
    visualise_belief_evolution(log, save_path="belief_evolution.png")


def _demo_context_comparison():
    """Compare calibration across different task contexts."""
    print("\n" + "=" * 60)
    print("DEMO — Context Comparison: Auth vs Infrastructure")
    print("=" * 60)

    shared_prior = Prior(mean=1.0, variance=0.25)

    # Auth tasks: consistently late
    auth_obs = [
        Observation(estimated=5, actual=7, context="auth"),
        Observation(estimated=10, actual=13, context="auth"),
        Observation(estimated=8, actual=10, context="auth"),
    ]
    auth_post = update_belief(shared_prior, auth_obs, observation_noise=0.15)

    # Infra tasks: roughly on time
    infra_obs = [
        Observation(estimated=5, actual=5.2, context="infra"),
        Observation(estimated=10, actual=9.8, context="infra"),
        Observation(estimated=8, actual=8.5, context="infra"),
    ]
    infra_post = update_belief(shared_prior, infra_obs, observation_noise=0.15)

    print(
        f"\nAuth tasks  ({len(auth_obs)} obs): delay factor = {auth_post.mean:.3f} ± {auth_post.std_dev:.3f}"
    )
    print(
        f"Infra tasks ({len(infra_obs)} obs): delay factor = {infra_post.mean:.3f} ± {infra_post.std_dev:.3f}"
    )

    # Same PERT estimate, different calibrations
    pert_est = 10.0
    auth_adj = adjust_estimate(pert_est, auth_post)
    infra_adj = adjust_estimate(pert_est, infra_post)

    print(f"\nFor a PERT estimate of {pert_est:.0f} days:")
    print(
        f"  Auth adjusted:  {auth_adj['adjusted_expected']:.1f} days  (95%: {auth_adj['adjusted_range_95']})"
    )
    print(
        f"  Infra adjusted: {infra_adj['adjusted_expected']:.1f} days  (95%: {infra_adj['adjusted_range_95']})"
    )
    print(
        f"\n  → Auth needs {auth_adj['adjusted_expected'] - infra_adj['adjusted_expected']:.1f} more days than infra"
    )


if __name__ == "__main__":
    _verify_worked_examples()
    _demo_full_scenario()
    _demo_context_comparison()
