from fastapi import FastAPI
from fastapi import FastAPI

app = FastAPI(
    title="Task Runner",
    description="A small task execution service with dependencies, retries, and concurrency control.",
    version="1.0.0",
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