# test_dirichlet_drift.py
"""Tests for the Dirichlet-drift Monte Carlo standalone module.

Covers the six test categories from the approved scope:

1. Degenerate reducibility — neutral posteriors collapse to plain MC.
2. Mean shift — posterior mu shifts the duration distribution proportionally.
3. Variance propagation — posterior sigma widens the result spread.
4. Dirichlet blending — unclassified tasks get the weighted blend.
5. Re-estimation monotonicity — smaller sigma → no wider spread.
6. Cross-project carry-forward — prior_new = posterior_old yields identical
   results.

Plus validation tests for malformed inputs.
"""

import numpy as np
import pytest
from dirichlet_drift import (
    DriftConfig,
    DriftTask,
    Posterior,
    RiskClass,
    simulate_with_drift,
)
from montecarlo import Task, simulate_schedule

# ── 1. Degenerate Reducibility ───────────────────────────────────────────


class TestDegenerateReducibility:
    """With neutral posteriors (mu=1.0, sigma=0), the drift multiplier is
    identically 1.0 and the result distribution must converge to plain
    Monte Carlo within statistical tolerance."""

    @pytest.fixture()
    def neutral_config(self):
        return DriftConfig(
            risk_classes=(
                RiskClass("c1", prior_alpha=1.0, posterior=Posterior(mu=1.0, sigma=0.0)),
                RiskClass("c2", prior_alpha=1.0, posterior=Posterior(mu=1.0, sigma=0.0)),
            ),
            seed=42,
        )

    @pytest.fixture()
    def schedule(self):
        plain = [
            Task("Design", 3, 5, 10),
            Task("Build", 5, 8, 15),
            Task("Test", 2, 4, 8),
        ]
        drift = [
            DriftTask("Design", 3, 5, 10),
            DriftTask("Build", 5, 8, 15),
            DriftTask("Test", 2, 4, 8),
        ]
        return plain, drift

    def test_mean_matches_plain_mc(self, schedule, neutral_config):
        plain, drift = schedule
        plain_r = simulate_schedule(plain, n_simulations=50_000, seed=42)
        drift_r = simulate_with_drift(drift, neutral_config, n_simulations=50_000)

        plain_mean = float(np.mean(plain_r.durations))
        drift_mean = float(np.mean(drift_r.durations))

        assert abs(plain_mean - drift_mean) / plain_mean < 0.01, (
            f"Drift mean {drift_mean:.3f} differs from plain {plain_mean:.3f} by >1%"
        )

    def test_percentiles_match_plain_mc(self, schedule, neutral_config):
        plain, drift = schedule
        plain_r = simulate_schedule(plain, n_simulations=50_000, seed=42)
        drift_r = simulate_with_drift(drift, neutral_config, n_simulations=50_000)

        for p in ["P50", "P75", "P85", "P95"]:
            rel = abs(plain_r.percentiles[p] - drift_r.percentiles[p]) / plain_r.percentiles[p]
            assert rel < 0.02, (
                f"{p} drift {drift_r.percentiles[p]:.2f} differs from plain "
                f"{plain_r.percentiles[p]:.2f} by >2%"
            )

    def test_drift_multiplier_is_identically_one(self, neutral_config):
        """With sigma=0 across all classes, the drift array should be
        exactly 1.0 in every iteration — independent of Dirichlet weights
        because uniform mu=1.0 across classes gives sum_k w_k * 1 = 1."""
        # Single unclassified task: drift = sum_k w_k * mu_k. With all
        # mu_k=1, this is sum(w) = 1.0 exactly.
        tasks = [DriftTask("X", 5, 5, 5)]  # degenerate base distribution
        result = simulate_with_drift(tasks, neutral_config, n_simulations=1_000)
        # Base task is constant 5; drift is identically 1 within float
        # precision (Dirichlet weights sum to ~1.0 with O(1e-16) noise).
        np.testing.assert_allclose(result.durations, 5.0, rtol=1e-12)


# ── 2. Mean Shift ────────────────────────────────────────────────────────


