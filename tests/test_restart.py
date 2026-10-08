from app.repository import (
    create_task,
    get_task,
    mark_task_running,
    recover_running_tasks,
)


def test_running_task_is_recovered_to_waiting():
    task_id = create_task(
        name="Running Task",
        max_retries=2,
        failure_probability=0,
        duration_min=1,
        duration_max=1,
        timeout=30,
    )

    assert mark_task_running(task_id) is True

    task_before = get_task(task_id)

    assert task_before["status"] == "running"

    recovered = recover_running_tasks()

    assert recovered == 1

    task_after = get_task(task_id)

    assert task_after["status"] == "waiting"
    assert task_after["attempts"] == 0


def test_completed_tasks_are_not_recovered():
    from app.repository import mark_task_succeeded

    task_id = create_task(
        name="Completed Task",
        max_retries=0,
        failure_probability=0,
        duration_min=1,
        duration_max=1,
        timeout=30,
    )

    assert mark_task_running(task_id) is True
    assert mark_task_succeeded(task_id) is True

    recovered = recover_running_tasks()

    assert recovered == 0

    task = get_task(task_id)

    assert task["status"] == "succeeded"


def test_terminal_states_are_not_recovered():
    from app.repository import (
        cancel_task,
        mark_task_failed,
    )

    # FAILED
    failed_id = create_task(
        name="Failed Task",
        max_retries=0,
        failure_probability=1,
        duration_min=1,
        duration_max=1,
        timeout=30,
    )

    assert mark_task_running(failed_id) is True

    mark_task_failed(failed_id)

    # CANCELLED
    cancelled_id = create_task(
        name="Cancelled Task",
        max_retries=0,
        failure_probability=0,
        duration_min=1,
        duration_max=1,
        timeout=30,
    )

    assert cancel_task(cancelled_id) is True

    recovered = recover_running_tasks()

    assert recovered == 0

    assert get_task(failed_id)["status"] == "failed"
    assert get_task(cancelled_id)["status"] == "cancelled"