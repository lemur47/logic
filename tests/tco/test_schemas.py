"""Tests for TCO Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from app.common.limits import MAX_LIST_ITEMS
from app.tco.schemas import CompareRequest, ScenarioCreate, ScenarioUpdate, TCOInput

# ── TCOInput ─────────────────────────────────────────────────────────────────


class TestTCOInput:
    def test_valid_minimal(self):
        inp = TCOInput(initial_price=100, useful_life_years=1)
        assert inp.initial_price == 100
        assert inp.discount_rate == 0.03

    def test_valid_full(self, full_input):
        inp = TCOInput(**full_input)
        assert inp.annual_maintenance == 5000

    def test_initial_price_must_be_positive(self):
        with pytest.raises(ValidationError):
            TCOInput(initial_price=0, useful_life_years=1)

    def test_initial_price_negative_rejected(self):
        with pytest.raises(ValidationError):
            TCOInput(initial_price=-1, useful_life_years=1)

    def test_useful_life_years_zero_rejected(self):
        with pytest.raises(ValidationError):
            TCOInput(initial_price=100, useful_life_years=0)

    def test_useful_life_years_above_100_rejected(self):
        with pytest.raises(ValidationError):
            TCOInput(initial_price=100, useful_life_years=101)

    def test_residual_value_negative_rejected(self):
        with pytest.raises(ValidationError):
            TCOInput(initial_price=100, useful_life_years=5, residual_value=-1)

    def test_discount_rate_above_1_rejected(self):
        with pytest.raises(ValidationError):
            TCOInput(initial_price=100, useful_life_years=5, discount_rate=1.5)

    def test_discount_rate_negative_rejected(self):
        with pytest.raises(ValidationError):
            TCOInput(initial_price=100, useful_life_years=5, discount_rate=-0.01)


# ── CompareRequest ───────────────────────────────────────────────────────────


class TestCompareRequest:
    def test_valid_two_options(self):
        req = CompareRequest(
            options=[
                {"name": "A", "initial_price": 100, "useful_life_years": 5},
                {"name": "B", "initial_price": 200, "useful_life_years": 5},
            ]
        )
        assert len(req.options) == 2

    def test_single_option_rejected(self):
        with pytest.raises(ValidationError):
            CompareRequest(options=[{"name": "A", "initial_price": 100, "useful_life_years": 5}])

    def test_options_at_limit_ok(self):
        req = CompareRequest(
            options=[
                {"name": f"O{i}", "initial_price": 100, "useful_life_years": 5}
                for i in range(MAX_LIST_ITEMS)
            ]
        )
        assert len(req.options) == MAX_LIST_ITEMS

    def test_options_over_limit_rejected(self):
        with pytest.raises(ValidationError):
            CompareRequest(
                options=[
                    {"name": f"O{i}", "initial_price": 100, "useful_life_years": 5}
                    for i in range(MAX_LIST_ITEMS + 1)
                ]
            )

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            CompareRequest(
                options=[
                    {"name": "", "initial_price": 100, "useful_life_years": 5},
                    {"name": "B", "initial_price": 200, "useful_life_years": 5},
                ]
            )


# ── ScenarioCreate ───────────────────────────────────────────────────────────


class TestScenarioCreate:
    def test_valid_minimal(self):
        s = ScenarioCreate(name="Test", initial_price=100, useful_life_years=5)
        assert s.tags == []
        assert s.description is None

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            ScenarioCreate(name="", initial_price=100, useful_life_years=5)

    def test_name_too_long_rejected(self):
        with pytest.raises(ValidationError):
            ScenarioCreate(name="x" * 256, initial_price=100, useful_life_years=5)

    def test_description_too_long_rejected(self):
        with pytest.raises(ValidationError):
            ScenarioCreate(
                name="Test",
                initial_price=100,
                useful_life_years=5,
                description="x" * 1001,
            )


# ── ScenarioUpdate ───────────────────────────────────────────────────────────


class TestScenarioUpdate:
    def test_all_fields_optional(self):
        s = ScenarioUpdate()
        assert s.name is None
        assert s.initial_price is None

    def test_partial_update(self):
        s = ScenarioUpdate(name="Updated")
        assert s.name == "Updated"
        assert s.initial_price is None

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            ScenarioUpdate(name="")
