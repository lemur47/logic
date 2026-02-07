"""TCO-specific test data fixtures."""

import pytest


@pytest.fixture
def basic_input():
    """Minimal valid TCO input."""
    return {
        "initial_price": 100000,
        "useful_life_years": 5,
    }


@pytest.fixture
def full_input():
    """TCO input with all fields populated."""
    return {
        "initial_price": 450000,
        "useful_life_years": 12,
        "residual_value": 90000,
        "annual_maintenance": 5000,
        "annual_operating_cost": 3000,
        "discount_rate": 0.05,
    }


@pytest.fixture
def cheap_option():
    """Low initial price, high annual cost option (annual=55000)."""
    return {
        "name": "Cheap",
        "initial_price": 50000,
        "useful_life_years": 5,
        "annual_maintenance": 30000,
        "annual_operating_cost": 15000,
    }


@pytest.fixture
def expensive_option():
    """High initial price, low annual cost option (annual=43000)."""
    return {
        "name": "Expensive",
        "initial_price": 200000,
        "useful_life_years": 5,
        "annual_maintenance": 2000,
        "annual_operating_cost": 1000,
    }


@pytest.fixture
def scenario_payload():
    """Valid scenario creation payload."""
    return {
        "name": "Test Scenario",
        "description": "A test scenario",
        "tags": ["test", "demo"],
        "initial_price": 100000,
        "useful_life_years": 5,
        "residual_value": 10000,
        "annual_maintenance": 2000,
        "annual_operating_cost": 1000,
        "discount_rate": 0.03,
    }
