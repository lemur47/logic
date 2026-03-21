"""
Bayesian Updating for PMO Estimation Calibration — Core Logic.

Learns systematic estimation bias from (estimated, actual) duration pairs
using conjugate normal-normal Bayesian inference.

Architecture constraint (Decision #166): this module MUST be pure Python.
LLMs cannot do sequential belief updating (Qiu et al. 2026, Nature Comms).

Validated against the Stanford FOMC dual-track framework (Decision #265).

License: MIT
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# ── Core Data Structures ────────────────────────────────────────────────


@dataclass(frozen=True)
class Prior:
    """A Gaussian prior belief about the delay factor.

    mean: expected delay factor (1.0 = no systematic bias)
    variance: uncertainty (larger = less confident)

    The uninformative default N(1.0, 0.25) says "we think estimates are
    roughly right, but we're not very sure." σ=0.5 covers the range
    [0.0, 2.0] at 95% confidence.
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
