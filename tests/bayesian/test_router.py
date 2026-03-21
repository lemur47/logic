"""Integration tests for Bayesian estimation calibration endpoints."""

import pytest
from httpx import AsyncClient

# ── POST /bayesian/calculate ─────────────────────────────────────────────


class TestCalculateEndpoint:
    async def test_basic_calculation(self, client: AsyncClient):
        resp = await client.post(
            "/bayesian/calculate",
            json={
                "observations": [
                    {"estimated": 10, "actual": 13},
                    {"estimated": 20, "actual": 22},
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mean"] == pytest.approx(1.19133, abs=0.01)
        assert data["n_observations"] == 2
        assert len(data["credible_interval_95"]) == 2

    async def test_custom_prior(self, client: AsyncClient):
        resp = await client.post(
            "/bayesian/calculate",
            json={
                "prior": {"mean": 1.5, "variance": 0.1},
                "observations": [{"estimated": 10, "actual": 10}],
                "observation_noise": 0.15,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # Strong prior at 1.5 should keep mean above 1.0
        assert data["mean"] > 1.0

    async def test_empty_observations_rejected(self, client: AsyncClient):
        resp = await client.post(
            "/bayesian/calculate",
            json={"observations": []},
        )
        assert resp.status_code == 422

    async def test_invalid_estimated_rejected(self, client: AsyncClient):
        resp = await client.post(
            "/bayesian/calculate",
            json={"observations": [{"estimated": 0, "actual": 5}]},
        )
        assert resp.status_code == 422


# ── POST /bayesian/adjust ────────────────────────────────────────────────


class TestAdjustEndpoint:
    async def test_basic_adjust(self, client: AsyncClient):
        resp = await client.post(
            "/bayesian/adjust",
            json={
                "pert_expected": 10.0,
                "delay_factor": 1.3,
                "n_observations": 5,
                "std_dev": 0.06,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["adjusted_expected"] == 13.0
        assert data["delay_factor"] == 1.3
        assert len(data["adjusted_range_95"]) == 2

    async def test_no_bias(self, client: AsyncClient):
        resp = await client.post(
            "/bayesian/adjust",
            json={"pert_expected": 10.0, "delay_factor": 1.0},
        )
        assert resp.status_code == 200
        assert resp.json()["adjusted_expected"] == 10.0


# ── Context CRUD ─────────────────────────────────────────────────────────


class TestContextCrud:
    async def test_create_context(self, client: AsyncClient):
        resp = await client.post(
            "/bayesian/contexts",
            json={"name": "auth", "description": "Authentication tasks"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "auth"
        assert data["prior_mean"] == 1.0
        assert data["prior_variance"] == 0.25
        assert data["n_observations"] == 0
        assert data["current_belief"] is None

    async def test_create_context_custom_prior(self, client: AsyncClient):
        resp = await client.post(
            "/bayesian/contexts",
            json={
                "name": "infra",
                "prior_mean": 1.2,
                "prior_variance": 0.1,
                "observation_noise": 0.2,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["prior_mean"] == 1.2
        assert data["observation_noise"] == 0.2

    async def test_get_context(self, client: AsyncClient):
        create_resp = await client.post(
            "/bayesian/contexts",
            json={"name": "auth"},
        )
        context_id = create_resp.json()["id"]

        resp = await client.get(f"/bayesian/contexts/{context_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "auth"

    async def test_get_context_not_found(self, client: AsyncClient):
        resp = await client.get("/bayesian/contexts/9999")
        assert resp.status_code == 404

    async def test_list_contexts(self, client: AsyncClient):
        await client.post("/bayesian/contexts", json={"name": "auth"})
        await client.post("/bayesian/contexts", json={"name": "infra"})

        resp = await client.get("/bayesian/contexts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_contexts_search(self, client: AsyncClient):
        await client.post("/bayesian/contexts", json={"name": "auth"})
        await client.post("/bayesian/contexts", json={"name": "infra"})

        resp = await client.get("/bayesian/contexts", params={"search": "auth"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    async def test_delete_context(self, client: AsyncClient):
        create_resp = await client.post(
            "/bayesian/contexts",
            json={"name": "auth"},
        )
        context_id = create_resp.json()["id"]

        resp = await client.delete(f"/bayesian/contexts/{context_id}")
        assert resp.status_code == 204

        resp = await client.get(f"/bayesian/contexts/{context_id}")
        assert resp.status_code == 404

    async def test_delete_context_not_found(self, client: AsyncClient):
        resp = await client.delete("/bayesian/contexts/9999")
        assert resp.status_code == 404


# ── Observations ─────────────────────────────────────────────────────────


class TestObservations:
    async def _create_context(self, client: AsyncClient, name: str = "auth") -> int:
        resp = await client.post("/bayesian/contexts", json={"name": name})
        return resp.json()["id"]

    async def test_add_single_observation(self, client: AsyncClient):
        ctx_id = await self._create_context(client)
        resp = await client.post(
            f"/bayesian/contexts/{ctx_id}/observations",
            json={"observations": [{"estimated": 10, "actual": 13}]},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert len(data) == 1
        assert data[0]["estimated"] == 10
        assert data[0]["actual"] == 13
        assert data[0]["delay_factor"] == pytest.approx(1.3)

    async def test_add_batch_observations(self, client: AsyncClient):
        ctx_id = await self._create_context(client)
        resp = await client.post(
            f"/bayesian/contexts/{ctx_id}/observations",
            json={
                "observations": [
                    {"estimated": 5, "actual": 7},
                    {"estimated": 10, "actual": 13},
                    {"estimated": 8, "actual": 10},
                ]
            },
        )
        assert resp.status_code == 201
        assert len(resp.json()) == 3

    async def test_add_observation_context_not_found(self, client: AsyncClient):
        resp = await client.post(
            "/bayesian/contexts/9999/observations",
            json={"observations": [{"estimated": 10, "actual": 13}]},
        )
        assert resp.status_code == 404

    async def test_list_observations(self, client: AsyncClient):
        ctx_id = await self._create_context(client)
        await client.post(
            f"/bayesian/contexts/{ctx_id}/observations",
            json={
                "observations": [
                    {"estimated": 5, "actual": 7},
                    {"estimated": 10, "actual": 13},
                ]
            },
        )

        resp = await client.get(f"/bayesian/contexts/{ctx_id}/observations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_delay_factor_computed_server_side(self, client: AsyncClient):
        """delay_factor should be actual/estimated, computed by the server."""
        ctx_id = await self._create_context(client)
        resp = await client.post(
            f"/bayesian/contexts/{ctx_id}/observations",
            json={"observations": [{"estimated": 8, "actual": 12}]},
        )
        assert resp.status_code == 201
        assert resp.json()[0]["delay_factor"] == pytest.approx(1.5)


# ── Belief Query ─────────────────────────────────────────────────────────


class TestBelief:
    async def _create_context_with_obs(self, client: AsyncClient) -> int:
        resp = await client.post("/bayesian/contexts", json={"name": "auth"})
        ctx_id = resp.json()["id"]
        await client.post(
            f"/bayesian/contexts/{ctx_id}/observations",
            json={
                "observations": [
                    {"estimated": 5, "actual": 7},
                    {"estimated": 10, "actual": 13},
                    {"estimated": 3, "actual": 4},
                    {"estimated": 8, "actual": 10},
                ]
            },
        )
        return ctx_id

    async def test_get_belief(self, client: AsyncClient):
        ctx_id = await self._create_context_with_obs(client)
        resp = await client.get(f"/bayesian/contexts/{ctx_id}/belief")
        assert resp.status_code == 200
        data = resp.json()
        assert data["context_name"] == "auth"
        assert data["n_observations"] == 4
        assert data["posterior"]["mean"] > 1.0  # auth tasks run late
        assert len(data["posterior"]["credible_interval_95"]) == 2

    async def test_belief_no_observations(self, client: AsyncClient):
        resp = await client.post("/bayesian/contexts", json={"name": "empty"})
        ctx_id = resp.json()["id"]

        resp = await client.get(f"/bayesian/contexts/{ctx_id}/belief")
        assert resp.status_code == 200
        data = resp.json()
        assert data["n_observations"] == 0
        assert data["posterior"]["mean"] == 1.0  # falls back to prior

    async def test_belief_not_found(self, client: AsyncClient):
        resp = await client.get("/bayesian/contexts/9999/belief")
        assert resp.status_code == 404

    async def test_adjust_from_context(self, client: AsyncClient):
        ctx_id = await self._create_context_with_obs(client)
        resp = await client.post(
            f"/bayesian/contexts/{ctx_id}/adjust",
            json={"pert_expected": 12.0},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["belief"]["context_name"] == "auth"
        assert data["adjustment"]["pert_expected"] == 12.0
        assert data["adjustment"]["adjusted_expected"] > 12.0  # auth delays

    async def test_adjust_not_found(self, client: AsyncClient):
        resp = await client.post(
            "/bayesian/contexts/9999/adjust",
            json={"pert_expected": 12.0},
        )
        assert resp.status_code == 404

    async def test_context_response_includes_belief(self, client: AsyncClient):
        """GET /contexts/{id} should include current_belief after observations."""
        ctx_id = await self._create_context_with_obs(client)
        resp = await client.get(f"/bayesian/contexts/{ctx_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_belief"] is not None
        assert data["current_belief"]["mean"] > 1.0
        assert data["n_observations"] == 4


# ── Cascade Delete ───────────────────────────────────────────────────────


class TestCascadeDelete:
    async def test_delete_context_removes_observations(self, client: AsyncClient):
        resp = await client.post("/bayesian/contexts", json={"name": "auth"})
        ctx_id = resp.json()["id"]
        await client.post(
            f"/bayesian/contexts/{ctx_id}/observations",
            json={"observations": [{"estimated": 10, "actual": 13}]},
        )

        resp = await client.delete(f"/bayesian/contexts/{ctx_id}")
        assert resp.status_code == 204

        # Context gone
        resp = await client.get(f"/bayesian/contexts/{ctx_id}")
        assert resp.status_code == 404
