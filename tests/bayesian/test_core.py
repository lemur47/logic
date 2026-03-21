"""Unit tests for bayesian/core.py pure calculation functions."""

import pytest

from app.bayesian.core import (
    Observation,
    Posterior,
    Prior,
    _confidence_label,
    adjust_estimate,
    update_belief,
)

# ── Prior ────────────────────────────────────────────────────────────────


class TestPrior:
    def test_defaults(self):
        p = Prior()
        assert p.mean == 1.0
        assert p.variance == 0.25

    def test_precision(self):
        p = Prior(mean=1.0, variance=0.25)
        assert p.precision == pytest.approx(4.0)

    def test_std_dev(self):
        p = Prior(mean=1.0, variance=0.25)
        assert p.std_dev == pytest.approx(0.5)

    def test_zero_variance_raises(self):
        with pytest.raises(ValueError, match="positive"):
            Prior(mean=1.0, variance=0)

    def test_negative_variance_raises(self):
        with pytest.raises(ValueError, match="positive"):
            Prior(mean=1.0, variance=-0.1)


# ── Observation ──────────────────────────────────────────────────────────


class TestObservation:
    def test_delay_factor(self):
        obs = Observation(estimated=10.0, actual=13.0)
        assert obs.delay_factor == pytest.approx(1.3)

    def test_default_context(self):
        obs = Observation(estimated=5.0, actual=5.0)
        assert obs.context == "default"

    def test_zero_estimated_raises(self):
        with pytest.raises(ValueError, match="positive"):
            Observation(estimated=0, actual=5.0)

    def test_negative_actual_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            Observation(estimated=5.0, actual=-1.0)

    def test_zero_actual_allowed(self):
        obs = Observation(estimated=5.0, actual=0.0)
        assert obs.delay_factor == pytest.approx(0.0)


# ── update_belief ────────────────────────────────────────────────────────


class TestUpdateBelief:
    """Verified against hand-computed values from the PoC."""

    def test_empty_observations_returns_prior(self):
        prior = Prior(mean=1.0, variance=0.25)
        posterior = update_belief(prior, [])
        assert posterior.mean == 1.0
        assert posterior.variance == 0.25
        assert posterior.n_observations == 0
        assert posterior.observations == ()

    def test_single_observation(self):
        """Example A from PoC: single obs r=1.3."""
        prior = Prior(mean=1.0, variance=0.25)
        obs = [Observation(estimated=10.0, actual=13.0)]
        posterior = update_belief(prior, obs, observation_noise=0.15)

        assert posterior.mean == pytest.approx(1.27521, abs=0.001)
        assert posterior.variance == pytest.approx(0.02064, abs=0.001)
        assert posterior.n_observations == 1

    def test_two_observations(self):
        """Example B from PoC: two obs r=1.3, r=1.1."""
        prior = Prior(mean=1.0, variance=0.25)
        obs = [
            Observation(estimated=10.0, actual=13.0),
            Observation(estimated=20.0, actual=22.0),
        ]
        posterior = update_belief(prior, obs, observation_noise=0.15)

        assert posterior.mean == pytest.approx(1.19133, abs=0.001)
        assert posterior.variance == pytest.approx(0.01077, abs=0.001)
        assert posterior.n_observations == 2

    def test_sequential_equals_batch(self):
        """Sequential processing must equal batch processing."""
        prior = Prior(mean=1.0, variance=0.25)
        obs = [
            Observation(estimated=10.0, actual=13.0),
            Observation(estimated=20.0, actual=22.0),
        ]

        # Batch
        batch = update_belief(prior, obs, observation_noise=0.15)

        # Sequential
        step1 = update_belief(prior, obs[:1], observation_noise=0.15)
        step2 = update_belief(
            Prior(mean=step1.mean, variance=step1.variance),
            obs[1:],
            observation_noise=0.15,
        )

        assert step2.mean == pytest.approx(batch.mean, abs=1e-6)
        assert step2.variance == pytest.approx(batch.variance, abs=1e-6)

    def test_negative_noise_raises(self):
        prior = Prior(mean=1.0, variance=0.25)
        obs = [Observation(estimated=10.0, actual=13.0)]
        with pytest.raises(ValueError, match="positive"):
            update_belief(prior, obs, observation_noise=-0.1)

    def test_zero_noise_raises(self):
        prior = Prior(mean=1.0, variance=0.25)
        obs = [Observation(estimated=10.0, actual=13.0)]
        with pytest.raises(ValueError, match="positive"):
            update_belief(prior, obs, observation_noise=0)

    def test_many_observations_narrows_variance(self):
        """More observations should reduce posterior variance."""
        prior = Prior(mean=1.0, variance=0.25)
        obs = [Observation(estimated=10.0, actual=13.0, context="auth") for _ in range(20)]
        posterior = update_belief(prior, obs, observation_noise=0.15)

        assert posterior.variance < prior.variance
        assert posterior.variance < 0.002  # should be very tight with 20 obs

    def test_custom_prior(self):
        """A strong prior (low variance) should resist a single observation."""
        strong_prior = Prior(mean=1.5, variance=0.01)
        obs = [Observation(estimated=10.0, actual=10.0)]  # r = 1.0
        posterior = update_belief(strong_prior, obs, observation_noise=0.15)

        # Should stay close to prior mean, not jump to 1.0
        assert posterior.mean > 1.3


# ── Posterior ────────────────────────────────────────────────────────────


class TestPosterior:
    def test_credible_intervals(self):
        post = Posterior(mean=1.3, variance=0.01, n_observations=5, observations=())
        ci_68 = post.credible_interval_68
        ci_95 = post.credible_interval_95
        ci_99 = post.credible_interval_99

        # 68% is narrowest, 99% is widest
        assert ci_68[0] > ci_95[0] > ci_99[0]
        assert ci_68[1] < ci_95[1] < ci_99[1]

        # All centered on mean
        mid_68 = (ci_68[0] + ci_68[1]) / 2
        assert mid_68 == pytest.approx(1.3, abs=0.01)


# ── adjust_estimate ──────────────────────────────────────────────────────


class TestAdjustEstimate:
    def test_basic_adjustment(self):
        posterior = Posterior(mean=1.3, variance=0.01, n_observations=5, observations=())
        result = adjust_estimate(10.0, posterior)

        assert result["pert_expected"] == 10.0
        assert result["delay_factor"] == 1.3
        assert result["adjusted_expected"] == 13.0
        assert result["n_observations"] == 5
        assert len(result["adjusted_range_68"]) == 2
        assert len(result["adjusted_range_95"]) == 2

    def test_no_bias_factor(self):
        posterior = Posterior(mean=1.0, variance=0.01, n_observations=10, observations=())
        result = adjust_estimate(10.0, posterior)
        assert result["adjusted_expected"] == 10.0

    def test_zero_observations_confidence(self):
        posterior = Posterior(mean=1.0, variance=0.25, n_observations=0, observations=())
        result = adjust_estimate(10.0, posterior)
        assert result["confidence"] == "no data — using prior"


# ── _confidence_label ────────────────────────────────────────────────────


class TestConfidenceLabel:
    def test_no_data(self):
        p = Posterior(mean=1.0, variance=0.25, n_observations=0, observations=())
        assert _confidence_label(p) == "no data — using prior"

    def test_low(self):
        p = Posterior(mean=1.2, variance=0.01, n_observations=2, observations=())
        assert "low" in _confidence_label(p)

    def test_high(self):
        p = Posterior(mean=1.2, variance=0.001, n_observations=20, observations=())
        assert "high" in _confidence_label(p)
