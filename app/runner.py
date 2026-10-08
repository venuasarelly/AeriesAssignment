import asyncio
import random


async def run_task(task) -> bool:
    duration = random.uniform(
        task["duration_min"],
        task["duration_max"],
    )

    print(
        f"Starting task {task['id']} "
        f"({task['name']}) for {duration:.2f}s"
    )

    async def simulate_work():
        await asyncio.sleep(duration)

        should_fail = (
            random.random()
            < task["failure_probability"]
        )

        if should_fail:
            raise RuntimeError("Simulated task failure")

    try:
        if task["timeout"] is not None:
            await asyncio.wait_for(
                simulate_work(),
                timeout=task["timeout"],
            )
        else:
            await simulate_work()

    except asyncio.TimeoutError:
        print(
            f"Task {task['id']} "
            f"({task['name']}) TIMED OUT"
        )
        return False

    except RuntimeError as error:
        print(
            f"Task {task['id']} "
            f"({task['name']}) FAILED: {error}"
        )
        return False

    print(
        f"Task {task['id']} "
        f"({task['name']}) SUCCEEDED"
    )

    return True