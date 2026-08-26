"""Tests for PERT Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from app.common.limits import MAX_LIST_ITEMS, MAX_NAME_LENGTH
from app.pert.schemas import (
    ProjectInput,
    ProjectTaskInput,
    ScenarioCreate,
    ScenarioUpdate,
    TagInput,
    TaskInput,
)

# ── TagInput ────────────────────────────────────────────────────────────────


class TestTagInput:
    def test_valid(self):
        tag = TagInput(name="FRAGMENTED_COMMUNICATION", severity=0.8)
        assert tag.name == "FRAGMENTED_COMMUNICATION"
        assert tag.severity == 0.8

    def test_default_severity(self):
        tag = TagInput(name="FRAGMENTED_COMMUNICATION")
        assert tag.severity == 0.5

    def test_severity_zero(self):
        tag = TagInput(name="TEST", severity=0.0)
        assert tag.severity == 0.0

    def test_severity_one(self):
        tag = TagInput(name="TEST", severity=1.0)
        assert tag.severity == 1.0

    def test_severity_below_zero_rejected(self):
        with pytest.raises(ValidationError):
            TagInput(name="TEST", severity=-0.1)

    def test_severity_above_one_rejected(self):
        with pytest.raises(ValidationError):
            TagInput(name="TEST", severity=1.1)

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            TagInput(name="")


# ── TaskInput ───────────────────────────────────────────────────────────────


class TestTaskInput:
    def test_valid_minimal(self):
        task = TaskInput(optimistic=5, most_likely=10, pessimistic=20)
        assert task.tags is None

    def test_valid_with_tags(self):
        task = TaskInput(
            optimistic=5,
            most_likely=10,
            pessimistic=20,
            tags=[TagInput(name="FRAGMENTED_COMMUNICATION")],
        )
        assert len(task.tags) == 1

    def test_negative_optimistic_rejected(self):
        with pytest.raises(ValidationError):
            TaskInput(optimistic=-1, most_likely=10, pessimistic=20)

    def test_negative_most_likely_rejected(self):
        with pytest.raises(ValidationError):
            TaskInput(optimistic=5, most_likely=-1, pessimistic=20)

    def test_negative_pessimistic_rejected(self):
        with pytest.raises(ValidationError):
            TaskInput(optimistic=5, most_likely=10, pessimistic=-1)

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            TaskInput()

    def test_float_coercion(self):
        task = TaskInput(optimistic=5, most_likely=10, pessimistic=20)
        assert isinstance(task.optimistic, float)


# ── ProjectInput ────────────────────────────────────────────────────────────


class TestProjectInput:
    def test_valid(self):
        project = ProjectInput(
            tasks=[
                ProjectTaskInput(name="A", optimistic=3, most_likely=5, pessimistic=10),
            ]
        )
        assert len(project.tasks) == 1

    def test_empty_tasks_rejected(self):
        with pytest.raises(ValidationError):
            ProjectInput(tasks=[])

    def test_task_requires_name(self):
        with pytest.raises(ValidationError):
            ProjectInput(
                tasks=[
                    {"optimistic": 3, "most_likely": 5, "pessimistic": 10},
                ]
            )

    def test_task_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            ProjectInput(
                tasks=[
                    {"name": "", "optimistic": 3, "most_likely": 5, "pessimistic": 10},
                ]
            )

    def test_task_name_too_long_rejected(self):
        with pytest.raises(ValidationError):
            ProjectInput(
                tasks=[
                    {"name": "x" * 256, "optimistic": 3, "most_likely": 5, "pessimistic": 10},
                ]
            )

    def test_tasks_at_limit_ok(self):
        project = ProjectInput(
            tasks=[
                ProjectTaskInput(name=f"T{i}", optimistic=3, most_likely=5, pessimistic=10)
                for i in range(MAX_LIST_ITEMS)
            ]
        )
        assert len(project.tasks) == MAX_LIST_ITEMS

    def test_tasks_over_limit_rejected(self):
        with pytest.raises(ValidationError):
            ProjectInput(
                tasks=[
                    ProjectTaskInput(name=f"T{i}", optimistic=3, most_likely=5, pessimistic=10)
                    for i in range(MAX_LIST_ITEMS + 1)
                ]
            )


class TestScenarioTagCaps:
    """The scalar-cap sweep capped tag NAMES but not the lists holding them.

    Every sibling list on these models carries MAX_LIST_ITEMS; `tags` carried
    neither that nor the per-item name cap, on both the create and the update
    surface.
    """

    def _scenario(self, **over) -> dict:
        return {
            "name": "S",
            "tasks": [{"name": "A", "optimistic": 1, "most_likely": 2, "pessimistic": 3}],
        } | over

    def test_create_rejects_an_oversized_tag_list(self):
        with pytest.raises(ValidationError):
            ScenarioCreate(**self._scenario(tags=["t"] * (MAX_LIST_ITEMS + 1)))

    def test_create_rejects_an_overlong_tag_name(self):
        with pytest.raises(ValidationError):
            ScenarioCreate(**self._scenario(tags=["t" * (MAX_NAME_LENGTH + 1)]))

    def test_update_rejects_an_oversized_tag_list(self):
        with pytest.raises(ValidationError):
            ScenarioUpdate(tags=["t"] * (MAX_LIST_ITEMS + 1))

    def test_update_rejects_an_overlong_tag_name(self):
        with pytest.raises(ValidationError):
            ScenarioUpdate(tags=["t" * (MAX_NAME_LENGTH + 1)])

    def test_a_realistic_tag_list_is_accepted(self):
        s = ScenarioCreate(**self._scenario(tags=["infra", "q3"]))
        assert s.tags == ["infra", "q3"]
