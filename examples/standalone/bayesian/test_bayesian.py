"""Tests for the Bayesian estimation calibration standalone module.

Covers the full update cycle: context creation (Prior, Observation,
EstimationLog), observation ingestion, posterior computation via
conjugate normal-normal updating, and calibration of PERT estimates.

The hand-computed expected values in the update_belief tests mirror the
worked examples in bayesian.py::_verify_worked_examples, giving us a
second independent check of the same mathematics.
"""

import math

import pytest
from bayesian import (
    EstimationLog,
    Observation,
    Posterior,
    Prior,
    _confidence_label,
    adjust_estimate,
    update_belief,
    update_belief_with_history,
    visualise_belief_evolution,
)

# ── Prior ────────────────────────────────────────────────────────────────


def test_prior_defaults():
    """Uninformative prior defaults to N(1.0, 0.25)."""
    prior = Prior()
    assert prior.mean == 1.0
    assert prior.variance == 0.25
    # σ = √0.25 = 0.5
    assert prior.std_dev == 0.5
    # τ = 1/σ² = 4.0
    assert prior.precision == 4.0


def test_prior_rejects_non_positive_variance():
    """Variance must be > 0 — zero breaks the conjugate formula."""
    with pytest.raises(ValueError, match="Variance must be positive"):
        Prior(mean=1.0, variance=0.0)
    with pytest.raises(ValueError, match="Variance must be positive"):
        Prior(mean=1.0, variance=-0.1)


# ── Observation ──────────────────────────────────────────────────────────


def test_observation_delay_factor():
    """r = actual / estimated."""
    obs = Observation(estimated=10.0, actual=13.0)
    assert obs.delay_factor == 1.3
    # Under-estimate
    assert Observation(estimated=10.0, actual=7.5).delay_factor == 0.75


def test_observation_default_context():
    """Context defaults to 'default' for untagged observations."""
    obs = Observation(estimated=5.0, actual=5.0)
    assert obs.context == "default"


def test_observation_rejects_non_positive_estimated():
    """Estimated duration must be > 0 — division by zero otherwise."""
    with pytest.raises(ValueError, match="Estimated duration must be positive"):
        Observation(estimated=0.0, actual=5.0)
    with pytest.raises(ValueError, match="Estimated duration must be positive"):
        Observation(estimated=-1.0, actual=5.0)


def test_observation_rejects_negative_actual():
    """Actual duration can be zero (task finished instantly) but not negative."""
    # Zero is allowed
    obs = Observation(estimated=5.0, actual=0.0)
    assert obs.delay_factor == 0.0
    # Negative is not
    with pytest.raises(ValueError, match="Actual duration must be non-negative"):
        Observation(estimated=5.0, actual=-1.0)


# ── Posterior ────────────────────────────────────────────────────────────


def test_posterior_credible_intervals():
    """68% ≈ ±σ, 95% ≈ ±1.96σ, 99.7% ≈ ±3σ."""
    # σ² = 0.01 → σ = 0.1
    post = Posterior(mean=1.2, variance=0.01, n_observations=10, observations=())

    ci_68 = post.credible_interval_68
    assert ci_68 == (1.1, 1.3)

    ci_95 = post.credible_interval_95
    # 1.2 ± 1.96 × 0.1 = [1.004, 1.396]
    assert ci_95 == (1.004, 1.396)

    ci_99 = post.credible_interval_99
    # 1.2 ± 3 × 0.1 = [0.9, 1.5]
    assert ci_99 == (0.9, 1.5)


def test_posterior_std_dev_and_precision():
    post = Posterior(mean=1.2, variance=0.04, n_observations=5, observations=())
    assert post.std_dev == 0.2
    assert post.precision == 25.0


# ── update_belief: single and sequential updates ─────────────────────────


def test_update_belief_empty_returns_prior():
    """No observations → posterior equals prior (identity)."""
    prior = Prior(mean=1.0, variance=0.25)
    post = update_belief(prior, [])

    assert post.mean == prior.mean
    assert post.variance == prior.variance
    assert post.n_observations == 0
    assert post.observations == ()


