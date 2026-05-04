"""
Dirichlet-drift Monte Carlo tests — core layer + /simulate router.

Core categories (from the Sprint 7 scope doc):
1. Degenerate reducibility — drift-with-neutral-posteriors ≈ plain MC.
2. Mean shift — posterior mu propagates linearly into the duration mean.
3. Variance propagation — posterior sigma widens the duration spread.
4. Dirichlet blending — unclassified tasks blend across classes by weight.
5. Re-estimation monotonicity — narrower posterior never widens the result.
6. Cross-project carry-forward — same seed + inputs → bit-identical output.

Router tests verify that legacy payloads (no drift_config) preserve the
existing SimulationResult contract, and that drift payloads return the
extended DriftResult shape.
"""

import numpy as np
import pytest
from httpx import AsyncClient

from app.montecarlo.core import (
    DEFAULT_UNINFORMATIVE_POSTERIOR_SIGMA,
    DriftConfig,
    DriftResult,
    DriftTask,
    Posterior,
    RiskClass,
    Task,
    simulate_schedule,
    simulate_with_drift,
)

# =============================================================================
# Posterior dataclass
# =============================================================================


class TestPosterior:
    def test_defaults(self):
        p = Posterior(mu=1.0, sigma=0.1)
        assert p.mu == 1.0
        assert p.sigma == 0.1

    def test_negative_mu_raises(self):
        with pytest.raises(ValueError, match="mu must be >= 0"):
            Posterior(mu=-0.1, sigma=0.1)

    def test_negative_sigma_raises(self):
        with pytest.raises(ValueError, match="sigma must be >= 0"):
            Posterior(mu=1.0, sigma=-0.01)

    def test_zero_sigma_is_degenerate_point_mass(self):
        p = Posterior(mu=1.2, sigma=0.0)
        assert p.sigma == 0.0


# =============================================================================
# RiskClass dataclass
# =============================================================================


class TestRiskClass:
    def test_defaults(self):
        rc = RiskClass(name="auth")
        assert rc.name == "auth"
        assert rc.prior_alpha == 1.0
        assert rc.posterior is None

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="non-empty string"):
            RiskClass(name="")

    def test_zero_prior_alpha_raises(self):
        with pytest.raises(ValueError, match="prior_alpha must be > 0"):
            RiskClass(name="x", prior_alpha=0.0)

    def test_negative_prior_alpha_raises(self):
        with pytest.raises(ValueError, match="prior_alpha must be > 0"):
            RiskClass(name="x", prior_alpha=-1.0)

    def test_effective_posterior_uses_supplied(self):
        p = Posterior(mu=1.5, sigma=0.2)
        rc = RiskClass(name="x", posterior=p)
        assert rc.effective_posterior == p

    def test_effective_posterior_falls_back_to_uninformative(self):
        rc = RiskClass(name="x")
        ep = rc.effective_posterior
        assert ep.mu == 1.0
        assert ep.sigma == DEFAULT_UNINFORMATIVE_POSTERIOR_SIGMA


# =============================================================================
# DriftTask + DriftConfig
# =============================================================================


class TestDriftTaskConfig:
    def test_drift_task_inherits_pert_validation(self):
        with pytest.raises(ValueError, match="cannot exceed most likely"):
            DriftTask("A", 6, 5, 10)

    def test_drift_task_default_risk_class_is_none(self):
        t = DriftTask("A", 2, 5, 10)
        assert t.risk_class is None

    def test_drift_task_with_risk_class(self):
        t = DriftTask("A", 2, 5, 10, risk_class="auth")
        assert t.risk_class == "auth"

    def test_drift_config_empty_classes_raises(self):
        with pytest.raises(ValueError, match="at least one risk_class"):
            DriftConfig(risk_classes=())

    def test_drift_config_duplicate_class_names_raises(self):
        with pytest.raises(ValueError, match="Duplicate risk class names"):
            DriftConfig(risk_classes=(RiskClass("x"), RiskClass("x")))


# =============================================================================
# simulate_with_drift — core behaviour
# =============================================================================


def _neutral_config(*names: str, seed: int | None = 42) -> DriftConfig:
    """Helper: a DriftConfig where every class has a degenerate mu=1, sigma=0
    posterior — drift collapses to 1.0 everywhere."""
    return DriftConfig(
        risk_classes=tuple(
            RiskClass(name=n, posterior=Posterior(mu=1.0, sigma=0.0)) for n in names
        ),
        seed=seed,
    )


