
from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, HTTPException

from app.database import initialize_database
from app.dependency_service import would_create_cycle
from app.repository import (
    add_dependency,
    cancel_task,
    create_task,
    delete_task,
    get_dependencies,
    get_task,
    get_task_stats,
    recover_running_tasks,
    task_exists,
)
from app.scheduler import Scheduler
from app.schemas import (
    TaskCreate,
    TaskResponse,
    TaskStatsResponse,
)


scheduler = Scheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):

    # Initialize SQLite database
    initialize_database()

    # Recover tasks that were RUNNING before restart/crash
    recovered = recover_running_tasks()

    if recovered:
        print(
            f"Recovered {recovered} running task(s)"
        )

    # Start background scheduler
    scheduler_task = asyncio.create_task(
        scheduler.start()
    )

    yield

    # Stop scheduler when application shuts down
    await scheduler.stop()

    scheduler_task.cancel()

    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Task Runner",
    description=(
        "A small task execution service with dependencies, "
        "retries, and concurrency control."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

@app.get(
    "/stats",
    response_model=TaskStatsResponse,
)
async def get_stats():
    return get_task_stats()
    
@app.get("/")
async def root():
    return {
        "service": "task-runner",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
    }


@app.post(
    "/tasks",
    response_model=TaskResponse,
)
async def submit_task(task: TaskCreate):

    # Check whether all dependencies exist
    for dependency_id in task.dependencies:

        if not task_exists(dependency_id):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Dependency task not found: "
                    f"{dependency_id}"
                ),
            )

    # Create the task first so we have its ID
    task_id = create_task(
        name=task.name,
        max_retries=task.max_retries,
        failure_probability=task.failure_probability,
        duration_min=task.duration_min,
        duration_max=task.duration_max,
        timeout=task.timeout,
    )

    # Check for circular dependencies
    for dependency_id in task.dependencies:

        if would_create_cycle(
            task_id,
            dependency_id,
        ):
            # Remove the temporary task because
            # submission failed.
            delete_task(task_id)

            raise HTTPException(
                status_code=400,
                detail="Circular dependency detected",
            )

    # Store dependencies
    for dependency_id in task.dependencies:
        add_dependency(
            task_id=task_id,
            depends_on_task_id=dependency_id,
        )

    return TaskResponse(
        id=task_id,
        name=task.name,
        status="waiting",
        attempts=0,
        max_retries=task.max_retries,
        dependencies=task.dependencies,
    )


@app.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
)
async def get_task_status(task_id: str):

    task = get_task(task_id)

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    dependencies = get_dependencies(task_id)

    return TaskResponse(
        id=task["id"],
        name=task["name"],
        status=task["status"],
        attempts=task["attempts"],
        max_retries=task["max_retries"],
        dependencies=dependencies,
    )


@app.post("/tasks/{task_id}/cancel")
def cancel_task_endpoint(task_id: str):

    task = get_task(task_id)

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    cancelled = cancel_task(task_id)

    if not cancelled:
        raise HTTPException(
            status_code=409,
            detail=(
                "Task cannot be cancelled because "
                "it is already completed or blocked"
            ),
        )

    return {
        "id": task_id,
        "status": "cancelled",
    }