class TestMeanShift:
    """Posterior mu = 1.3 should shift the duration distribution by ~30%."""

    @pytest.fixture()
    def tasks(self):
        return [
            DriftTask("A", 3, 5, 10, risk_class="overrun"),
            DriftTask("B", 5, 8, 15, risk_class="overrun"),
        ]

    def test_30pct_shift_in_mean(self, tasks):
        neutral = DriftConfig(
            risk_classes=(RiskClass("overrun", posterior=Posterior(mu=1.0, sigma=0.0)),),
            seed=42,
        )
        shifted = DriftConfig(
            risk_classes=(RiskClass("overrun", posterior=Posterior(mu=1.3, sigma=0.0)),),
            seed=42,
        )

        n = simulate_with_drift(tasks, neutral, n_simulations=50_000)
        s = simulate_with_drift(tasks, shifted, n_simulations=50_000)

        ratio = float(np.mean(s.durations)) / float(np.mean(n.durations))
        assert 1.28 < ratio < 1.32, f"Expected ~1.30 ratio, got {ratio:.4f}"

    def test_negative_shift_works(self, tasks):
        """mu = 0.7 should shorten by ~30%."""
        neutral = DriftConfig(
            risk_classes=(RiskClass("overrun", posterior=Posterior(mu=1.0, sigma=0.0)),),
            seed=42,
        )
        shorter = DriftConfig(
            risk_classes=(RiskClass("overrun", posterior=Posterior(mu=0.7, sigma=0.0)),),
            seed=42,
        )

        n = simulate_with_drift(tasks, neutral, n_simulations=50_000)
        s = simulate_with_drift(tasks, shorter, n_simulations=50_000)

        ratio = float(np.mean(s.durations)) / float(np.mean(n.durations))
        assert 0.68 < ratio < 0.72, f"Expected ~0.70 ratio, got {ratio:.4f}"


# ── 3. Variance Propagation ──────────────────────────────────────────────


class TestVarianceProgagation:
    """Posterior sigma > 0 should widen the duration spread relative to
    sigma = 0 (which is the plain-MC baseline once mu = 1)."""

    def test_diffuse_posterior_widens_spread(self):
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

        assert diff_std > sharp_std * 1.5, (
            f"Diffuse spread {diff_std:.2f} should be >1.5× sharp spread {sharp_std:.2f}"
        )

    def test_p95_widens_with_sigma(self):
        """P95 should be markedly higher when posterior is uncertain."""
        tasks = [DriftTask("A", 3, 5, 10, risk_class="x")]
        sharp = DriftConfig(
            risk_classes=(RiskClass("x", posterior=Posterior(mu=1.0, sigma=0.0)),), seed=42
        )
        diffuse = DriftConfig(
            risk_classes=(RiskClass("x", posterior=Posterior(mu=1.0, sigma=0.3)),), seed=42
        )

        sharp_r = simulate_with_drift(tasks, sharp, n_simulations=50_000)
        diff_r = simulate_with_drift(tasks, diffuse, n_simulations=50_000)

        assert diff_r.percentiles["P95"] > sharp_r.percentiles["P95"]


# ── 4. Dirichlet Blending ────────────────────────────────────────────────