class TestSimulateWithDrift:
    def test_empty_tasks_raises(self):
        with pytest.raises(ValueError, match="At least one task"):
            simulate_with_drift([], _neutral_config("x"))

    def test_unknown_risk_class_raises(self):
        tasks = [DriftTask("A", 2, 5, 10, risk_class="ghost")]
        with pytest.raises(ValueError, match="unknown risk_class 'ghost'"):
            simulate_with_drift(tasks, _neutral_config("real"))

    def test_returns_drift_result(self):
        tasks = [DriftTask("A", 2, 5, 10)]
        result = simulate_with_drift(tasks, _neutral_config("x"), n_simulations=500)
        assert isinstance(result, DriftResult)
        assert result.n_simulations == 500
        assert result.dirichlet_weights_used.shape == (500, 1)

    def test_class_contribution_records_bound_count(self):
        tasks = [
            DriftTask("A", 2, 5, 10, risk_class="x"),
            DriftTask("B", 2, 5, 10, risk_class="x"),
            DriftTask("C", 2, 5, 10),  # unclassified
        ]
        result = simulate_with_drift(tasks, _neutral_config("x"), n_simulations=200)
        assert result.class_contribution["x"]["n_tasks_bound"] == 2

    def test_dirichlet_weights_sum_to_one(self):
        """Each per-iteration Dirichlet draw should sum to ~1 by definition."""
        tasks = [DriftTask("A", 2, 5, 10)]
        result = simulate_with_drift(tasks, _neutral_config("a", "b", "c"), n_simulations=1000)
        row_sums = result.dirichlet_weights_used.sum(axis=1)
        np.testing.assert_allclose(row_sums, np.ones_like(row_sums), atol=1e-10)


# =============================================================================
# Six PoC-aligned behaviour categories
# =============================================================================


class TestDegenerateReducibility:
    """Drift with mu=1, sigma=0 must collapse to plain MC within tolerance."""

    @pytest.mark.parametrize("seed", [0, 1, 7, 42])
    def test_mean_within_one_percent(self, seed):
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
        plain = simulate_schedule(plain_tasks, n_simulations=20_000, seed=seed)
        drift = simulate_with_drift(
            drift_tasks, _neutral_config("c1", "c2", seed=seed), n_simulations=20_000
        )
        rel_err = abs(np.mean(plain.durations) - np.mean(drift.durations)) / np.mean(
            plain.durations
        )
        assert rel_err < 0.01


class TestMeanShift:
    def test_thirty_percent_shift(self):
        tasks = [
            DriftTask("A", 3, 5, 10, risk_class="x"),
            DriftTask("B", 5, 8, 15, risk_class="x"),
        ]
        neutral = DriftConfig(
            risk_classes=(RiskClass("x", posterior=Posterior(mu=1.0, sigma=0.0)),), seed=42
        )
        shifted = DriftConfig(
            risk_classes=(RiskClass("x", posterior=Posterior(mu=1.3, sigma=0.0)),), seed=42
        )
        n = simulate_with_drift(tasks, neutral, n_simulations=20_000)
        s = simulate_with_drift(tasks, shifted, n_simulations=20_000)
        ratio = float(np.mean(s.durations)) / float(np.mean(n.durations))
        assert 1.28 < ratio < 1.32

    def test_zero_mu_collapses_durations(self):
        """Posterior mu=0 forces every drift to 0 → all durations zero."""
        tasks = [DriftTask("A", 2, 5, 10, risk_class="dead")]
        cfg = DriftConfig(
            risk_classes=(RiskClass("dead", posterior=Posterior(mu=0.0, sigma=0.0)),),
            seed=42,
        )
        result = simulate_with_drift(tasks, cfg, n_simulations=500)
        assert float(np.max(result.durations)) == pytest.approx(0.0)


class TestVariancePropagation:
    def test_sigma_widens_spread(self):
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
        sharp_r = simulate_with_drift(tasks, sharp, n_simulations=20_000)
        diff_r = simulate_with_drift(tasks, diffuse, n_simulations=20_000)
        assert float(np.std(diff_r.durations)) > float(np.std(sharp_r.durations)) * 1.5


