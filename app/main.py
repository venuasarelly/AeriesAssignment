from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import initialize_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()

    yield


app = FastAPI(
    title="Task Runner",
    description=(
        "A small task execution service with dependencies, "
        "retries, and concurrency control."
    ),
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