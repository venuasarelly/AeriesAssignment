from fastapi.testclient import TestClient

from app.main import app
from app.repository import (
    create_task,
    add_dependency,
    get_task,
    mark_blocked_tasks,
    mark_task_failed,
    mark_task_succeeded,
)


client = TestClient(app)


def test_task_is_blocked_when_dependency_fails():
    dependency_id = create_task(
        name="Dependency",
        max_retries=0,
        failure_probability=1,
        duration_min=0.01,
        duration_max=0.01,
        timeout=30,
    )

    task_id = create_task(
        name="Dependent Task",
        max_retries=0,
        failure_probability=0,
        duration_min=0.01,
        duration_max=0.01,
        timeout=30,
    )

    add_dependency(
        task_id,
        dependency_id,
    )

    mark_task_failed(dependency_id)

    blocked_count = mark_blocked_tasks()

    assert blocked_count == 1

    task = get_task(task_id)

    assert task["status"] == "blocked"

def test_blocked_status_propagates_downstream():
    task_a = create_task(
        name="Task A",
        max_retries=0,
        failure_probability=0,
        duration_min=0.01,
        duration_max=0.01,
        timeout=30,
    )

    task_b = create_task(
        name="Task B",
        max_retries=0,
        failure_probability=0,
        duration_min=0.01,
        duration_max=0.01,
        timeout=30,
    )

    task_c = create_task(
        name="Task C",
        max_retries=0,
        failure_probability=0,
        duration_min=0.01,
        duration_max=0.01,
        timeout=30,
    )

    add_dependency(task_b, task_a)
    add_dependency(task_c, task_b)

    # A permanently fails.
    mark_task_failed(task_a)

    # B becomes blocked.
    mark_blocked_tasks()

    assert get_task(task_b)["status"] == "blocked"

    # C depends on B, which is now blocked.
    mark_blocked_tasks()

    assert get_task(task_c)["status"] == "blocked"    