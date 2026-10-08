from app.repository import (
    cancel_task,
    create_task,
    get_task,
)


def test_waiting_task_can_be_cancelled():
    task_id = create_task(
        name="Cancel Me",
        max_retries=0,
        failure_probability=0,
        duration_min=1,
        duration_max=1,
        timeout=30,
    )

    result = cancel_task(task_id)

    assert result is True
    assert get_task(task_id)["status"] == "cancelled"


def test_completed_task_cannot_be_cancelled():
    task_id = create_task(
        name="Completed Task",
        max_retries=0,
        failure_probability=0,
        duration_min=1,
        duration_max=1,
        timeout=30,
    )

    from app.repository import mark_task_succeeded

    # Simulate a running task first.
    from app.repository import mark_task_running

    assert mark_task_running(task_id) is True
    assert mark_task_succeeded(task_id) is True

    result = cancel_task(task_id)

    assert result is False
    assert get_task(task_id)["status"] == "succeeded"

def test_cancelled_dependency_blocks_downstream_task():
    dependency_id = create_task(
        name="Dependency",
        max_retries=0,
        failure_probability=0,
        duration_min=1,
        duration_max=1,
        timeout=30,
    )

    dependent_id = create_task(
        name="Dependent",
        max_retries=0,
        failure_probability=0,
        duration_min=1,
        duration_max=1,
        timeout=30,
    )

    from app.repository import add_dependency

    add_dependency(
        dependent_id,
        dependency_id,
    )

    assert cancel_task(dependency_id) is True

    from app.repository import mark_blocked_tasks

    mark_blocked_tasks()

    assert get_task(dependent_id)["status"] == "blocked"    