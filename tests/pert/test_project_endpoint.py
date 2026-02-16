"""Tests for POST /pert/project endpoint."""

from httpx import AsyncClient


async def test_project_basic(client: AsyncClient, project_input):
    resp = await client.post("/pert/project", json=project_input)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["tasks"]) == 3
    assert data["tasks"][0]["name"] == "Design"
    assert "project" in data
    assert data["adjusted_project"] is None


async def test_project_stats_fields(client: AsyncClient, project_input):
    resp = await client.post("/pert/project", json=project_input)
    proj = resp.json()["project"]
    expected_keys = {"expected", "std_dev", "variance", "range_68", "range_95", "range_99"}
    assert expected_keys == set(proj.keys())


async def test_project_with_tags(client: AsyncClient, project_input_with_tags):
    resp = await client.post("/pert/project", json=project_input_with_tags)
    assert resp.status_code == 200
    data = resp.json()
    assert data["adjusted_project"] is not None
    assert data["adjusted_project"]["expected"] > data["project"]["expected"]


async def test_project_individual_task_results(client: AsyncClient, project_input_with_tags):
    resp = await client.post("/pert/project", json=project_input_with_tags)
    data = resp.json()
    build_task = data["tasks"][1]
    assert build_task["name"] == "Build"
    assert build_task["adjusted"] is not None
    assert build_task["adjusted"]["pessimistic"] > 30


async def test_project_empty_tasks_returns_422(client: AsyncClient):
    resp = await client.post("/pert/project", json={"tasks": []})
    assert resp.status_code == 422


async def test_project_missing_task_name_returns_422(client: AsyncClient):
    resp = await client.post(
        "/pert/project",
        json={"tasks": [{"optimistic": 3, "most_likely": 5, "pessimistic": 10}]},
    )
    assert resp.status_code == 422


async def test_project_invalid_task_ordering_returns_400(client: AsyncClient):
    resp = await client.post(
        "/pert/project",
        json={"tasks": [{"name": "Bad", "optimistic": 20, "most_likely": 10, "pessimistic": 5}]},
    )
    assert resp.status_code == 400


async def test_project_unknown_tag_returns_400(client: AsyncClient):
    resp = await client.post(
        "/pert/project",
        json={
            "tasks": [
                {
                    "name": "Task",
                    "optimistic": 5,
                    "most_likely": 10,
                    "pessimistic": 20,
                    "tags": [{"name": "BOGUS"}],
                }
            ]
        },
    )
    assert resp.status_code == 400
