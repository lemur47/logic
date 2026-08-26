"""Tests for Monte Carlo Pydantic schema validation and DoS guards."""

import pytest
from pydantic import ValidationError

from app.common.limits import MAX_LIST_ITEMS
from app.montecarlo.core import MAX_SIMULATION_CELLS, Task, simulate_schedule
from app.montecarlo.schemas import (
    DriftConfigInput,
    ScenarioCreate,
    ScenarioUpdate,
    SimulateInput,
    TaskInput,
)


def _tasks(n: int) -> list[dict]:
    """n minimal, distinctly-named task payloads."""
    return [
        {"name": f"T{i}", "optimistic": 3, "most_likely": 5, "pessimistic": 10} for i in range(n)
    ]


# ── TaskInput / list caps ─────────────────────────────────────────────────


class TestTaskInput:
    def test_valid_minimal(self):
        t = TaskInput(name="Design", optimistic=3, most_likely=5, pessimistic=10)
        assert t.depends_on == []

    def test_depends_on_over_limit_rejected(self):
        with pytest.raises(ValidationError):
            TaskInput(
                name="Design",
                optimistic=3,
                most_likely=5,
                pessimistic=10,
                depends_on=[f"P{i}" for i in range(MAX_LIST_ITEMS + 1)],
            )


class TestSimulateInputListCaps:
    def test_valid_minimal(self):
        inp = SimulateInput(tasks=_tasks(3))
        assert inp.config.num_simulations == 10_000

    def test_empty_tasks_rejected(self):
        with pytest.raises(ValidationError):
            SimulateInput(tasks=[])

    def test_tasks_over_limit_rejected(self):
        with pytest.raises(ValidationError):
            SimulateInput(tasks=_tasks(MAX_LIST_ITEMS + 1), config={"num_simulations": 100})

    def test_risk_classes_over_limit_rejected(self):
        with pytest.raises(ValidationError):
            DriftConfigInput(risk_classes=[{"name": f"R{i}"} for i in range(MAX_LIST_ITEMS + 1)])


# ── Product cap (n_tasks × num_simulations) at the API boundary ────────────


class TestSimulationCellCap:
    def test_at_limit_ok(self):
        # 10 × 1_000_000 == MAX_SIMULATION_CELLS (boundary is inclusive).
        n = 10
        assert n * 1_000_000 == MAX_SIMULATION_CELLS
        inp = SimulateInput(tasks=_tasks(n), config={"num_simulations": 1_000_000})
        assert len(inp.tasks) == n

    def test_over_limit_rejected(self):
        # 11 × 1_000_000 exceeds the cap.
        with pytest.raises(ValidationError):
            SimulateInput(tasks=_tasks(11), config={"num_simulations": 1_000_000})

    def test_scenario_create_over_limit_rejected(self):
        with pytest.raises(ValidationError):
            ScenarioCreate(name="Big", tasks=_tasks(11), num_simulations=1_000_000)

    def test_scenario_update_both_over_limit_rejected(self):
        with pytest.raises(ValidationError):
            ScenarioUpdate(tasks=_tasks(11), num_simulations=1_000_000)

    def test_scenario_update_tasks_only_not_checked(self):
        # Without num_simulations in the same patch there is nothing to multiply
        # against; the crud layer and core guard bound the mixed case.
        upd = ScenarioUpdate(tasks=_tasks(11))
        assert len(upd.tasks) == 11


# ── Core guard (covers crud-update / MCP / direct-call paths) ──────────────


class TestCoreAllocationGuard:
    def test_over_limit_raises_before_allocation(self):
        # 1 task × 20_000_000 sims would allocate ~1.1 GB; the guard rejects it.
        tasks = [Task(name="A", optimistic=1, most_likely=2, pessimistic=3)]
        with pytest.raises(ValueError, match="exceeds the limit"):
            simulate_schedule(tasks, n_simulations=MAX_SIMULATION_CELLS + 1)


class TestDependencyEdgeBudgetAtTheBoundary:
    """`depends_on` is capped per task but the SUM was never bounded.

    1000 tasks each carrying the permitted 1000 predecessors is a million
    edges, and `_forward_pass` allocates one array row per edge per task. The
    per-task cap alone therefore does not bound the request.
    """

    def _task(self, name: str, deps: list[str]) -> dict:
        return {
            "name": name,
            "optimistic": 1,
            "most_likely": 2,
            "pessimistic": 3,
            "depends_on": deps,
        }

    def test_dense_distinct_graph_is_rejected(self):
        tasks = [self._task("t0", [])] + [
            self._task(f"t{i}", [f"t{j}" for j in range(i)]) for i in range(1, 700)
        ]
        with pytest.raises(ValidationError, match="dependency_edges"):
            SimulateInput(tasks=tasks, config={"num_simulations": 10_000})

    def test_repeated_edges_are_counted_once(self):
        """The core de-duplicates, so the boundary must budget distinct edges.

        Counting repeats here would reject a payload that costs nothing to run.
        """
        tasks = [self._task("t0", [])] + [
            self._task(f"t{i}", ["t0"] * 1_000) for i in range(1, 200)
        ]
        SimulateInput(tasks=tasks, config={"num_simulations": 10_000})  # must not raise

    def test_a_realistic_chain_is_still_accepted(self):
        tasks = [self._task("t0", [])] + [
            self._task(f"t{i}", [f"t{i - 1}"]) for i in range(1, 1_000)
        ]
        SimulateInput(tasks=tasks, config={"num_simulations": 10_000})  # must not raise