class TestDirichletBlending:
    """Unclassified tasks (risk_class=None) should be blended via
    Dirichlet weights across all classes: d_j = sum_k w_k * mu_k."""

    def test_uniform_blend_two_classes(self):
        """Two classes with mu={1.0, 2.0} and uniform alpha → expected
        drift ≈ 1.5 → mean duration ≈ 1.5 × pert_expected."""
        tasks = [DriftTask("Mystery", 4, 6, 10)]
        config = DriftConfig(
            risk_classes=(
                RiskClass("low", prior_alpha=1.0, posterior=Posterior(mu=1.0, sigma=0.0)),
                RiskClass("high", prior_alpha=1.0, posterior=Posterior(mu=2.0, sigma=0.0)),
            ),
            seed=42,
        )

        result = simulate_with_drift(tasks, config, n_simulations=50_000)
        pert_expected = (4 + 4 * 6 + 10) / 6  # 6.333
        expected_mean = pert_expected * 1.5

        actual_mean = float(np.mean(result.durations))
        assert abs(actual_mean - expected_mean) / expected_mean < 0.02

    def test_skewed_alpha_pulls_blend(self):
        """Heavy alpha on the high class should pull mean drift toward 2.0."""
        tasks = [DriftTask("Mystery", 4, 6, 10)]

        # alpha = (1, 9) → expected weight high = 9/10 = 0.9
        # expected drift = 0.1*1.0 + 0.9*2.0 = 1.9
        config = DriftConfig(
            risk_classes=(
                RiskClass("low", prior_alpha=1.0, posterior=Posterior(mu=1.0, sigma=0.0)),
                RiskClass("high", prior_alpha=9.0, posterior=Posterior(mu=2.0, sigma=0.0)),
            ),
            seed=42,
        )

        result = simulate_with_drift(tasks, config, n_simulations=50_000)
        pert_expected = (4 + 4 * 6 + 10) / 6
        expected_mean = pert_expected * 1.9

        actual_mean = float(np.mean(result.durations))
        assert abs(actual_mean - expected_mean) / expected_mean < 0.02

        # Diagnostics: high class should dominate
        assert result.class_contribution["high"]["mean_weight"] > 0.85

    def test_classified_task_ignores_blend(self):
        """A task bound to a class uses that class's posterior directly,
        not the Dirichlet blend."""
        tasks = [DriftTask("Bound", 4, 6, 10, risk_class="low")]
        config = DriftConfig(
            risk_classes=(
                RiskClass("low", prior_alpha=1.0, posterior=Posterior(mu=1.0, sigma=0.0)),
                RiskClass("high", prior_alpha=1.0, posterior=Posterior(mu=2.0, sigma=0.0)),
            ),
            seed=42,
        )
        result = simulate_with_drift(tasks, config, n_simulations=50_000)
        pert_expected = (4 + 4 * 6 + 10) / 6
        # Expected: drift = 1.0 (low's posterior), so mean ≈ pert_expected
        actual_mean = float(np.mean(result.durations))
        assert abs(actual_mean - pert_expected) / pert_expected < 0.02


# ── 5. Re-Estimation Monotonicity ────────────────────────────────────────


class TestReEstimationMonotonicity:
    """As posterior sigma shrinks (more observations, less uncertainty),
    the result spread should not widen. Tests the contract that
    reducing input uncertainty cannot hurt output certainty."""

    def test_std_dev_non_increasing(self):
        tasks = [
            DriftTask("A", 3, 5, 10, risk_class="x"),
            DriftTask("B", 5, 8, 15, risk_class="x"),
        ]
        sigmas = [0.5, 0.3, 0.15, 0.05, 0.0]
        stds = []
        for sigma in sigmas:
            cfg = DriftConfig(
                risk_classes=(RiskClass("x", posterior=Posterior(mu=1.0, sigma=sigma)),),
                seed=42,
            )
            r = simulate_with_drift(tasks, cfg, n_simulations=50_000)
            stds.append(float(np.std(r.durations)))

        for prev, curr in zip(stds, stds[1:], strict=False):
            # Allow 1% slack per step for sampling noise.
            assert prev * 1.01 >= curr, (
                f"Spread should be non-increasing as sigma shrinks; sigmas={sigmas}, stds={stds}"
            )


# ── 6. Cross-Project Carry-Forward ───────────────────────────────────────


class TestCrossProjectCarryForward:
    """Starting a new project with prior_new = posterior_old should be a
    no-op — no hidden state. Same input → same output (with same seed)."""

    def test_identical_runs_match_exactly(self):
        tasks = [
            DriftTask("A", 3, 5, 10, risk_class="auth"),
            DriftTask("B", 5, 8, 15, risk_class="auth"),
        ]
        carried_posterior = Posterior(mu=1.2, sigma=0.15)
        cfg_old = DriftConfig(
            risk_classes=(RiskClass("auth", posterior=carried_posterior),), seed=99
        )
        cfg_new = DriftConfig(
            risk_classes=(RiskClass("auth", posterior=carried_posterior),), seed=99
        )

        r_old = simulate_with_drift(tasks, cfg_old, n_simulations=20_000)
        r_new = simulate_with_drift(tasks, cfg_new, n_simulations=20_000)

        np.testing.assert_array_equal(r_old.durations, r_new.durations)

    def test_carried_posterior_distinct_from_uninformative(self):
        """A project that carries forward a tight posterior produces a
        visibly different distribution from one starting fresh with the
        uninformative fallback."""
        tasks = [DriftTask("A", 3, 5, 10, risk_class="auth")]

        # Cold start: no posterior → uninformative fallback (1.0, 0.5)
        cold = DriftConfig(risk_classes=(RiskClass("auth"),), seed=42)
        # Warm start: carried posterior (1.2, 0.05) — narrow, biased
        warm = DriftConfig(
            risk_classes=(RiskClass("auth", posterior=Posterior(mu=1.2, sigma=0.05)),),
            seed=42,
        )

        cold_r = simulate_with_drift(tasks, cold, n_simulations=50_000)
        warm_r = simulate_with_drift(tasks, warm, n_simulations=50_000)

        # Warm mean should be biased upward (~20%) and tighter spread.
        cold_mean = float(np.mean(cold_r.durations))
        warm_mean = float(np.mean(warm_r.durations))
        cold_std = float(np.std(cold_r.durations))
        warm_std = float(np.std(warm_r.durations))

        assert warm_mean > cold_mean  # warm has higher mu
        assert warm_std < cold_std  # warm has tighter posterior


