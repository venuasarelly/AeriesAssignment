import asyncio

from app.config import (
    MAX_CONCURRENCY,
    SCHEDULER_INTERVAL,
)
from app.repository import (
    get_ready_tasks,
    handle_task_failure,
    increment_attempts,
    mark_blocked_tasks,
    mark_task_running,
    mark_task_succeeded,
)
from app.runner import run_task


class Scheduler:

    def __init__(
        self,
        max_concurrency: int = MAX_CONCURRENCY,
    ):
        self.max_concurrency = max_concurrency

        self.semaphore = asyncio.Semaphore(
            max_concurrency
        )

        self.running_tasks: set[asyncio.Task] = set()

        self._stop_event = asyncio.Event()

    async def start(self):

        print(
            f"Scheduler started "
            f"with concurrency={self.max_concurrency}"
        )

        while not self._stop_event.is_set():

            await self.schedule_ready_tasks()

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=SCHEDULER_INTERVAL,
                )
            except asyncio.TimeoutError:
                pass

    async def stop(self):

        print("Stopping scheduler...")

        self._stop_event.set()

        if self.running_tasks:

            await asyncio.gather(
                *self.running_tasks,
                return_exceptions=True,
            )

        print("Scheduler stopped")

    async def schedule_ready_tasks(self):
        mark_blocked_tasks()
        ready_tasks = get_ready_tasks()

        for task in ready_tasks:

            if self.semaphore.locked():
                break

            acquired = await self.semaphore.acquire()

            if not acquired:
                break

            claimed = mark_task_running(
                task["id"]
            )

            if not claimed:
                self.semaphore.release()
                continue

            increment_attempts(
               task["id"]
            )    

            execution = asyncio.create_task(
                self._execute(task)
            )

            self.running_tasks.add(execution)

            execution.add_done_callback(
                self._task_finished
            )

async def _execute(self, task):
    try:
        succeeded = await run_task(task)

        if succeeded:
            mark_task_succeeded(task["id"])
        else:
            handle_task_failure(task["id"])

    except Exception as error:
        print(
            f"Unexpected error while running "
            f"task {task['id']}: {error}"
        )

    finally:
        self.semaphore.release()