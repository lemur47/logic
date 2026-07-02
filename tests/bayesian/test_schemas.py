"""Tests for Bayesian Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from app.bayesian.schemas import (
    BayesianCalculateInput,
    ObservationBatchCreate,
    ObservationInput,
)
from app.common.limits import MAX_LIST_ITEMS

# ── BayesianCalculateInput ────────────────────────────────────────────────


class TestBayesianCalculateInput:
    def test_valid_minimal(self):
        inp = BayesianCalculateInput(observations=[ObservationInput(estimated=5, actual=7)])
        assert inp.prior.mean == 1.0
        assert inp.observation_noise == 0.15

    def test_empty_observations_rejected(self):
        with pytest.raises(ValidationError):
            BayesianCalculateInput(observations=[])

    def test_observations_at_limit_ok(self):
        inp = BayesianCalculateInput(
            observations=[ObservationInput(estimated=5, actual=7) for _ in range(MAX_LIST_ITEMS)]
        )
        assert len(inp.observations) == MAX_LIST_ITEMS

    def test_observations_over_limit_rejected(self):
        with pytest.raises(ValidationError):
            BayesianCalculateInput(
                observations=[
                    ObservationInput(estimated=5, actual=7) for _ in range(MAX_LIST_ITEMS + 1)
                ]
            )


# ── ObservationBatchCreate ────────────────────────────────────────────────


class TestObservationBatchCreate:
    def test_valid(self):
        batch = ObservationBatchCreate(observations=[{"estimated": 5, "actual": 7}])
        assert len(batch.observations) == 1

    def test_empty_rejected(self):
        with pytest.raises(ValidationError):
            ObservationBatchCreate(observations=[])

    def test_over_limit_rejected(self):
        with pytest.raises(ValidationError):
            ObservationBatchCreate(
                observations=[{"estimated": 5, "actual": 7} for _ in range(MAX_LIST_ITEMS + 1)]
            )
