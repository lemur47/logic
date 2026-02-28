"""EVM-specific test data fixtures."""

import pytest

# ── Verification table scenarios (hand-calculated) ────────────────────────


@pytest.fixture
def scenario_on_track():
    """On track: PV=100, EV=100, AC=100, BAC=200."""
    return {
        "input": {"pv": 100, "ev": 100, "ac": 100, "bac": 200},
        "expected": {
            "sv": 0,
            "spi": 1.0,
            "cv": 0,
            "cpi": 1.0,
            "eac": 200,
            "tcpi": 1.0,
            "percent_complete": 50.0,
            "percent_spent": 50.0,
        },
    }


@pytest.fixture
def scenario_behind_over():
    """Behind schedule + over budget: PV=100, EV=80, AC=110, BAC=200."""
    return {
        "input": {"pv": 100, "ev": 80, "ac": 110, "bac": 200},
        "expected": {
            "sv": -20,
            "spi": 0.8,
            "cv": -30,
            "cpi": 0.7273,
            "eac": 275.0,
            "tcpi": 1.3333,
            "percent_complete": 40.0,
            "percent_spent": 55.0,
        },
    }


@pytest.fixture
def scenario_ahead_under():
    """Ahead of schedule + under budget: PV=100, EV=120, AC=90, BAC=200."""
    return {
        "input": {"pv": 100, "ev": 120, "ac": 90, "bac": 200},
        "expected": {
            "sv": 20,
            "spi": 1.2,
            "cv": 30,
            "cpi": 1.3333,
            "eac": 150.01,
            "tcpi": 0.7273,
            "percent_complete": 60.0,
            "percent_spent": 45.0,
        },
    }


@pytest.fixture
def scenario_not_started():
    """Not started: PV=100, EV=0, AC=0, BAC=200."""
    return {
        "input": {"pv": 100, "ev": 0, "ac": 0, "bac": 200},
        "expected": {
            "sv": -100,
            "spi": 0.0,
            "cv": 0,
            "cpi": float("inf"),
            "percent_complete": 0.0,
            "percent_spent": 0.0,
        },
    }


@pytest.fixture
def scenario_all_done():
    """All done, on budget: PV=200, EV=200, AC=200, BAC=200."""
    return {
        "input": {"pv": 200, "ev": 200, "ac": 200, "bac": 200},
        "expected": {
            "sv": 0,
            "spi": 1.0,
            "cv": 0,
            "cpi": 1.0,
            "eac": 200,
            "percent_complete": 100.0,
            "percent_spent": 100.0,
        },
    }


# ── Baseline fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def baseline_payload():
    """Valid baseline creation payload for API tests."""
    return {
        "name": "Test Project",
        "description": "A test project baseline",
        "work_packages": [
            {"name": "Design", "planned_value": 3000},
            {"name": "Build", "planned_value": 5000},
            {"name": "Test", "planned_value": 2000},
        ],
    }


@pytest.fixture
def evaluate_payload():
    """Valid evaluate payload for API tests."""
    return {
        "percent_planned": 50.0,
        "actual_completions": [
            {"name": "Design", "percent_complete": 100.0},
            {"name": "Build", "percent_complete": 40.0},
            {"name": "Test", "percent_complete": 0.0},
        ],
        "actual_cost": 5500,
    }
