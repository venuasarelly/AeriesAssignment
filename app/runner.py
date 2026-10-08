import asyncio
import random

from app.repository import (
    mark_task_failed,
    mark_task_succeeded,
)


async def run_task(task) -> None:

    duration = random.uniform(
        task["duration_min"],
        task["duration_max"],
    )

    print(
        f"Starting task {task['id']} "
        f"({task['name']}) "
        f"for {duration:.2f}s"
    )

    # Simulate actual work
    await asyncio.sleep(duration)

    # Simulate random failure
    should_fail = (
        random.random()
        < task["failure_probability"]
    )

    if should_fail:

        mark_task_failed(
            task["id"]
        )

        print(
            f"Task {task['id']} "
            f"({task['name']}) FAILED"
        )

        return

    mark_task_succeeded(
        task["id"]
    )

    print(
        f"Task {task['id']} "
        f"({task['name']}) SUCCEEDED"
    )