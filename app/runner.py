import asyncio
import random

from app.repository import mark_task_succeeded


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

    await asyncio.sleep(duration)

    mark_task_succeeded(task["id"])

    print(
        f"Completed task {task['id']} "
        f"({task['name']})"
    )