import asyncio

import pytest

from app.scheduler import Scheduler


@pytest.mark.asyncio
async def test_scheduler_concurrency_limit():

    scheduler = Scheduler(
        max_concurrency=2
    )

    running_count = 0
    maximum_running_count = 0

    async def simulated_task():

        nonlocal running_count
        nonlocal maximum_running_count

        async with scheduler.semaphore:

            running_count += 1

            maximum_running_count = max(
                maximum_running_count,
                running_count,
            )

            await asyncio.sleep(0.05)

            running_count -= 1

    tasks = [
        asyncio.create_task(
            simulated_task()
        )
        for _ in range(5)
    ]

    await asyncio.gather(*tasks)

    assert maximum_running_count <= 2