class TestDirichletBlending:
    def test_uniform_blend_equals_average_drift(self):
        tasks = [DriftTask("Mystery", 4, 6, 10)]
        cfg = DriftConfig(
            risk_classes=(
                RiskClass("low", prior_alpha=1.0, posterior=Posterior(mu=1.0, sigma=0.0)),
                RiskClass("high", prior_alpha=1.0, posterior=Posterior(mu=2.0, sigma=0.0)),
            ),
            seed=42,
        )
        result = simulate_with_drift(tasks, cfg, n_simulations=20_000)
        pert_expected = (4 + 4 * 6 + 10) / 6
        expected_mean = pert_expected * 1.5  # uniform blend over 1.0/2.0
        rel_err = abs(float(np.mean(result.durations)) - expected_mean) / expected_mean
        assert rel_err < 0.02

    def test_skewed_alpha_pulls_blend(self):
        """Heavy alpha on one class pulls the blended drift toward its mu."""
        tasks = [DriftTask("Mystery", 4, 6, 10)]
        cfg = DriftConfig(
            risk_classes=(
                RiskClass("low", prior_alpha=10.0, posterior=Posterior(mu=1.0, sigma=0.0)),
                RiskClass("high", prior_alpha=1.0, posterior=Posterior(mu=2.0, sigma=0.0)),
            ),
            seed=42,
        )
        result = simulate_with_drift(tasks, cfg, n_simulations=20_000)
        # Expected blended drift ≈ (10*1 + 1*2)/11 ≈ 1.0909
        pert_expected = (4 + 4 * 6 + 10) / 6
        expected_mean = pert_expected * (10 / 11 * 1.0 + 1 / 11 * 2.0)
        rel_err = abs(float(np.mean(result.durations)) - expected_mean) / expected_mean
        assert rel_err < 0.02


class TestReEstimationMonotonicity:
    def test_narrowing_sigma_weakly_reduces_spread(self):
        tasks = [
            DriftTask("A", 3, 5, 10, risk_class="x"),
            DriftTask("B", 5, 8, 15, risk_class="x"),
        ]
        sigmas = [0.4, 0.2, 0.1, 0.0]
        stds = []
        for sigma in sigmas:
            cfg = DriftConfig(
                risk_classes=(RiskClass("x", posterior=Posterior(mu=1.0, sigma=sigma)),),
                seed=42,
            )
            stds.append(
                float(np.std(simulate_with_drift(tasks, cfg, n_simulations=20_000).durations))
            )
        for a, b in zip(stds, stds[1:], strict=False):
            assert a >= b * 0.99  # weak monotonic non-increasing


class TestCrossProjectCarryForward:
    def test_same_seed_same_inputs_identical_output(self):
        tasks = [
            DriftTask("A", 3, 5, 10, risk_class="auth"),
            DriftTask("B", 5, 8, 15, risk_class="auth"),
        ]
        cfg_one = DriftConfig(
            risk_classes=(RiskClass("auth", posterior=Posterior(mu=1.2, sigma=0.15)),), seed=99
        )
        cfg_two = DriftConfig(
            risk_classes=(RiskClass("auth", posterior=Posterior(mu=1.2, sigma=0.15)),), seed=99
        )
        r1 = simulate_with_drift(tasks, cfg_one, n_simulations=5_000)
        r2 = simulate_with_drift(tasks, cfg_two, n_simulations=5_000)
        np.testing.assert_array_equal(r1.durations, r2.durations)

    def test_different_seed_different_output(self):
        tasks = [DriftTask("A", 3, 5, 10, risk_class="x")]
        cfg_a = DriftConfig(
            risk_classes=(RiskClass("x", posterior=Posterior(mu=1.0, sigma=0.2)),), seed=1
        )
        cfg_b = DriftConfig(
            risk_classes=(RiskClass("x", posterior=Posterior(mu=1.0, sigma=0.2)),), seed=2
        )
        r1 = simulate_with_drift(tasks, cfg_a, n_simulations=2_000)
        r2 = simulate_with_drift(tasks, cfg_b, n_simulations=2_000)
        assert not np.array_equal(r1.durations, r2.durations)


# =============================================================================
# Schedule topology — drift respects dependencies
# =============================================================================


class TestDriftWithDependencies:
    def test_topological_sort_applied(self):
        tasks = [
            DriftTask("End", 1, 2, 4, depends_on=("Start",), risk_class="x"),
            DriftTask("Start", 1, 2, 4, risk_class="x"),
        ]
        cfg = DriftConfig(
            risk_classes=(RiskClass("x", posterior=Posterior(mu=1.0, sigma=0.0)),), seed=42
        )
        result = simulate_with_drift(tasks, cfg, n_simulations=500)
        # Two sequential tasks of expected ~2.17 each → mean total ≈ 4.33.
        assert 3.5 < float(np.mean(result.durations)) < 5.0
        assert "Start" in result.critical_path_frequency
        assert "End" in result.critical_path_frequency

    def test_circular_dependency_raises(self):
        tasks = [
            DriftTask("A", 1, 2, 3, depends_on=("B",)),
            DriftTask("B", 1, 2, 3, depends_on=("A",)),
        ]
        with pytest.raises(ValueError, match="Circular dependency"):
            simulate_with_drift(tasks, _neutral_config("x"), n_simulations=100)


