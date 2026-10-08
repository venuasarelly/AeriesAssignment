
import pytest

from app.database import initialize_database
from app.repository import create_task, get_task
from app.runner import run_task


def setup_function():
    initialize_database()


@pytest.mark.asyncio
async def test_task_always_succeeds():
    task_id = create_task(
        name="Success Task",
        max_retries=0,
        failure_probability=0,
        duration_min=0.01,
        duration_max=0.01,
        timeout=30,
    )

    task = get_task(task_id)

    result = await run_task(task)

    assert result is True


@pytest.mark.asyncio
async def test_task_always_fails():
    task_id = create_task(
        name="Failure Task",
        max_retries=0,
        failure_probability=1,
        duration_min=0.01,
        duration_max=0.01,
        timeout=30,
    )

    task = get_task(task_id)

    result = await run_task(task)

    assert result is False
