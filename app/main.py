from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.database import initialize_database
from app.repository import (
    add_dependency,
    create_task,
    get_dependencies,
    get_task,
    task_exists,
)
from app.schemas import TaskCreate, TaskResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Task Runner",
    description="A small task execution service with dependencies, retries, and concurrency control.",
    version="1.0.0",
    lifespan=lifespan,
)


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
                detail=f"Dependency task not found: {dependency_id}",
            )

    # Create the task
    task_id = create_task(
        name=task.name,
        max_retries=task.max_retries,
        failure_probability=task.failure_probability,
        duration_min=task.duration_min,
        duration_max=task.duration_max,
        timeout=task.timeout,
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