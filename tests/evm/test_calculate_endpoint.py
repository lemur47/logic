"""Tests for stateless EVM endpoints: POST /evm/calculate and POST /evm/health."""

import pytest
from httpx import AsyncClient

# ── POST /evm/calculate ───────────────────────────────────────────────────


class TestCalculateEndpoint:
    async def test_on_track(self, client: AsyncClient):
        resp = await client.post(
            "/evm/calculate",
            json={
                "pv": 100,
                "ev": 100,
                "ac": 100,
                "bac": 200,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["metrics"]["sv"] == 0
        assert data["metrics"]["spi"] == pytest.approx(1.0)
        assert data["metrics"]["cpi"] == pytest.approx(1.0)
        assert data["health"]["status"] == "on_track"

    async def test_behind_and_over(self, client: AsyncClient):
        resp = await client.post(
            "/evm/calculate",
            json={
                "pv": 100,
                "ev": 80,
                "ac": 110,
                "bac": 200,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["metrics"]["sv"] == -20
        assert data["metrics"]["spi"] == pytest.approx(0.8)
        assert data["metrics"]["cpi"] == pytest.approx(0.7273, abs=0.0001)
        assert data["health"]["status"] == "off_track"

    async def test_inf_becomes_null_in_json(self, client: AsyncClient):
        resp = await client.post(
            "/evm/calculate",
            json={
                "pv": 100,
                "ev": 0,
                "ac": 0,
                "bac": 200,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["metrics"]["cpi"] is None

    async def test_combined_metrics_and_health(self, client: AsyncClient):
        resp = await client.post(
            "/evm/calculate",
            json={
                "pv": 100,
                "ev": 90,
                "ac": 110,
                "bac": 500,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "metrics" in data
        assert "health" in data
        assert "spi" in data["metrics"]
        assert "status" in data["health"]

    async def test_negative_pv_rejected(self, client: AsyncClient):
        resp = await client.post(
            "/evm/calculate",
            json={
                "pv": -1,
                "ev": 100,
                "ac": 100,
                "bac": 200,
            },
        )
        assert resp.status_code == 422

    async def test_zero_bac_rejected(self, client: AsyncClient):
        resp = await client.post(
            "/evm/calculate",
            json={
                "pv": 100,
                "ev": 100,
                "ac": 100,
                "bac": 0,
            },
        )
        assert resp.status_code == 422

    async def test_missing_fields_rejected(self, client: AsyncClient):
        resp = await client.post("/evm/calculate", json={"pv": 100})
        assert resp.status_code == 422


# ── POST /evm/health ─────────────────────────────────────────────────────


class TestHealthEndpoint:
    async def test_on_track(self, client: AsyncClient):
        resp = await client.post("/evm/health", json={"spi": 1.0, "cpi": 1.0})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "on_track"
        assert data["reasons"] == []

    async def test_off_track(self, client: AsyncClient):
        resp = await client.post("/evm/health", json={"spi": 0.85, "cpi": 0.85})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "off_track"
        assert len(data["reasons"]) == 2

    async def test_custom_thresholds(self, client: AsyncClient):
        resp = await client.post(
            "/evm/health",
            json={
                "spi": 0.92,
                "cpi": 1.0,
                "thresholds": {
                    "spi_off_track": 0.95,
                    "spi_at_risk": 1.0,
                    "cpi_off_track": 0.95,
                    "cpi_at_risk": 1.0,
                },
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "off_track"

    async def test_missing_spi_rejected(self, client: AsyncClient):
        resp = await client.post("/evm/health", json={"cpi": 1.0})
        assert resp.status_code == 422