# =============================================================================
# Histogram edge case — zero-range distributions
# =============================================================================


class TestHistogramEdgeCase:
    def test_constant_durations_collapse_to_spike(self):
        """Tasks with O==M==P + neutral posterior produce constant durations.
        np.histogram with bins=50 rejects zero-range arrays; the drift module
        must handle this by emitting a single spike bin."""
        tasks = [DriftTask("A", 5, 5, 5, risk_class="x")]
        cfg = DriftConfig(
            risk_classes=(RiskClass("x", posterior=Posterior(mu=1.0, sigma=0.0)),), seed=42
        )
        result = simulate_with_drift(tasks, cfg, n_simulations=200)
        assert result.histogram["counts"] == [200]


# =============================================================================
# Router — additivity of /simulate
# =============================================================================


class TestSimulateRouterLegacyPath:
    """Legacy payloads (no drift_config) must keep returning SimulationResult."""

    async def test_legacy_payload_still_works(self, client: AsyncClient):
        resp = await client.post(
            "/montecarlo/simulate",
            json={
                "tasks": [
                    {"name": "A", "optimistic": 2, "most_likely": 5, "pessimistic": 10},
                    {"name": "B", "optimistic": 3, "most_likely": 6, "pessimistic": 12},
                ],
                "config": {"num_simulations": 500, "seed": 42},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "class_contribution" not in data
        assert "dirichlet_weights_used" not in data
        assert data["n_simulations"] == 500

    async def test_risk_class_field_ignored_without_drift_config(self, client: AsyncClient):
        """A risk_class on a TaskInput without drift_config is silently ignored."""
        resp = await client.post(
            "/montecarlo/simulate",
            json={
                "tasks": [
                    {
                        "name": "A",
                        "optimistic": 2,
                        "most_likely": 5,
                        "pessimistic": 10,
                        "risk_class": "auth",
                    },
                ],
                "config": {"num_simulations": 200, "seed": 42},
            },
        )
        assert resp.status_code == 200
        assert "class_contribution" not in resp.json()


class TestSimulateRouterDriftPath:
    async def test_drift_payload_returns_drift_result(self, client: AsyncClient):
        resp = await client.post(
            "/montecarlo/simulate",
            json={
                "tasks": [
                    {
                        "name": "A",
                        "optimistic": 3,
                        "most_likely": 5,
                        "pessimistic": 10,
                        "risk_class": "auth",
                    },
                    {
                        "name": "B",
                        "optimistic": 5,
                        "most_likely": 8,
                        "pessimistic": 15,
                        "risk_class": "auth",
                    },
                ],
                "config": {"num_simulations": 500, "seed": 42},
                "drift_config": {
                    "risk_classes": [
                        {
                            "name": "auth",
                            "prior_alpha": 1.0,
                            "posterior": {"mu": 1.2, "sigma": 0.1},
                        },
                    ],
                    "seed": 42,
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "class_contribution" in data
        assert "dirichlet_weights_used" in data
        assert "auth" in data["class_contribution"]
        assert data["class_contribution"]["auth"]["n_tasks_bound"] == 2
        assert len(data["dirichlet_weights_used"]) == 500
        assert len(data["dirichlet_weights_used"][0]) == 1

    async def test_drift_mean_shift_visible_via_router(self, client: AsyncClient):
        """Posterior mu=1.4 → mean ~40% higher than neutral path, end-to-end."""
        base = {
            "tasks": [
                {
                    "name": "A",
                    "optimistic": 4,
                    "most_likely": 6,
                    "pessimistic": 10,
                    "risk_class": "x",
                },
            ],
            "config": {"num_simulations": 5_000, "seed": 42},
        }
        neutral = await client.post(
            "/montecarlo/simulate",
            json={
                **base,
                "drift_config": {
                    "risk_classes": [
                        {"name": "x", "posterior": {"mu": 1.0, "sigma": 0.0}},
                    ],
                    "seed": 42,
                },
            },
        )
        shifted = await client.post(
            "/montecarlo/simulate",
            json={
                **base,
                "drift_config": {
                    "risk_classes": [
                        {"name": "x", "posterior": {"mu": 1.4, "sigma": 0.0}},
                    ],
                    "seed": 42,
                },
            },
        )
        ratio = shifted.json()["mean"] / neutral.json()["mean"]
        assert 1.38 < ratio < 1.42

    async def test_drift_unclassified_task_blends(self, client: AsyncClient):
        resp = await client.post(
            "/montecarlo/simulate",
            json={
                "tasks": [
                    {"name": "Mystery", "optimistic": 4, "most_likely": 6, "pessimistic": 10},
                ],
                "config": {"num_simulations": 2_000, "seed": 42},
                "drift_config": {
                    "risk_classes": [
                        {"name": "low", "posterior": {"mu": 1.0, "sigma": 0.0}},
                        {"name": "high", "posterior": {"mu": 2.0, "sigma": 0.0}},
                    ],
                    "seed": 42,
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["class_contribution"]["low"]["n_tasks_bound"] == 0
        assert data["class_contribution"]["high"]["n_tasks_bound"] == 0

    async def test_drift_seed_falls_back_to_config_seed(self, client: AsyncClient):
        """Two requests with the same config.seed and no drift_config.seed should
        yield identical drift results."""
        payload = {
            "tasks": [
                {
                    "name": "A",
                    "optimistic": 3,
                    "most_likely": 5,
                    "pessimistic": 10,
                    "risk_class": "x",
                },
            ],
            "config": {"num_simulations": 500, "seed": 7},
            "drift_config": {
                "risk_classes": [
                    {"name": "x", "posterior": {"mu": 1.1, "sigma": 0.05}},
                ],
            },
        }
        r1 = await client.post("/montecarlo/simulate", json=payload)
        r2 = await client.post("/montecarlo/simulate", json=payload)
        assert r1.json()["mean"] == r2.json()["mean"]
        assert r1.json()["histogram"] == r2.json()["histogram"]

    async def test_drift_unknown_risk_class_returns_400(self, client: AsyncClient):
        resp = await client.post(
            "/montecarlo/simulate",
            json={
                "tasks": [
                    {
                        "name": "A",
                        "optimistic": 2,
                        "most_likely": 5,
                        "pessimistic": 10,
                        "risk_class": "ghost",
                    },
                ],
                "config": {"num_simulations": 200, "seed": 42},
                "drift_config": {
                    "risk_classes": [
                        {"name": "real", "posterior": {"mu": 1.0, "sigma": 0.0}},
                    ],
                },
            },
        )
        assert resp.status_code == 400
        assert "ghost" in resp.json()["detail"]

    async def test_drift_empty_risk_classes_returns_422(self, client: AsyncClient):
        """Pydantic min_length=1 on risk_classes should reject empty list."""
        resp = await client.post(
            "/montecarlo/simulate",
            json={
                "tasks": [
                    {"name": "A", "optimistic": 2, "most_likely": 5, "pessimistic": 10},
                ],
                "config": {"num_simulations": 100},
                "drift_config": {"risk_classes": []},
            },
        )
        assert resp.status_code == 422

    async def test_drift_negative_posterior_mu_returns_422(self, client: AsyncClient):
        resp = await client.post(
            "/montecarlo/simulate",
            json={
                "tasks": [
                    {"name": "A", "optimistic": 2, "most_likely": 5, "pessimistic": 10},
                ],
                "config": {"num_simulations": 100},
                "drift_config": {
                    "risk_classes": [
                        {"name": "x", "posterior": {"mu": -1.0, "sigma": 0.1}},
                    ],
                },
            },
        )
        assert resp.status_code == 422

    async def test_drift_zero_prior_alpha_returns_422(self, client: AsyncClient):
        resp = await client.post(
            "/montecarlo/simulate",
            json={
                "tasks": [
                    {"name": "A", "optimistic": 2, "most_likely": 5, "pessimistic": 10},
                ],
                "config": {"num_simulations": 100},
                "drift_config": {
                    "risk_classes": [
                        {
                            "name": "x",
                            "prior_alpha": 0.0,
                            "posterior": {"mu": 1.0, "sigma": 0.0},
                        },
                    ],
                },
            },
        )
        assert resp.status_code == 422

    async def test_drift_uninformative_fallback_when_posterior_omitted(self, client: AsyncClient):
        """A risk class with no posterior should not error — falls back to N(1.0, 0.5)."""
        resp = await client.post(
            "/montecarlo/simulate",
            json={
                "tasks": [
                    {
                        "name": "A",
                        "optimistic": 3,
                        "most_likely": 5,
                        "pessimistic": 10,
                        "risk_class": "vague",
                    },
                ],
                "config": {"num_simulations": 1_000, "seed": 42},
                "drift_config": {"risk_classes": [{"name": "vague"}]},
            },
        )
        assert resp.status_code == 200
        assert "vague" in resp.json()["class_contribution"]
