# test_tco.py
import pytest
from tco import calculate_tco


def test_calculate_tco():
    """Test calculate_tco with only initial price and useful life."""
    result = calculate_tco(initial_price=100000, useful_life_years=5)

    assert result["total_cost"] == 100000
    assert result["annual_cost"] == 20000
    assert result["monthly_cost"] == 1666.67  # Exact match expectrred
    assert result["cost_per_day"] == 54.79  # Exact match expected
    assert result["npv_tco"] == 100000.0
    assert result["npv_annual"] == 20000.0
