"""Tests for all 6 scenario CRUD endpoints under /tco/scenarios."""

from httpx import AsyncClient

# ── Helpers ──────────────────────────────────────────────────────────────────


async def _create_scenario(client: AsyncClient, payload: dict) -> dict:
    resp = await client.post("/tco/scenarios", json=payload)
    assert resp.status_code == 201
    return resp.json()


# ── POST /tco/scenarios ─────────────────────────────────────────────────────


class TestCreateScenario:
    async def test_create(self, client: AsyncClient, scenario_payload):
        data = await _create_scenario(client, scenario_payload)
        assert data["name"] == scenario_payload["name"]
        assert data["id"] is not None
        assert data["total_cost"] > 0

    async def test_create_computed_fields(self, client: AsyncClient, scenario_payload):
        data = await _create_scenario(client, scenario_payload)
        for field in (
            "total_cost",
            "annual_cost",
            "monthly_cost",
            "cost_per_day",
            "npv_tco",
            "npv_annual",
        ):
            assert field in data

    async def test_create_with_tags(self, client: AsyncClient, scenario_payload):
        data = await _create_scenario(client, scenario_payload)
        assert data["tags"] == ["test", "demo"]

    async def test_create_invalid_rejected(self, client: AsyncClient):
        resp = await client.post("/tco/scenarios", json={"name": "Bad"})
        assert resp.status_code == 422


# ── GET /tco/scenarios/{id} ─────────────────────────────────────────────────


class TestGetScenario:
    async def test_get_existing(self, client: AsyncClient, scenario_payload):
        created = await _create_scenario(client, scenario_payload)
        resp = await client.get(f"/tco/scenarios/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["name"] == scenario_payload["name"]

    async def test_get_not_found(self, client: AsyncClient):
        resp = await client.get("/tco/scenarios/99999")
        assert resp.status_code == 404


# ── GET /tco/scenarios ───────────────────────────────────────────────────────


class TestListScenarios:
    async def test_list_empty(self, client: AsyncClient):
        resp = await client.get("/tco/scenarios")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_with_items(self, client: AsyncClient, scenario_payload):
        await _create_scenario(client, scenario_payload)
        await _create_scenario(client, {**scenario_payload, "name": "Second"})
        resp = await client.get("/tco/scenarios")
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_pagination(self, client: AsyncClient, scenario_payload):
        for i in range(3):
            await _create_scenario(client, {**scenario_payload, "name": f"Scenario {i}"})
        resp = await client.get("/tco/scenarios", params={"per_page": 2, "page": 1})
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["per_page"] == 2

    async def test_search(self, client: AsyncClient, scenario_payload):
        await _create_scenario(client, {**scenario_payload, "name": "Alpha Plan"})
        await _create_scenario(client, {**scenario_payload, "name": "Beta Plan"})
        await _create_scenario(client, {**scenario_payload, "name": "Gamma"})
        resp = await client.get("/tco/scenarios", params={"search": "Plan"})
        data = resp.json()
        assert data["total"] == 2


# ── PATCH /tco/scenarios/{id} ───────────────────────────────────────────────


class TestUpdateScenario:
    async def test_update_name(self, client: AsyncClient, scenario_payload):
        created = await _create_scenario(client, scenario_payload)
        resp = await client.patch(f"/tco/scenarios/{created['id']}", json={"name": "Renamed"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed"

    async def test_update_recalculates_tco(self, client: AsyncClient, scenario_payload):
        created = await _create_scenario(client, scenario_payload)
        old_total = created["total_cost"]
        resp = await client.patch(f"/tco/scenarios/{created['id']}", json={"initial_price": 999999})
        assert resp.status_code == 200
        assert resp.json()["total_cost"] != old_total

    async def test_update_not_found(self, client: AsyncClient):
        resp = await client.patch("/tco/scenarios/99999", json={"name": "Ghost"})
        assert resp.status_code == 404


# ── DELETE /tco/scenarios/{id} ───────────────────────────────────────────────


class TestDeleteScenario:
    async def test_delete(self, client: AsyncClient, scenario_payload):
        created = await _create_scenario(client, scenario_payload)
        resp = await client.delete(f"/tco/scenarios/{created['id']}")
        assert resp.status_code == 204
        get_resp = await client.get(f"/tco/scenarios/{created['id']}")
        assert get_resp.status_code == 404

    async def test_delete_not_found(self, client: AsyncClient):
        resp = await client.delete("/tco/scenarios/99999")
        assert resp.status_code == 404


# ── GET /tco/scenarios/stats ─────────────────────────────────────────────────


class TestStats:
    async def test_stats_empty(self, client: AsyncClient):
        resp = await client.get("/tco/scenarios/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_scenarios"] == 0

    async def test_stats_with_data(self, client: AsyncClient, scenario_payload):
        await _create_scenario(client, scenario_payload)
        await _create_scenario(
            client, {**scenario_payload, "name": "Second", "initial_price": 200000}
        )
        resp = await client.get("/tco/scenarios/stats")
        data = resp.json()
        assert data["total_scenarios"] == 2
        assert data["avg_monthly_cost"] > 0