def test_update_belief_single_observation_hand_computed():
    """Hand-computed check mirroring bayesian.py::_verify_worked_examples Example A.

    Prior N(1.0, 0.25) with noise σ = 0.15, single obs r = 1.3:
        τ_prior = 4.0, τ_obs = 1/0.0225 ≈ 44.444
        τ_post = 48.444 → σ²_post ≈ 0.02064
        μ_post = (4×1.0 + 44.444×1.3) / 48.444 ≈ 1.27521
    """
    prior = Prior(mean=1.0, variance=0.25)
    obs = [Observation(estimated=10.0, actual=13.0)]
    post = update_belief(prior, obs, observation_noise=0.15)

    assert abs(post.mean - 1.27521) < 0.001
    assert abs(post.variance - 0.02064) < 0.001
    assert post.n_observations == 1
    assert post.observations == (1.3,)


def test_update_belief_sequential_equals_batch():
    """Processing observations in two passes must equal processing all at once."""
    prior = Prior(mean=1.0, variance=0.25)
    obs = [
        Observation(estimated=10.0, actual=13.0),  # r = 1.3
        Observation(estimated=20.0, actual=22.0),  # r = 1.1
    ]

    # Batch
    batch = update_belief(prior, obs, observation_noise=0.15)

    # Sequential — feed the first posterior as the prior for the second step
    step1 = update_belief(prior, obs[:1], observation_noise=0.15)
    step2 = update_belief(
        Prior(mean=step1.mean, variance=step1.variance),
        obs[1:],
        observation_noise=0.15,
    )

    assert abs(step2.mean - batch.mean) < 1e-6
    assert abs(step2.variance - batch.variance) < 1e-6


def test_update_belief_narrows_variance():
    """Each observation must reduce posterior variance (more data = more certainty)."""
    prior = Prior(mean=1.0, variance=0.25)
    obs = [Observation(estimated=10.0, actual=11.0) for _ in range(5)]

    post = update_belief(prior, obs, observation_noise=0.15)
    # Posterior variance is strictly less than prior variance after any update
    assert post.variance < prior.variance
    # And less than after a single observation
    post_single = update_belief(prior, obs[:1], observation_noise=0.15)
    assert post.variance < post_single.variance


def test_update_belief_rejects_non_positive_noise():
    """observation_noise must be > 0 — guard matches app/bayesian/core.py."""
    prior = Prior()
    obs = [Observation(estimated=10.0, actual=11.0)]

    with pytest.raises(ValueError, match="Observation noise must be positive"):
        update_belief(prior, obs, observation_noise=0.0)
    with pytest.raises(ValueError, match="Observation noise must be positive"):
        update_belief(prior, obs, observation_noise=-0.1)


# ── EstimationLog + update_belief_with_history ───────────────────────────


def test_estimation_log_rejects_non_positive_noise():
    with pytest.raises(ValueError, match="Observation noise must be positive"):
        EstimationLog(observation_noise=0.0)


def test_update_belief_with_history_records_evolution():
    """Each observation produces one posterior; log.history grows in lockstep."""
    log = EstimationLog(prior=Prior(mean=1.0, variance=0.25), observation_noise=0.15)
    obs = [
        Observation(estimated=10.0, actual=13.0),
        Observation(estimated=20.0, actual=22.0),
        Observation(estimated=5.0, actual=6.0),
    ]

    posteriors = update_belief_with_history(log, obs)

    assert len(posteriors) == 3
    assert len(log.history) == 3
    assert len(log.observations) == 3

    # Each posterior reports the cumulative n_observations
    assert posteriors[0].n_observations == 1
    assert posteriors[1].n_observations == 2
    assert posteriors[2].n_observations == 3

    # Final posterior matches a direct batch update with the same inputs
    batch = update_belief(log.prior, obs, observation_noise=0.15)
    assert abs(posteriors[-1].mean - batch.mean) < 1e-6
    assert abs(posteriors[-1].variance - batch.variance) < 1e-6


def test_update_belief_with_history_continues_from_previous():
    """A second call to update_belief_with_history resumes from the last posterior."""
    log = EstimationLog(prior=Prior(mean=1.0, variance=0.25), observation_noise=0.15)
    all_obs = [
        Observation(estimated=10.0, actual=13.0),
        Observation(estimated=20.0, actual=22.0),
        Observation(estimated=5.0, actual=6.0),
    ]

    update_belief_with_history(log, all_obs[:2])
    update_belief_with_history(log, all_obs[2:])

    # Final posterior should match a single-batch update of all observations
    batch = update_belief(log.prior, all_obs, observation_noise=0.15)
    final = log.history[-1]
    assert abs(final.mean - batch.mean) < 1e-6
    assert abs(final.variance - batch.variance) < 1e-6
    assert final.n_observations == 3


