"""Tests for EVM evaluate and snapshot endpoints."""

import pytest
from httpx import AsyncClient

# ── Helpers ──────────────────────────────────────────────────────────────


async def _create_baseline(client: AsyncClient, payload: dict) -> dict:
    resp = await client.post("/evm/baselines", json=payload)
    assert resp.status_code == 201
    return resp.json()


# ── POST /evm/baselines/{id}/evaluate ────────────────────────────────────


class TestEvaluateEndpoint:
    async def test_evaluate_basic(self, client: AsyncClient, baseline_payload, evaluate_payload):
        created = await _create_baseline(client, baseline_payload)
        resp = await client.post(f"/evm/baselines/{created['id']}/evaluate", json=evaluate_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "metrics" in data
        assert "health" in data
        assert "work_packages" in data
        assert "input" in data

    async def test_evaluate_metrics_computed(
        self, client: AsyncClient, baseline_payload, evaluate_payload
    ):
        created = await _create_baseline(client, baseline_payload)
        resp = await client.post(f"/evm/baselines/{created['id']}/evaluate", json=evaluate_payload)
        data = resp.json()
        # BAC = 10000, PV = 10000 * 0.5 = 5000
        assert data["input"]["pv"] == pytest.approx(5000.0, abs=0.01)
        # EV = 3000*1.0 + 5000*0.4 + 2000*0.0 = 5000
        assert data["input"]["ev"] == pytest.approx(5000.0, abs=0.01)

    async def test_evaluate_work_package_breakdown(
        self, client: AsyncClient, baseline_payload, evaluate_payload
    ):
        created = await _create_baseline(client, baseline_payload)
        resp = await client.post(f"/evm/baselines/{created['id']}/evaluate", json=evaluate_payload)
        data = resp.json()
        assert len(data["work_packages"]) == 3
        design_wp = next(wp for wp in data["work_packages"] if wp["name"] == "Design")
        assert design_wp["earned_value"] == pytest.approx(3000.0, abs=0.01)
        assert design_wp["percent_complete"] == 100.0

    async def test_evaluate_missing_wp_defaults_zero(self, client: AsyncClient, baseline_payload):
        created = await _create_baseline(client, baseline_payload)
        resp = await client.post(
            f"/evm/baselines/{created['id']}/evaluate",
            json={
                "percent_planned": 50.0,
                "actual_completions": [
                    {"name": "Design", "percent_complete": 100.0},
                ],
                "actual_cost": 3000,
            },
        )
        data = resp.json()
        build_wp = next(wp for wp in data["work_packages"] if wp["name"] == "Build")
        assert build_wp["percent_complete"] == 0.0
        assert build_wp["earned_value"] == 0.0

    async def test_evaluate_baseline_not_found(self, client: AsyncClient, evaluate_payload):
        resp = await client.post("/evm/baselines/99999/evaluate", json=evaluate_payload)
        assert resp.status_code == 404

    async def test_evaluate_with_custom_thresholds(self, client: AsyncClient, baseline_payload):
        created = await _create_baseline(client, baseline_payload)
        resp = await client.post(
            f"/evm/baselines/{created['id']}/evaluate",
            json={
                "percent_planned": 50.0,
                "actual_completions": [],
                "actual_cost": 5000,
                "thresholds": {
                    "spi_off_track": 0.95,
                    "spi_at_risk": 1.0,
                    "cpi_off_track": 0.95,
                    "cpi_at_risk": 1.0,
                },
            },
        )
        assert resp.status_code == 200
        assert resp.json()["health"]["status"] == "off_track"

    async def test_evaluate_creates_snapshot(
        self, client: AsyncClient, baseline_payload, evaluate_payload
    ):
        created = await _create_baseline(client, baseline_payload)
        bid = created["id"]

        # Evaluate
        await client.post(f"/evm/baselines/{bid}/evaluate", json=evaluate_payload)

        # Check snapshot was created
        snap_resp = await client.get(f"/evm/baselines/{bid}/snapshots")
        assert snap_resp.status_code == 200
        data = snap_resp.json()
        assert data["total"] == 1
        assert data["items"][0]["baseline_id"] == bid

    async def test_evaluate_invalid_percent_planned(self, client: AsyncClient, baseline_payload):
        created = await _create_baseline(client, baseline_payload)
        resp = await client.post(
            f"/evm/baselines/{created['id']}/evaluate",
            json={"percent_planned": 150, "actual_cost": 1000},
        )
        assert resp.status_code == 422


# ── GET /evm/baselines/{id}/snapshots ────────────────────────────────────


class TestSnapshotsEndpoint:
    async def test_empty_snapshots(self, client: AsyncClient, baseline_payload):
        created = await _create_baseline(client, baseline_payload)
        resp = await client.get(f"/evm/baselines/{created['id']}/snapshots")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_multiple_snapshots(
        self, client: AsyncClient, baseline_payload, evaluate_payload
    ):
        created = await _create_baseline(client, baseline_payload)
        bid = created["id"]

        # Create 3 snapshots
        for pct in [25.0, 50.0, 75.0]:
            await client.post(
                f"/evm/baselines/{bid}/evaluate",
                json={**evaluate_payload, "percent_planned": pct},
            )

        resp = await client.get(f"/evm/baselines/{bid}/snapshots")
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    async def test_snapshots_reverse_chronological(
        self, client: AsyncClient, baseline_payload, evaluate_payload
    ):
        created = await _create_baseline(client, baseline_payload)
        bid = created["id"]

        for pct in [25.0, 50.0, 75.0]:
            await client.post(
                f"/evm/baselines/{bid}/evaluate",
                json={**evaluate_payload, "percent_planned": pct},
            )

        resp = await client.get(f"/evm/baselines/{bid}/snapshots")
        items = resp.json()["items"]
        # Most recent (75%) should be first
        assert items[0]["percent_planned"] == 75.0
        assert items[2]["percent_planned"] == 25.0

    async def test_snapshots_pagination(
        self, client: AsyncClient, baseline_payload, evaluate_payload
    ):
        created = await _create_baseline(client, baseline_payload)
        bid = created["id"]

        for pct in [20.0, 40.0, 60.0]:
            await client.post(
                f"/evm/baselines/{bid}/evaluate",
                json={**evaluate_payload, "percent_planned": pct},
            )

        resp = await client.get(
            f"/evm/baselines/{bid}/snapshots",
            params={"per_page": 2, "page": 1},
        )
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2

    async def test_snapshots_baseline_not_found(self, client: AsyncClient):
        resp = await client.get("/evm/baselines/99999/snapshots")
        assert resp.status_code == 404