# ── Validation ───────────────────────────────────────────────────────────


class TestValidation:
    """Input validation and error conditions."""

    def test_posterior_negative_mu(self):
        with pytest.raises(ValueError, match="mu must be >= 0"):
            Posterior(mu=-0.1, sigma=0.5)

    def test_posterior_negative_sigma(self):
        with pytest.raises(ValueError, match="sigma must be >= 0"):
            Posterior(mu=1.0, sigma=-0.5)

    def test_riskclass_non_positive_alpha(self):
        with pytest.raises(ValueError, match="prior_alpha must be > 0"):
            RiskClass("x", prior_alpha=0.0)

    def test_riskclass_empty_name(self):
        with pytest.raises(ValueError, match="non-empty"):
            RiskClass("")

    def test_driftconfig_empty_classes(self):
        with pytest.raises(ValueError, match="at least one risk_class"):
            DriftConfig(risk_classes=())

    def test_driftconfig_duplicate_class_names(self):
        with pytest.raises(ValueError, match="Duplicate"):
            DriftConfig(
                risk_classes=(
                    RiskClass("dupe"),
                    RiskClass("dupe"),
                )
            )

    def test_task_unknown_risk_class(self):
        tasks = [DriftTask("A", 3, 5, 10, risk_class="ghost")]
        cfg = DriftConfig(risk_classes=(RiskClass("real"),), seed=1)
        with pytest.raises(ValueError, match="unknown risk_class"):
            simulate_with_drift(tasks, cfg, n_simulations=100)

    def test_drifttask_inherits_task_validation(self):
        """DriftTask should reject the same malformed three-point
        estimates as Task does."""
        with pytest.raises(ValueError, match="cannot exceed most likely"):
            DriftTask("Bad", 10, 5, 20)


# ── Smoke / Result Shape ─────────────────────────────────────────────────


class TestResultShape:
    """Sanity checks on the DriftResult container itself."""

    def test_result_fields_populated(self):
        tasks = [DriftTask("A", 3, 5, 10, risk_class="x")]
        cfg = DriftConfig(
            risk_classes=(RiskClass("x", posterior=Posterior(mu=1.0, sigma=0.1)),),
            seed=42,
        )
        result = simulate_with_drift(tasks, cfg, n_simulations=1_000)

        assert result.n_simulations == 1_000
        assert result.durations.shape == (1_000,)
        assert set(result.percentiles.keys()) == {"P50", "P75", "P85", "P95"}
        assert "x" in result.class_contribution
        assert result.dirichlet_weights_used.shape == (1_000, 1)
        # Single-class Dirichlet → all weights are 1.0 within float noise.
        np.testing.assert_allclose(result.dirichlet_weights_used, 1.0, rtol=1e-12)

    def test_critical_path_frequency_for_dependent_schedule(self):
        tasks = [
            DriftTask("A", 2, 4, 6, risk_class="x"),
            DriftTask("B", 1, 3, 8, risk_class="x"),
            DriftTask("C", 3, 5, 9, risk_class="x", depends_on=("A", "B")),
        ]
        cfg = DriftConfig(
            risk_classes=(RiskClass("x", posterior=Posterior(mu=1.0, sigma=0.0)),),
            seed=42,
        )
        result = simulate_with_drift(tasks, cfg, n_simulations=20_000)

        # C is the terminal task — always critical.
        assert result.critical_path_frequency["C"] > 0.99
        # A and B both contribute to the critical path some of the time.
        assert result.critical_path_frequency["A"] > 0.1
        assert result.critical_path_frequency["B"] > 0.1
