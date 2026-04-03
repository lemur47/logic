"""
Monte Carlo router integration tests.

Covers: stateless simulation endpoint, scenario CRUD (create, list, get,
update, delete), stats endpoint, and smart resimulation on PATCH.
"""

import pytest
from httpx import AsyncClient

# =============================================================================
# Stateless Simulation
# =============================================================================


class TestSimulateEndpoint:
    async def test_basic_simulation(self, client: AsyncClient):
        resp = await client.post(
            "/montecarlo/simulate",
            json={
                "tasks": [
                    {"name": "A", "optimistic": 2, "most_likely": 5, "pessimistic": 10},
                    {"name": "B", "optimistic": 3, "most_likely": 6, "pessimistic": 12},
                ],
                "config": {"num_simulations": 1000, "seed": 42},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["n_simulations"] == 1000
        assert "P50" in data["percentiles"]
        assert "P75" in data["percentiles"]
        assert "P85" in data["percentiles"]
        assert "P95" in data["percentiles"]

    async def test_simulation_with_dependencies(self, client: AsyncClient):
        resp = await client.post(
            "/montecarlo/simulate",
            json={
                "tasks": [
                    {"name": "A", "optimistic": 2, "most_likely": 4, "pessimistic": 6},
                    {"name": "B", "optimistic": 1, "most_likely": 3, "pessimistic": 8},
                    {
                        "name": "C",
                        "optimistic": 3,
                        "most_likely": 5,
                        "pessimistic": 9,
                        "depends_on": ["A", "B"],
                    },
                ],
                "config": {"num_simulations": 1000, "seed": 42},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "C" in data["critical_path_frequency"]

    async def test_simulation_default_config(self, client: AsyncClient):
        """Config should default to 10,000 simulations."""
        resp = await client.post(
            "/montecarlo/simulate",
            json={
                "tasks": [
                    {"name": "A", "optimistic": 2, "most_likely": 5, "pessimistic": 10},
                ],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["n_simulations"] == 10_000

    async def test_simulation_histogram(self, client: AsyncClient):
        resp = await client.post(
            "/montecarlo/simulate",
            json={
                "tasks": [
                    {"name": "A", "optimistic": 2, "most_likely": 5, "pessimistic": 10},
                ],
                "config": {"num_simulations": 5000, "seed": 42},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["histogram"]["counts"]) == 50
        assert sum(data["histogram"]["counts"]) == 5000

    async def test_simulation_statistics(self, client: AsyncClient):
        resp = await client.post(
            "/montecarlo/simulate",
            json={
                "tasks": [
                    {"name": "A", "optimistic": 5, "most_likely": 5, "pessimistic": 5},
                ],
                "config": {"num_simulations": 100, "seed": 42},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mean"] == pytest.approx(5.0)
        assert data["std_dev"] == pytest.approx(0.0)
        assert data["min_duration"] == pytest.approx(5.0)
        assert data["max_duration"] == pytest.approx(5.0)

    async def test_simulation_invalid_task_order(self, client: AsyncClient):
        """Optimistic > most_likely should return 400."""
        resp = await client.post(
            "/montecarlo/simulate",
            json={
                "tasks": [
                    {"name": "A", "optimistic": 10, "most_likely": 5, "pessimistic": 3},
                ],
                "config": {"num_simulations": 100},
            },
        )
        assert resp.status_code == 400

    async def test_simulation_empty_tasks(self, client: AsyncClient):
        resp = await client.post(
            "/montecarlo/simulate",
            json={"tasks": []},
        )
        assert resp.status_code == 422

    async def test_simulation_circular_dependency(self, client: AsyncClient):
        resp = await client.post(
            "/montecarlo/simulate",
            json={
                "tasks": [
                    {
                        "name": "A",
                        "optimistic": 1,
                        "most_likely": 2,
                        "pessimistic": 3,
                        "depends_on": ["B"],
                    },
                    {
                        "name": "B",
                        "optimistic": 1,
                        "most_likely": 2,
                        "pessimistic": 3,
                        "depends_on": ["A"],
                    },
                ],
                "config": {"num_simulations": 100},
            },
        )
        assert resp.status_code == 400
        assert "Circular" in resp.json()["detail"]

    async def test_simulation_missing_dependency(self, client: AsyncClient):
        resp = await client.post(
            "/montecarlo/simulate",
            json={
                "tasks": [
                    {
                        "name": "A",
                        "optimistic": 1,
                        "most_likely": 2,
                        "pessimistic": 3,
                        "depends_on": ["X"],
                    },
                ],
                "config": {"num_simulations": 100},
            },
        )
        assert resp.status_code == 400
        assert "unknown task" in resp.json()["detail"]


# =============================================================================
# Target Probability
# =============================================================================


class TestSimulateTargetEndpoint:
    async def test_target_probability(self, client: AsyncClient):
        resp = await client.post(
            "/montecarlo/simulate/target",
            json={
                "input_data": {
                    "tasks": [
                        {"name": "A", "optimistic": 2, "most_likely": 5, "pessimistic": 10},
                    ],
                    "config": {"num_simulations": 5000, "seed": 42},
                },
                "target": {"target_duration": 100.0},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["probability"] == pytest.approx(1.0)

    async def test_target_impossible(self, client: AsyncClient):
        resp = await client.post(
            "/montecarlo/simulate/target",
            json={
                "input_data": {
                    "tasks": [
                        {"name": "A", "optimistic": 5, "most_likely": 8, "pessimistic": 15},
                    ],
                    "config": {"num_simulations": 5000, "seed": 42},
                },
                "target": {"target_duration": 1.0},
            },
        )
        assert resp.status_code == 200
        assert resp.json()["probability"] == pytest.approx(0.0)


# =============================================================================
# Scenario CRUD
# =============================================================================

SAMPLE_TASKS = [
    {"name": "Design", "optimistic": 3, "most_likely": 5, "pessimistic": 10},
    {
        "name": "Build",
        "optimistic": 8,
        "most_likely": 14,
        "pessimistic": 25,
        "depends_on": ["Design"],
    },
]


class TestScenarioCrud:
    async def _create_scenario(self, client: AsyncClient, name: str = "Test Project") -> int:
        resp = await client.post(
            "/montecarlo/scenarios",
            json={
                "name": name,
                "tasks": SAMPLE_TASKS,
                "num_simulations": 1000,
                "seed": 42,
            },
        )
        assert resp.status_code == 201
        return resp.json()["id"]

    async def test_create_scenario(self, client: AsyncClient):
        resp = await client.post(
            "/montecarlo/scenarios",
            json={
                "name": "Sprint 6 Schedule",
                "description": "Monte Carlo simulation for Sprint 6",
                "tasks": SAMPLE_TASKS,
                "num_simulations": 1000,
                "seed": 42,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Sprint 6 Schedule"
        assert data["num_simulations"] == 1000
        assert "P50" in data["percentiles"]
        assert len(data["tasks"]) == 2
        assert data["mean_duration"] > 0
        assert data["std_dev_duration"] >= 0

    async def test_create_scenario_default_simulations(self, client: AsyncClient):
        resp = await client.post(
            "/montecarlo/scenarios",
            json={
                "name": "Default Config",
                "tasks": SAMPLE_TASKS,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["num_simulations"] == 10_000

    async def test_get_scenario(self, client: AsyncClient):
        scenario_id = await self._create_scenario(client)
        resp = await client.get(f"/montecarlo/scenarios/{scenario_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == scenario_id
        assert data["name"] == "Test Project"

    async def test_get_scenario_not_found(self, client: AsyncClient):
        resp = await client.get("/montecarlo/scenarios/9999")
        assert resp.status_code == 404

    async def test_list_scenarios(self, client: AsyncClient):
        await self._create_scenario(client, "Project A")
        await self._create_scenario(client, "Project B")
        resp = await client.get("/montecarlo/scenarios")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_scenarios_pagination(self, client: AsyncClient):
        for i in range(3):
            await self._create_scenario(client, f"Project {i}")
        resp = await client.get("/montecarlo/scenarios?page=1&per_page=2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["per_page"] == 2

    async def test_list_scenarios_search(self, client: AsyncClient):
        await self._create_scenario(client, "Alpha Sprint")
        await self._create_scenario(client, "Beta Release")
        resp = await client.get("/montecarlo/scenarios?search=Alpha")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Alpha Sprint"

    async def test_delete_scenario(self, client: AsyncClient):
        scenario_id = await self._create_scenario(client)
        resp = await client.delete(f"/montecarlo/scenarios/{scenario_id}")
        assert resp.status_code == 204

        resp = await client.get(f"/montecarlo/scenarios/{scenario_id}")
        assert resp.status_code == 404

    async def test_delete_scenario_not_found(self, client: AsyncClient):
        resp = await client.delete("/montecarlo/scenarios/9999")
        assert resp.status_code == 404


# =============================================================================
# Scenario Update (PATCH)
# =============================================================================


class TestScenarioUpdate:
    async def _create_scenario(self, client: AsyncClient) -> dict:
        resp = await client.post(
            "/montecarlo/scenarios",
            json={
                "name": "Original",
                "tasks": SAMPLE_TASKS,
                "num_simulations": 1000,
                "seed": 42,
            },
        )
        return resp.json()

    async def test_update_metadata_only(self, client: AsyncClient):
        """Metadata-only update should NOT resimulate (same percentiles)."""
        original = await self._create_scenario(client)
        resp = await client.patch(
            f"/montecarlo/scenarios/{original['id']}",
            json={"name": "Renamed"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Renamed"
        # Percentiles should remain identical (no resimulation)
        assert data["percentiles"] == original["percentiles"]

    async def test_update_tasks_triggers_resimulation(self, client: AsyncClient):
        """Changing tasks should trigger resimulation."""
        original = await self._create_scenario(client)
        new_tasks = [
            {"name": "Quick Task", "optimistic": 1, "most_likely": 2, "pessimistic": 3},
        ]
        resp = await client.patch(
            f"/montecarlo/scenarios/{original['id']}",
            json={"tasks": new_tasks},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["tasks"]) == 1
        # Percentiles should differ (different tasks)
        assert data["percentiles"]["P50"] != original["percentiles"]["P50"]

    async def test_update_num_simulations_triggers_resimulation(self, client: AsyncClient):
        """Changing num_simulations should trigger resimulation."""
        original = await self._create_scenario(client)
        resp = await client.patch(
            f"/montecarlo/scenarios/{original['id']}",
            json={"num_simulations": 5000},
        )
        assert resp.status_code == 200
        assert resp.json()["num_simulations"] == 5000

    async def test_update_seed_triggers_resimulation(self, client: AsyncClient):
        """Changing seed should trigger resimulation."""
        original = await self._create_scenario(client)
        resp = await client.patch(
            f"/montecarlo/scenarios/{original['id']}",
            json={"seed": 99},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["seed"] == 99

    async def test_update_not_found(self, client: AsyncClient):
        resp = await client.patch(
            "/montecarlo/scenarios/9999",
            json={"name": "Ghost"},
        )
        assert resp.status_code == 404

    async def test_update_description(self, client: AsyncClient):
        original = await self._create_scenario(client)
        resp = await client.patch(
            f"/montecarlo/scenarios/{original['id']}",
            json={"description": "Updated description"},
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated description"


# =============================================================================
# Stats Endpoint
# =============================================================================


class TestStatsEndpoint:
    async def test_stats_empty(self, client: AsyncClient):
        resp = await client.get("/montecarlo/scenarios/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_scenarios"] == 0

    async def test_stats_with_scenarios(self, client: AsyncClient):
        for name in ["A", "B", "C"]:
            await client.post(
                "/montecarlo/scenarios",
                json={
                    "name": name,
                    "tasks": SAMPLE_TASKS,
                    "num_simulations": 1000,
                    "seed": 42,
                },
            )
        resp = await client.get("/montecarlo/scenarios/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_scenarios"] == 3
        assert data["avg_mean_duration"] > 0
        assert data["min_mean_duration"] > 0
        assert data["max_mean_duration"] > 0


# =============================================================================
# Response Structure Validation
# =============================================================================


class TestResponseStructure:
    async def test_scenario_response_has_all_fields(self, client: AsyncClient):
        resp = await client.post(
            "/montecarlo/scenarios",
            json={
                "name": "Full Check",
                "description": "All fields present",
                "tasks": SAMPLE_TASKS,
                "num_simulations": 1000,
                "seed": 42,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        required_fields = [
            "id",
            "name",
            "description",
            "tasks",
            "num_simulations",
            "seed",
            "percentiles",
            "histogram",
            "critical_path_frequency",
            "mean_duration",
            "std_dev_duration",
            "min_duration",
            "max_duration",
            "created_at",
            "updated_at",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    async def test_simulate_response_has_all_fields(self, client: AsyncClient):
        resp = await client.post(
            "/montecarlo/simulate",
            json={
                "tasks": [
                    {"name": "A", "optimistic": 2, "most_likely": 5, "pessimistic": 10},
                ],
                "config": {"num_simulations": 100, "seed": 42},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        required_fields = [
            "n_simulations",
            "percentiles",
            "histogram",
            "critical_path_frequency",
            "mean",
            "std_dev",
            "min_duration",
            "max_duration",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
