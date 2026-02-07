"""Tests for POST /tco/breakeven endpoint."""

from httpx import AsyncClient


async def test_breakeven_crossover(client: AsyncClient):
    """Option A costs more upfront but less annually — breakeven exists."""
    resp = await client.post(
        "/tco/breakeven",
        json={
            "option_a": {
                "initial_price": 200000,
                "useful_life_years": 10,
                "annual_maintenance": 2000,
            },
            "option_b": {
                "initial_price": 50000,
                "useful_life_years": 10,
                "annual_maintenance": 20000,
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_breakeven"] is True
    assert data["breakeven_years"] > 0


async def test_breakeven_no_crossover(client: AsyncClient):
    """Option A has higher annual cost — annual_savings <= 0, no breakeven."""
    resp = await client.post(
        "/tco/breakeven",
        json={
            "option_a": {
                "initial_price": 50000,
                "useful_life_years": 5,
                "annual_maintenance": 20000,
            },
            "option_b": {
                "initial_price": 100000,
                "useful_life_years": 5,
                "annual_maintenance": 2000,
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_breakeven"] is False
    assert data["breakeven_years"] is None


async def test_breakeven_equal_options(client: AsyncClient):
    """Identical options — no breakeven (annual_savings == 0)."""
    option = {"initial_price": 100000, "useful_life_years": 5}
    resp = await client.post("/tco/breakeven", json={"option_a": option, "option_b": option})
    assert resp.status_code == 200
    assert resp.json()["has_breakeven"] is False


async def test_breakeven_invalid_input(client: AsyncClient):
    resp = await client.post(
        "/tco/breakeven",
        json={
            "option_a": {"initial_price": -1, "useful_life_years": 5},
            "option_b": {"initial_price": 100, "useful_life_years": 5},
        },
    )
    assert resp.status_code == 422
