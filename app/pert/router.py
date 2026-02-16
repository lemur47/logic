"""
PERT API Router.

All PERT endpoints are defined here and mounted to /pert in main.py.
"""

from fastapi import APIRouter, HTTPException

from . import calculate_project, calculate_task
from .core import DEFAULT_TAGS
from .schemas import (
    ProjectEstimation,
    ProjectInput,
    TaskEstimation,
    TaskInput,
)

router = APIRouter()


def _resolve_tags(task_input: TaskInput) -> list | None:
    """Resolve tag names from input to (InsightTag, severity) tuples."""
    if not task_input.tags:
        return None

    resolved = []
    for tag_input in task_input.tags:
        tag = DEFAULT_TAGS.get(tag_input.name)
        if tag is None:
            valid = ", ".join(sorted(DEFAULT_TAGS.keys()))
            raise ValueError(f"Unknown tag '{tag_input.name}'. Valid tags: {valid}")
        resolved.append((tag, tag_input.severity))
    return resolved


@router.post("/task", response_model=TaskEstimation)
async def estimate_task(task_input: TaskInput):
    """Calculate PERT estimate for a single task.

    Optionally apply insight tags to adjust the pessimistic estimate
    based on real-world risk factors.
    """
    try:
        tags = _resolve_tags(task_input)
        result = calculate_task(
            optimistic=task_input.optimistic,
            most_likely=task_input.most_likely,
            pessimistic=task_input.pessimistic,
            tags=tags,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/project", response_model=ProjectEstimation)
async def estimate_project(project_input: ProjectInput):
    """Aggregate PERT estimates across multiple tasks.

    Project-level statistics assume task independence: expected values sum,
    variances sum, and project std_dev is the square root of summed variances.
    """
    try:
        tasks = []
        for task in project_input.tasks:
            task_dict: dict = {
                "name": task.name,
                "optimistic": task.optimistic,
                "most_likely": task.most_likely,
                "pessimistic": task.pessimistic,
            }
            tags = _resolve_tags(task)
            if tags:
                task_dict["tags"] = tags
            tasks.append(task_dict)

        result = calculate_project(tasks)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
