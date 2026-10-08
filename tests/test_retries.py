import asyncio

import pytest

from app.database import initialize_database
from app.repository import (
    create_task,
    get_task,
    handle_task_failure,
)


def setup_function():
    initialize_database()


def test_retry_delay_is_scheduled():
    task_id = create_task(
        name="Retry Task",
        max_retries=3,
        failure_probability=1,
        duration_min=0.01,
        duration_max=0.01,
        timeout=30,
    )

    # Simulate first attempt.
    from app.repository import increment_attempts

    increment_attempts(task_id)

    should_retry = handle_task_failure(task_id)

    assert should_retry is True

    task = get_task(task_id)

    assert task["status"] == "waiting"
    assert task["next_run_at"] is not None


def test_task_eventually_fails_after_retries():
    task_id = create_task(
        name="Permanent Failure",
        max_retries=2,
        failure_probability=1,
        duration_min=0.01,
        duration_max=0.01,
        timeout=30,
    )

    from app.repository import increment_attempts

    # Attempt 1
    increment_attempts(task_id)
    assert handle_task_failure(task_id) is True

    # Attempt 2
    increment_attempts(task_id)
    assert handle_task_failure(task_id) is True

    # Attempt 3 - no retries left
    increment_attempts(task_id)
    assert handle_task_failure(task_id) is False

    task = get_task(task_id)

    assert task["status"] == "failed"
    assert task["attempts"] == 3