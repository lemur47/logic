"""Tests for POST /tco/calculate endpoint."""

from httpx import AsyncClient


async def test_calculate_basic(client: AsyncClient, basic_input):
    resp = await client.post("/tco/calculate", json=basic_input)
    assert resp.status_code == 200
    data = resp.json()
    assert data["input"]["initial_price"] == basic_input["initial_price"]
    assert "result" in data
    assert data["result"]["total_cost"] == 100000


async def test_calculate_full(client: AsyncClient, full_input):
    resp = await client.post("/tco/calculate", json=full_input)
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["total_cost"] > 0
    assert result["npv_tco"] > 0


async def test_calculate_returns_all_fields(client: AsyncClient, basic_input):
    resp = await client.post("/tco/calculate", json=basic_input)
    result = resp.json()["result"]
    expected_keys = {
        "total_cost",
        "annual_cost",
        "monthly_cost",
        "cost_per_day",
        "npv_tco",
        "npv_annual",
    }
    assert expected_keys == set(result.keys())


async def test_calculate_missing_required_fields(client: AsyncClient):
    resp = await client.post("/tco/calculate", json={})
    assert resp.status_code == 422


async def test_calculate_zero_price_rejected(client: AsyncClient):
    resp = await client.post("/tco/calculate", json={"initial_price": 0, "useful_life_years": 5})
    assert resp.status_code == 422


async def test_calculate_negative_price_rejected(client: AsyncClient):
    resp = await client.post("/tco/calculate", json={"initial_price": -1, "useful_life_years": 5})
    assert resp.status_code == 422


async def test_calculate_zero_years_rejected(client: AsyncClient):
    resp = await client.post("/tco/calculate", json={"initial_price": 100, "useful_life_years": 0})
    assert resp.status_code == 422