# ── adjust_estimate ──────────────────────────────────────────────────────


def test_adjust_estimate_applies_delay_factor():
    """adjusted_expected = pert_expected × posterior.mean."""
    # Fabricate a posterior with delay factor 1.25
    post = Posterior(mean=1.25, variance=0.01, n_observations=10, observations=())
    result = adjust_estimate(pert_expected=10.0, posterior=post)

    assert result["pert_expected"] == 10.0
    assert result["delay_factor"] == 1.25
    assert result["adjusted_expected"] == 12.5
    assert result["n_observations"] == 10


def test_adjust_estimate_propagates_credible_intervals():
    """Confidence bands scale with the same delay factor ranges as the posterior."""
    post = Posterior(mean=1.25, variance=0.01, n_observations=10, observations=())
    result = adjust_estimate(pert_expected=10.0, posterior=post)

    # Posterior CIs: σ=0.1, so 68% = [1.15, 1.35], 95% = [1.054, 1.446]
    # Applied to pert_expected=10 → [11.5, 13.5] and [10.54, 14.46]
    assert result["adjusted_range_68"] == [11.5, 13.5]
    assert result["adjusted_range_95"] == [10.54, 14.46]


def test_adjust_estimate_output_keys():
    """Output dict must expose the full calibration contract."""
    post = Posterior(mean=1.0, variance=0.04, n_observations=3, observations=())
    result = adjust_estimate(pert_expected=10.0, posterior=post)

    expected_keys = {
        "pert_expected",
        "delay_factor",
        "adjusted_expected",
        "adjusted_range_68",
        "adjusted_range_95",
        "n_observations",
        "confidence",
    }
    assert set(result.keys()) == expected_keys


# ── _confidence_label ────────────────────────────────────────────────────


def test_confidence_label_regimes():
    """Each tier maps to the right label — thresholds: 0, 3, σ=0.15, σ=0.05."""
    # No data
    post = Posterior(mean=1.0, variance=0.25, n_observations=0, observations=())
    assert _confidence_label(post) == "no data — using prior"

    # Low: < 3 observations
    post = Posterior(mean=1.0, variance=0.01, n_observations=2, observations=())
    assert _confidence_label(post) == "low — fewer than 3 observations"

    # Moderate: σ > 0.15 (here σ = √0.04 = 0.2)
    post = Posterior(mean=1.0, variance=0.04, n_observations=10, observations=())
    assert _confidence_label(post) == "moderate — high variance in observations"

    # Good: 0.05 < σ ≤ 0.15 (here σ = 0.1)
    post = Posterior(mean=1.0, variance=0.01, n_observations=10, observations=())
    assert _confidence_label(post) == "good — converging"

    # High: σ ≤ 0.05 (here σ ≈ 0.032)
    post = Posterior(mean=1.0, variance=0.001, n_observations=20, observations=())
    assert _confidence_label(post) == "high — well-calibrated"


# ── visualise_belief_evolution ───────────────────────────────────────────


def test_visualise_belief_evolution_returns_figure():
    """The plot helper returns a matplotlib Figure for chaining/saving."""
    import matplotlib.pyplot as plt

    log = EstimationLog(prior=Prior(mean=1.0, variance=0.25), observation_noise=0.15)
    update_belief_with_history(
        log,
        [
            Observation(estimated=10.0, actual=13.0),
            Observation(estimated=20.0, actual=22.0),
        ],
    )

    fig = visualise_belief_evolution(log)
    assert fig is not None
    assert isinstance(fig, plt.Figure)
    plt.close(fig)


# ── Convergence sanity check ─────────────────────────────────────────────


def test_convergence_toward_true_delay_factor():
    """With consistent observations around r = 1.3, the posterior mean converges to ~1.3."""
    prior = Prior(mean=1.0, variance=0.25)
    # 20 observations all near r = 1.3 (small jitter so noise ≠ 0)
    obs = []
    for i in range(20):
        jitter = 0.01 * (1 if i % 2 == 0 else -1)
        obs.append(Observation(estimated=10.0, actual=13.0 + jitter))

    post = update_belief(prior, obs, observation_noise=0.15)

    # Posterior mean should be within 0.05 of the true 1.3
    assert abs(post.mean - 1.3) < 0.05
    # And standard deviation should have tightened dramatically
    assert post.std_dev < 0.1
    # Sanity: math.isfinite — no NaN/inf
    assert math.isfinite(post.mean)
    assert math.isfinite(post.variance)
