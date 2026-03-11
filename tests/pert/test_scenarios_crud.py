"""Tests for all CRUD endpoints under /pert/scenarios."""

from httpx import AsyncClient

# ── Helpers ──────────────────────────────────────────────────────────────────


async def _create_scenario(client: AsyncClient, payload: dict) -> dict:
    resp = await client.post("/pert/scenarios", json=payload)
    assert resp.status_code == 201
    return resp.json()


# ── POST /pert/scenarios ─────────────────────────────────────────────────────


class TestCreateScenario:
    async def test_create(self, client: AsyncClient, scenario_payload):
        data = await _create_scenario(client, scenario_payload)
        assert data["name"] == scenario_payload["name"]
        assert data["id"] is not None
        assert data["total_expected"] > 0

    async def test_create_computed_fields(self, client: AsyncClient, scenario_payload):
        data = await _create_scenario(client, scenario_payload)
        for field in (
            "total_expected",
            "total_std_dev",
            "total_variance",
            "range_68",
            "range_95",
            "range_99",
        ):
            assert field in data

    async def test_create_with_tags(self, client: AsyncClient, scenario_payload):
        data = await _create_scenario(client, scenario_payload)
        assert data["tags"] == ["test", "demo"]

    async def test_create_tasks_have_computed_estimates(
        self, client: AsyncClient, scenario_payload
    ):
        data = await _create_scenario(client, scenario_payload)
        for task in data["tasks"]:
            assert "expected" in task
            assert "std_dev" in task
            assert "variance" in task

    async def test_create_invalid_rejected(self, client: AsyncClient):
        resp = await client.post("/pert/scenarios", json={"name": "Bad"})
        assert resp.status_code == 422

    async def test_create_empty_tasks_rejected(self, client: AsyncClient):
        resp = await client.post(
            "/pert/scenarios",
            json={"name": "Empty", "tasks": []},
        )
        assert resp.status_code == 422


# ── GET /pert/scenarios/{id} ─────────────────────────────────────────────────


class TestGetScenario:
    async def test_get_existing(self, client: AsyncClient, scenario_payload):
        created = await _create_scenario(client, scenario_payload)
        resp = await client.get(f"/pert/scenarios/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["name"] == scenario_payload["name"]

    async def test_get_not_found(self, client: AsyncClient):
        resp = await client.get("/pert/scenarios/99999")
        assert resp.status_code == 404


# ── GET /pert/scenarios ───────────────────────────────────────────────────────


class TestListScenarios:
    async def test_list_empty(self, client: AsyncClient):
        resp = await client.get("/pert/scenarios")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_with_items(self, client: AsyncClient, scenario_payload):
        await _create_scenario(client, scenario_payload)
        await _create_scenario(client, {**scenario_payload, "name": "Second"})
        resp = await client.get("/pert/scenarios")
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_pagination(self, client: AsyncClient, scenario_payload):
        for i in range(3):
            await _create_scenario(client, {**scenario_payload, "name": f"Scenario {i}"})
        resp = await client.get("/pert/scenarios", params={"per_page": 2, "page": 1})
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["per_page"] == 2

    async def test_search(self, client: AsyncClient, scenario_payload):
        await _create_scenario(client, {**scenario_payload, "name": "Alpha Plan"})
        await _create_scenario(client, {**scenario_payload, "name": "Beta Plan"})
        await _create_scenario(client, {**scenario_payload, "name": "Gamma"})
        resp = await client.get("/pert/scenarios", params={"search": "Plan"})
        data = resp.json()
        assert data["total"] == 2


# ── PATCH /pert/scenarios/{id} ───────────────────────────────────────────────


class TestUpdateScenario:
    async def test_update_name(self, client: AsyncClient, scenario_payload):
        created = await _create_scenario(client, scenario_payload)
        resp = await client.patch(f"/pert/scenarios/{created['id']}", json={"name": "Renamed"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed"

    async def test_update_recalculates_pert(self, client: AsyncClient, scenario_payload):
        created = await _create_scenario(client, scenario_payload)
        old_expected = created["total_expected"]
        new_tasks = [
            {"name": "Big Task", "optimistic": 20, "most_likely": 40, "pessimistic": 80},
        ]
        resp = await client.patch(f"/pert/scenarios/{created['id']}", json={"tasks": new_tasks})
        assert resp.status_code == 200
        assert resp.json()["total_expected"] != old_expected

    async def test_update_preserves_tasks_when_only_name_changes(
        self, client: AsyncClient, scenario_payload
    ):
        created = await _create_scenario(client, scenario_payload)
        resp = await client.patch(f"/pert/scenarios/{created['id']}", json={"name": "Renamed"})
        assert resp.status_code == 200
        assert resp.json()["total_expected"] == created["total_expected"]
        assert len(resp.json()["tasks"]) == len(created["tasks"])

    async def test_update_not_found(self, client: AsyncClient):
        resp = await client.patch("/pert/scenarios/99999", json={"name": "Ghost"})
        assert resp.status_code == 404


# ── DELETE /pert/scenarios/{id} ───────────────────────────────────────────────


class TestDeleteScenario:
    async def test_delete(self, client: AsyncClient, scenario_payload):
        created = await _create_scenario(client, scenario_payload)
        resp = await client.delete(f"/pert/scenarios/{created['id']}")
        assert resp.status_code == 204
        get_resp = await client.get(f"/pert/scenarios/{created['id']}")
        assert get_resp.status_code == 404

    async def test_delete_not_found(self, client: AsyncClient):
        resp = await client.delete("/pert/scenarios/99999")
        assert resp.status_code == 404
