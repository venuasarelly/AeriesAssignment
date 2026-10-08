import asyncio
import random


async def run_task(task) -> bool:
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

    should_fail = (
        random.random()
        < task["failure_probability"]
    )

    if should_fail:
        print(
            f"Task {task['id']} "
            f"({task['name']}) FAILED"
        )
        return False

    print(
        f"Task {task['id']} "
        f"({task['name']}) SUCCEEDED"
    )

    return True