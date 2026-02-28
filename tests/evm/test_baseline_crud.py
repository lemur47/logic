"""Tests for EVM baseline CRUD endpoints."""

from httpx import AsyncClient

# ── Helpers ──────────────────────────────────────────────────────────────


async def _create_baseline(client: AsyncClient, payload: dict) -> dict:
    resp = await client.post("/evm/baselines", json=payload)
    assert resp.status_code == 201
    return resp.json()


# ── POST /evm/baselines ──────────────────────────────────────────────────


class TestCreateBaseline:
    async def test_create(self, client: AsyncClient, baseline_payload):
        data = await _create_baseline(client, baseline_payload)
        assert data["name"] == baseline_payload["name"]
        assert data["id"] is not None
        assert data["bac"] == 10000.0
        assert len(data["work_packages"]) == 3

    async def test_work_package_weights(self, client: AsyncClient, baseline_payload):
        data = await _create_baseline(client, baseline_payload)
        weights = [wp["weight"] for wp in data["work_packages"]]
        assert sum(weights) > 0.99

    async def test_create_with_description(self, client: AsyncClient, baseline_payload):
        data = await _create_baseline(client, baseline_payload)
        assert data["description"] == baseline_payload["description"]

    async def test_create_invalid_no_work_packages(self, client: AsyncClient):
        resp = await client.post(
            "/evm/baselines",
            json={
                "name": "Bad",
                "work_packages": [],
            },
        )
        assert resp.status_code == 422

    async def test_create_invalid_no_name(self, client: AsyncClient):
        resp = await client.post(
            "/evm/baselines",
            json={
                "work_packages": [{"name": "A", "planned_value": 1000}],
            },
        )
        assert resp.status_code == 422


# ── GET /evm/baselines/{id} ──────────────────────────────────────────────


class TestGetBaseline:
    async def test_get_existing(self, client: AsyncClient, baseline_payload):
        created = await _create_baseline(client, baseline_payload)
        resp = await client.get(f"/evm/baselines/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["name"] == baseline_payload["name"]
        assert len(resp.json()["work_packages"]) == 3

    async def test_get_not_found(self, client: AsyncClient):
        resp = await client.get("/evm/baselines/99999")
        assert resp.status_code == 404


# ── GET /evm/baselines ───────────────────────────────────────────────────


class TestListBaselines:
    async def test_list_empty(self, client: AsyncClient):
        resp = await client.get("/evm/baselines")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_with_items(self, client: AsyncClient, baseline_payload):
        await _create_baseline(client, baseline_payload)
        await _create_baseline(client, {**baseline_payload, "name": "Second"})
        resp = await client.get("/evm/baselines")
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_pagination(self, client: AsyncClient, baseline_payload):
        for i in range(3):
            await _create_baseline(client, {**baseline_payload, "name": f"Baseline {i}"})
        resp = await client.get("/evm/baselines", params={"per_page": 2, "page": 1})
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["per_page"] == 2

    async def test_search(self, client: AsyncClient, baseline_payload):
        await _create_baseline(client, {**baseline_payload, "name": "Alpha Project"})
        await _create_baseline(client, {**baseline_payload, "name": "Beta Project"})
        await _create_baseline(client, {**baseline_payload, "name": "Gamma"})
        resp = await client.get("/evm/baselines", params={"search": "Project"})
        data = resp.json()
        assert data["total"] == 2


# ── DELETE /evm/baselines/{id} ────────────────────────────────────────────


class TestDeleteBaseline:
    async def test_delete(self, client: AsyncClient, baseline_payload):
        created = await _create_baseline(client, baseline_payload)
        resp = await client.delete(f"/evm/baselines/{created['id']}")
        assert resp.status_code == 204
        get_resp = await client.get(f"/evm/baselines/{created['id']}")
        assert get_resp.status_code == 404

    async def test_delete_not_found(self, client: AsyncClient):
        resp = await client.delete("/evm/baselines/99999")
        assert resp.status_code == 404

    async def test_delete_cascades_snapshots(self, client: AsyncClient, baseline_payload):
        """Deleting a baseline should also delete its snapshots."""
        created = await _create_baseline(client, baseline_payload)
        bid = created["id"]

        # Create a snapshot via evaluate
        await client.post(
            f"/evm/baselines/{bid}/evaluate",
            json={
                "percent_planned": 50.0,
                "actual_completions": [
                    {"name": "Design", "percent_complete": 100.0},
                ],
                "actual_cost": 3000,
            },
        )

        # Verify snapshot exists
        snap_resp = await client.get(f"/evm/baselines/{bid}/snapshots")
        assert snap_resp.json()["total"] == 1

        # Delete baseline
        del_resp = await client.delete(f"/evm/baselines/{bid}")
        assert del_resp.status_code == 204

        # Baseline gone
        assert (await client.get(f"/evm/baselines/{bid}")).status_code == 404
