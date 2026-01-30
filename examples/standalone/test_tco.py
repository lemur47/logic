# test_tco.py
import pytest
import pandas as pd  # Need for isinstance check
from tco import calculate_tco, compare_tco, calculate_breakeven_point


def test_calculate_tco():
    """Test calculate_tco with only initial price and useful life."""
    result = calculate_tco(initial_price=100000, useful_life_years=5)

    assert result["total_cost"] == 100000
    assert result["annual_cost"] == 20000
    assert result["monthly_cost"] == 1666.67  # Exact match expectrred
    assert result["cost_per_day"] == 54.79  # Exact match expected
    assert result["npv_tco"] == 100000.0
    assert result["npv_annual"] == 20000.0


def test_compare_tco():
    """Test compare_tco with 2 simple options."""
    # Step 1: Prepare test data
    options = [
        {
            "name": "Premium",
            "initial_price": 450000,
            "useful_life_years": 12,
            "residual_value": 90000,
        },
        {"name": "Budget", "initial_price": 50000, "useful_life_years": 3},
    ]

    # Step 2: Call the function
    result = compare_tco(options)

    # Step 3: Verify it returns a DataFrame
    assert isinstance(result, pd.DataFrame)

    # Step 4: Verify it has 2 rows
    assert len(result) == 2

    # Step 5: Verify required colums exist
    assert "option" in result.columns
    assert "annual_cost" in result.columns
    assert "monthly_cost" in result.columns

    # Step 6: Verify it's sorted by annual_cost (cheapest first)
    assert result.iloc[0]["annual_cost"] <= result.iloc[1]["annual_cost"]

    # Step 7: Verify the option names are present
    option_names = result["option"].tolist()
    assert "Premium" in option_names
    assert "Budget" in option_names


def test_calculate_breakeven_point():
    """Test calculate_breakeven_point with simple scenario."""
    # Option A: Higher upfront, lower annual cost
    option_a = {
        "initial_price": 110000,
        "useful_life_years": 5,
        "annual_operating_cost": 5000,
    }

    # Option B: Lower upfront, higher annual cost
    option_b = {
        "initial_price": 100000,
        "useful_life_years": 5,
        "annual_operating_cost": 15000,
    }

    # Calculate break-even
    result = calculate_breakeven_point(option_a, option_b)

    # Verify it returns a number (not None)
    assert result is not None

    # Verify it's the correct break-even time
    #
    # Option A TCO per year:
    # (110,000 + 5,000*5) / 5 = 135,000 / 5 = 27,000/year
    #
    # Option B TCO per year:
    # (100,000 + 15,000*5) / 5 = 175,000 / 5 = 35,000/year
    #
    # Annual savings: 35,000 - 27,000 = 8,000
    # Extra upfront: 110,000 - 100,000 = 10,000
    # Break-even: 10,000 / 8,000 = 1.25 years
    assert result == 1.25
