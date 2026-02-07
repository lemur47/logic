"""Tests for POST /tco/compare endpoint."""

from httpx import AsyncClient


async def test_compare_two_options(client: AsyncClient, cheap_option, expensive_option):
    resp = await client.post("/tco/compare", json={"options": [cheap_option, expensive_option]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["best_option"] == "Expensive"
    assert len(data["results"]) == 2


async def test_compare_ranking(client: AsyncClient, cheap_option, expensive_option):
    resp = await client.post("/tco/compare", json={"options": [cheap_option, expensive_option]})
    results = resp.json()["results"]
    assert results[0]["rank"] == 1
    assert results[1]["rank"] == 2
    assert results[0]["annual_cost"] <= results[1]["annual_cost"]


async def test_compare_sorted_by_annual_cost(client: AsyncClient):
    options = [
        {"name": "High", "initial_price": 300000, "useful_life_years": 5},
        {"name": "Low", "initial_price": 50000, "useful_life_years": 5},
        {"name": "Mid", "initial_price": 150000, "useful_life_years": 5},
    ]
    resp = await client.post("/tco/compare", json={"options": options})
    results = resp.json()["results"]
    costs = [r["annual_cost"] for r in results]
    assert costs == sorted(costs)


async def test_compare_single_option_rejected(client: AsyncClient):
    resp = await client.post(
        "/tco/compare",
        json={"options": [{"name": "Solo", "initial_price": 100, "useful_life_years": 5}]},
    )
    assert resp.status_code == 422


async def test_compare_empty_name_rejected(client: AsyncClient):
    resp = await client.post(
        "/tco/compare",
        json={
            "options": [
                {"name": "", "initial_price": 100, "useful_life_years": 5},
                {"name": "B", "initial_price": 200, "useful_life_years": 5},
            ]
        },
    )
    assert resp.status_code == 422


async def test_compare_invalid_option_price_rejected(client: AsyncClient):
    resp = await client.post(
        "/tco/compare",
        json={
            "options": [
                {"name": "A", "initial_price": -1, "useful_life_years": 5},
                {"name": "B", "initial_price": 200, "useful_life_years": 5},
            ]
        },
    )
    assert resp.status_code == 422
