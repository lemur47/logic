"""Unit tests for tco/core.py pure calculation functions."""

import pytest
from tco.core import calculate_breakeven, calculate_tco, compare_options

# ── calculate_tco ────────────────────────────────────────────────────────────


class TestCalculateTco:
    def test_basic(self, basic_input):
        result = calculate_tco(**basic_input)
        assert result["total_cost"] == 100000
        assert result["annual_cost"] == 20000
        assert result["monthly_cost"] == pytest.approx(20000 / 12, rel=1e-2)
        assert result["cost_per_day"] == pytest.approx(20000 / 365, rel=1e-2)

    def test_with_residual_value(self):
        result = calculate_tco(initial_price=100000, useful_life_years=5, residual_value=20000)
        assert result["total_cost"] == 80000

    def test_with_annual_costs(self):
        result = calculate_tco(
            initial_price=100000,
            useful_life_years=5,
            annual_maintenance=5000,
            annual_operating_cost=3000,
        )
        total_ops = (5000 + 3000) * 5
        assert result["total_cost"] == 100000 + total_ops

    def test_full_input(self, full_input):
        result = calculate_tco(**full_input)
        expected_ops = (5000 + 3000) * 12
        expected_total = 450000 + expected_ops - 90000
        assert result["total_cost"] == expected_total
        assert result["annual_cost"] == pytest.approx(expected_total / 12, rel=1e-2)

    def test_npv_less_than_simple(self, full_input):
        """NPV-adjusted TCO should differ from simple TCO when discount_rate > 0."""
        result = calculate_tco(**full_input)
        assert result["npv_tco"] != result["total_cost"]

    def test_npv_equals_simple_at_zero_rate(self, basic_input):
        """With discount_rate=0, NPV should equal simple TCO."""
        basic_input["discount_rate"] = 0
        result = calculate_tco(**basic_input)
        assert result["npv_tco"] == result["total_cost"]

    def test_one_year_life(self):
        result = calculate_tco(initial_price=12000, useful_life_years=1)
        assert result["annual_cost"] == 12000
        assert result["monthly_cost"] == 1000

    def test_zero_life_years_raises(self):
        with pytest.raises(ValueError, match="useful_life_years must be positive"):
            calculate_tco(initial_price=100, useful_life_years=0)

    def test_negative_life_years_raises(self):
        with pytest.raises(ValueError, match="useful_life_years must be positive"):
            calculate_tco(initial_price=100, useful_life_years=-1)

    def test_negative_price_raises(self):
        with pytest.raises(ValueError, match="Prices cannot be negative"):
            calculate_tco(initial_price=-1, useful_life_years=5)

    def test_negative_residual_raises(self):
        with pytest.raises(ValueError, match="Prices cannot be negative"):
            calculate_tco(initial_price=100, useful_life_years=5, residual_value=-1)

    def test_negative_maintenance_raises(self):
        with pytest.raises(ValueError, match="Annual costs cannot be negative"):
            calculate_tco(initial_price=100, useful_life_years=5, annual_maintenance=-1)

    def test_negative_operating_cost_raises(self):
        with pytest.raises(ValueError, match="Annual costs cannot be negative"):
            calculate_tco(initial_price=100, useful_life_years=5, annual_operating_cost=-1)


# ── compare_options ──────────────────────────────────────────────────────────


class TestCompareOptions:
    def test_ranks_by_annual_cost(self, cheap_option, expensive_option):
        results = compare_options([cheap_option, expensive_option])
        names = [r["name"] for r in results]
        assert names[0] == "Expensive"
        assert results[0]["rank"] == 1
        assert results[1]["rank"] == 2

    def test_includes_tco_fields(self, cheap_option, expensive_option):
        results = compare_options([cheap_option, expensive_option])
        for r in results:
            assert "total_cost" in r
            assert "annual_cost" in r
            assert "npv_tco" in r
            assert "name" in r

    def test_three_options(self):
        options = [
            {"name": "A", "initial_price": 100000, "useful_life_years": 5},
            {"name": "B", "initial_price": 50000, "useful_life_years": 5},
            {"name": "C", "initial_price": 75000, "useful_life_years": 5},
        ]
        results = compare_options(options)
        assert len(results) == 3
        assert results[0]["name"] == "B"
        assert results[0]["rank"] == 1


# ── calculate_breakeven ─────────────────────────────────────────────────────


class TestCalculateBreakeven:
    def test_returns_years(self):
        """Option A costs more upfront but less annually — breakeven exists."""
        option_a = {
            "initial_price": 200000,
            "useful_life_years": 10,
            "annual_maintenance": 2000,
        }
        option_b = {
            "initial_price": 50000,
            "useful_life_years": 10,
            "annual_maintenance": 20000,
        }
        years = calculate_breakeven(option_a, option_b)
        assert years is not None
        assert years > 0

    def test_no_breakeven_when_a_costs_more(self):
        """When option A has higher annual cost, annual_savings <= 0."""
        option_a = {
            "initial_price": 50000,
            "useful_life_years": 5,
            "annual_maintenance": 20000,
        }
        option_b = {
            "initial_price": 100000,
            "useful_life_years": 5,
            "annual_maintenance": 2000,
        }
        assert calculate_breakeven(option_a, option_b) is None
