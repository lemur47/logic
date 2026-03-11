"""PERT-specific test data fixtures."""

import pytest


@pytest.fixture
def basic_task_input():
    """Minimal valid PERT task input."""
    return {
        "optimistic": 5,
        "most_likely": 10,
        "pessimistic": 20,
    }


@pytest.fixture
def task_with_tags():
    """PERT task input with insight tags."""
    return {
        "optimistic": 5,
        "most_likely": 10,
        "pessimistic": 20,
        "tags": [
            {"name": "FRAGMENTED_COMMUNICATION", "severity": 0.8},
            {"name": "MULTIPLE_STAKEHOLDERS", "severity": 0.6},
        ],
    }


@pytest.fixture
def project_input():
    """Multi-task project input."""
    return {
        "tasks": [
            {"name": "Design", "optimistic": 3, "most_likely": 5, "pessimistic": 10},
            {"name": "Build", "optimistic": 10, "most_likely": 15, "pessimistic": 30},
            {"name": "Test", "optimistic": 2, "most_likely": 4, "pessimistic": 8},
        ]
    }


@pytest.fixture
def scenario_payload():
    """Valid PERT scenario creation payload."""
    return {
        "name": "Test Scenario",
        "description": "A test scenario",
        "tags": ["test", "demo"],
        "tasks": [
            {"name": "Design", "optimistic": 3, "most_likely": 5, "pessimistic": 10},
            {"name": "Build", "optimistic": 10, "most_likely": 15, "pessimistic": 30},
            {"name": "Test", "optimistic": 2, "most_likely": 4, "pessimistic": 8},
        ],
    }


@pytest.fixture
def project_input_with_tags():
    """Multi-task project input where some tasks have tags."""
    return {
        "tasks": [
            {"name": "Design", "optimistic": 3, "most_likely": 5, "pessimistic": 10},
            {
                "name": "Build",
                "optimistic": 10,
                "most_likely": 15,
                "pessimistic": 30,
                "tags": [{"name": "FRAGMENTED_COMMUNICATION", "severity": 0.5}],
            },
            {"name": "Test", "optimistic": 2, "most_likely": 4, "pessimistic": 8},
        ]
    }
