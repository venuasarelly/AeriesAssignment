from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    WAITING = "waiting"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


@dataclass
class Task:
    id: str
    name: str
    status: TaskStatus
    attempts: int
    max_retries: int
    failure_probability: float
    duration_min: float
    duration_max: float
    timeout: float | None
    created_at: datetime
    updated_at: datetime