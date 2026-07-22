"""Tests for POST /pert/task endpoint."""

from httpx import AsyncClient


async def test_task_basic(client: AsyncClient, basic_task_input):
    resp = await client.post("/pert/task", json=basic_task_input)
    assert resp.status_code == 200
    data = resp.json()
    assert data["input"]["optimistic"] == 5
    assert data["input"]["most_likely"] == 10
    assert data["input"]["pessimistic"] == 20
    assert "textbook" in data
    assert data["adjusted"] is None


async def test_task_textbook_fields(client: AsyncClient, basic_task_input):
    resp = await client.post("/pert/task", json=basic_task_input)
    tb = resp.json()["textbook"]
    expected_keys = {"expected", "std_dev", "variance", "range_68", "range_95", "range_99"}
    assert expected_keys == set(tb.keys())


async def test_task_with_tags(client: AsyncClient, task_with_tags):
    resp = await client.post("/pert/task", json=task_with_tags)
    assert resp.status_code == 200
    data = resp.json()
    assert data["adjusted"] is not None
    adj = data["adjusted"]
    assert adj["pessimistic"] > 20
    assert len(adj["tags_applied"]) == 2
    assert adj["combined_multiplier"] > 1.0
    assert "expected" in adj


async def test_task_with_single_tag_default_severity(client: AsyncClient, basic_task_input):
    basic_task_input["tags"] = [{"name": "HIDDEN_DEPENDENCIES"}]
    resp = await client.post("/pert/task", json=basic_task_input)
    assert resp.status_code == 200
    adj = resp.json()["adjusted"]
    assert adj["tags_applied"][0]["severity"] == 0.5


async def test_task_unknown_tag_returns_400(client: AsyncClient, basic_task_input):
    basic_task_input["tags"] = [{"name": "NONEXISTENT_TAG"}]
    resp = await client.post("/pert/task", json=basic_task_input)
    assert resp.status_code == 400
    # Wording now comes from the shared core resolver. It was "Unknown tag" here
    # and "Unknown insight tag" on the MCP surface; one resolver means one message,
    # and MCP's is the shipped one with an installed base, so it wins.
    assert "Unknown insight tag" in resp.json()["detail"]


async def test_task_tag_name_is_case_insensitive(client: AsyncClient, basic_task_input):
    """REST previously rejected lower-case tag names that MCP accepted.

    Both surfaces now share one resolver, so the same input works on both. This is
    a widening — nothing that was accepted before is rejected now.
    """
    basic_task_input["tags"] = [{"name": "hidden_dependencies", "severity": 0.5}]
    resp = await client.post("/pert/task", json=basic_task_input)

    assert resp.status_code == 200
    applied = resp.json()["adjusted"]["tags_applied"]
    assert [t["name"] for t in applied] == ["HIDDEN_DEPENDENCIES"]


async def test_task_tag_mixed_case_matches_too(client: AsyncClient, basic_task_input):
    basic_task_input["tags"] = [{"name": "Hidden_Dependencies", "severity": 0.5}]
    resp = await client.post("/pert/task", json=basic_task_input)
    assert resp.status_code == 200


async def test_task_invalid_ordering_returns_400(client: AsyncClient):
    resp = await client.post(
        "/pert/task",
        json={"optimistic": 20, "most_likely": 10, "pessimistic": 5},
    )
    assert resp.status_code == 400


async def test_task_negative_value_returns_422(client: AsyncClient):
    resp = await client.post(
        "/pert/task",
        json={"optimistic": -1, "most_likely": 10, "pessimistic": 20},
    )
    assert resp.status_code == 422


async def test_task_missing_fields_returns_422(client: AsyncClient):
    resp = await client.post("/pert/task", json={})
    assert resp.status_code == 422


async def test_task_tag_severity_out_of_range_returns_422(client: AsyncClient, basic_task_input):
    basic_task_input["tags"] = [{"name": "FRAGMENTED_COMMUNICATION", "severity": 1.5}]
    resp = await client.post("/pert/task", json=basic_task_input)
    assert resp.status_code == 422
