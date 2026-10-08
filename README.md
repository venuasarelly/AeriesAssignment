# Task Runner Service

A small asynchronous task execution service built with **Python, FastAPI, SQLite, and asyncio**.

The service supports:

- Task dependencies
- Circular dependency detection
- Configurable concurrency
- FIFO scheduling
- Automatic retries with exponential backoff
- Failed dependency propagation
- Task cancellation
- Restart recovery
- Task execution timeouts
- Task statistics
- Persistent task state using SQLite

---

## Scenario

This project models a **Document Processing Pipeline**.

A document can move through multiple processing stages:

```text
Upload Document
       ↓
Extract Text
       ↓
Generate Summary
       ↓
Send Report
```

A task only starts when all of its dependencies have successfully completed.

For example:

```text
Upload Document
       ↓
Extract Text
       ↓
Generate Summary
       ↓
Send Report
```

If `Extract Text` permanently fails:

```text
Upload Document
       ↓
Extract Text → FAILED
       ↓
Generate Summary → BLOCKED
       ↓
Send Report → BLOCKED
```

This prevents downstream tasks from waiting indefinitely for an impossible dependency.

---

# Features

## 1. Task Dependencies

Tasks can depend on one or more other tasks.

A task is eligible to run only when **all dependencies are `succeeded`**.

Example:

```text
Task A
 ├── Task B
 └── Task C
       ↓
     Task D
```

`Task D` will only run after both `Task B` and `Task C` succeed.

---

## 2. Circular Dependency Detection

Circular dependencies are rejected when a task is submitted.

Example:

```text
Task A → Task B
Task B → Task C
Task C → Task A
```

This would create a cycle, so the submission is rejected.

The implementation uses depth-first graph traversal to detect whether adding a dependency would create a cycle.

---

## 3. Concurrency Control

The scheduler supports a configurable maximum number of simultaneously running tasks.

The default limit is:

```text
MAX_CONCURRENCY=3
```

For example, with:

```text
MAX_CONCURRENCY=3
```

the scheduler will never intentionally execute more than three tasks concurrently.

The scheduler uses an `asyncio.Semaphore` together with an atomic database state transition:

```text
WAITING → RUNNING
```

This prevents two scheduler iterations from claiming the same task.

---

## 4. FIFO Scheduling

Ready tasks are selected in creation order.

Among tasks that are currently eligible to run:

```text
oldest ready task
        ↓
next ready task
        ↓
next ready task
```

This keeps scheduling deterministic and simple.

A tradeoff is that FIFO does not prioritize short tasks over long tasks.

---

## 5. Automatic Retries

Failed tasks can be retried automatically.

The `max_retries` configuration determines how many retries are allowed after the initial attempt.

For example:

```text
max_retries = 3
```

means:

```text
Attempt 1 → failure
      ↓
Retry after 1 second

Attempt 2 → failure
      ↓
Retry after 2 seconds

Attempt 3 → failure
      ↓
Retry after 4 seconds

Attempt 4 → permanent failure
```

The retry delay follows exponential backoff:

```text
1s → 2s → 4s → ...
```

Attempts are persisted in SQLite.

---

## 6. Failed Dependency Blocking

If a dependency permanently enters one of these states:

```text
FAILED
BLOCKED
CANCELLED
```

the dependent task becomes:

```text
BLOCKED
```

This behavior propagates through the dependency graph.

Example:

```text
A → FAILED

B depends on A
B → BLOCKED

C depends on B
C → BLOCKED
```

No downstream task waits forever.

---

## 7. Task Cancellation

Tasks in `WAITING` or `RUNNING` state can be cancelled.

Cancellation is cooperative.

If a running task is cancelled:

```text
RUNNING
   ↓
CANCELLED
```

The simulated coroutine may continue until its execution finishes, but its completion result cannot overwrite the persisted `CANCELLED` state.

This prevents a cancelled task from later becoming `SUCCEEDED`.

Dependents of a cancelled task become `BLOCKED`.

---

## 8. Task Timeout

Each task can have a configurable timeout.

For example:

```text
duration = 10 seconds
timeout  = 3 seconds
```

The task is stopped after the timeout:

```text
RUNNING
   ↓
TIMEOUT
   ↓
FAILED ATTEMPT
   ↓
RETRY
```

Timeouts are implemented using Python's `asyncio.wait_for()`.

This is the additional improvement implemented for this project.

---

## 9. Restart Recovery

Task state is persisted in SQLite.

On service startup:

```text
SUCCEEDED → remains SUCCEEDED
FAILED    → remains FAILED
BLOCKED   → remains BLOCKED
CANCELLED → remains CANCELLED
WAITING   → remains WAITING
RUNNING   → WAITING
```

A task that was `RUNNING` when the service stopped is returned to `WAITING`.

Its attempt count is preserved.

This uses an **at-least-once execution model**.

A crash at exactly the wrong moment can potentially cause a task to execute again, but this design avoids silently losing unfinished work.

---

# Technology Stack

- **Python 3**
- **FastAPI**
- **SQLite**
- **asyncio**
- **Pydantic**
- **pytest**
- **pytest-asyncio**
- **httpx**

The project intentionally avoids external distributed infrastructure such as:

- Redis
- Celery
- Kafka
- Kubernetes
- PostgreSQL

The goal is to keep the service small enough to understand and review easily.

---

# Project Structure

```text
task-runner/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── dependency_service.py
│   ├── models.py
│   ├── repository.py
│   ├── runner.py
│   ├── scheduler.py
│   └── schemas.py
│
├── data/
│   └── task_runner.db
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_blocked.py
│   ├── test_cancel.py
│   ├── test_concurrency.py
│   ├── test_database.py
│   ├── test_dependencies.py
│   ├── test_health.py
│   ├── test_restart.py
│   ├── test_runner.py
│   ├── test_schemas.py
│   ├── test_stats.py
│   └── test_tasks.py
│
├── .gitignore
├── requirements.txt
├── README.md
├── DESIGN.md
└── TRADEOFFS.md
```

---

# Setup

## 1. Clone the repository

```bash
git clone <your-github-repository-url>
cd task-runner
```

---

## 2. Create a virtual environment

### Windows PowerShell

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

If PowerShell activation is blocked, you can use:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then activate again:

```powershell
.venv\Scripts\Activate.ps1
```

---

## 3. Install dependencies

```powershell
pip install -r requirements.txt
```

---

# Running the Service

Start the FastAPI application:

```powershell
uvicorn app.main:app --reload
```

The service will be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

---

# Configuration

The scheduler concurrency can be configured with an environment variable.

Default:

```text
MAX_CONCURRENCY=3
```

### Windows PowerShell

```powershell
$env:MAX_CONCURRENCY="5"
uvicorn app.main:app --reload
```

The scheduler polling interval can also be configured:

```powershell
$env:SCHEDULER_INTERVAL="0.25"
```

---

# API

## Health Check

### Request

```http
GET /health
```

### Response

```json
{
  "status": "healthy"
}
```

---

# Submit a Task

### Request

```http
POST /tasks
```

Example:

```json
{
  "name": "Upload Document",
  "dependencies": [],
  "max_retries": 3,
  "failure_probability": 0.2,
  "duration_min": 1,
  "duration_max": 3,
  "timeout": 10
}
```

Example response:

```json
{
  "id": "task-id",
  "name": "Upload Document",
  "status": "waiting",
  "attempts": 0,
  "max_retries": 3,
  "dependencies": []
}
```

---

# Submit a Dependent Task

First create:

```text
Upload Document
```

Suppose its ID is:

```text
abc123
```

Then submit:

```json
{
  "name": "Extract Text",
  "dependencies": [
    "abc123"
  ],
  "max_retries": 3,
  "failure_probability": 0.1,
  "duration_min": 1,
  "duration_max": 3,
  "timeout": 10
}
```

The task remains:

```text
WAITING
```

until `Upload Document` succeeds.

---

# Get Task Status

### Request

```http
GET /tasks/{task_id}
```

Example:

```text
GET /tasks/abc123
```

Response:

```json
{
  "id": "abc123",
  "name": "Upload Document",
  "status": "succeeded",
  "attempts": 1,
  "max_retries": 3,
  "dependencies": []
}
```

Possible statuses:

```text
waiting
running
succeeded
failed
blocked
cancelled
```

---

# Cancel a Task

### Request

```http
POST /tasks/{task_id}/cancel
```

Example:

```text
POST /tasks/abc123/cancel
```

Response:

```json
{
  "id": "abc123",
  "status": "cancelled"
}
```

A task cannot be cancelled after it has reached a terminal state such as:

```text
SUCCEEDED
FAILED
BLOCKED
CANCELLED
```

---

# Get Statistics

### Request

```http
GET /stats
```

Example response:

```json
{
  "total": 10,
  "waiting": 2,
  "running": 1,
  "succeeded": 4,
  "failed": 1,
  "blocked": 1,
  "cancelled": 1
}
```

---

# Example Workflow

A document processing pipeline can be represented as:

```text
                 ┌──────────────────┐
                 │ Upload Document  │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │   Extract Text   │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Generate Summary │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │   Send Report    │
                 └──────────────────┘
```

The scheduler automatically determines when each task becomes eligible.

---

# Running Tests

Run the complete test suite:

```powershell
pytest -q
```

For verbose output:

```powershell
pytest
```

Tests use isolated temporary SQLite databases so that test cases do not depend on state left behind by previous test runs.

---

# Task State Model

```text
                    ┌──────────┐
                    │ WAITING  │
                    └────┬─────┘
                         │
                         ▼
                    ┌──────────┐
                    │ RUNNING  │
                    └────┬─────┘
                         │
                ┌────────┴────────┐
                │                 │
                ▼                 ▼
          ┌───────────┐      ┌──────────┐
          │ SUCCEEDED │      │  FAILED  │
          └───────────┘      └────┬─────┘
                                  │
                              retry?
                             /      \
                           yes       no
                           │          │
                           ▼          ▼
                       WAITING      FAILED
```

Blocked and cancelled states are also terminal states for the affected task:

```text
Dependency FAILED
       ↓
   BLOCKED

Cancellation
       ↓
   CANCELLED
```

---

# Design Documentation

Additional design decisions are documented in:

- `DESIGN.md` — architecture, concurrency safety, restart behavior, scheduling rule, and correctness invariant
- `TRADEOFFS.md` — design tradeoffs and limitations

---

# Limitations

This is intentionally a small task runner rather than a production distributed workflow engine.

Current limitations include:

- SQLite is used as the persistent store.
- Scheduling is handled by a single application process.
- The simulated task workload does not represent real external processing.
- FIFO scheduling does not optimize for shortest-job-first execution.
- Restart recovery uses at-least-once execution semantics.
- Running task cancellation is cooperative rather than forceful.
- There is no distributed worker pool.

These choices keep the implementation understandable and appropriate for the scope of the assignment.

---

# License

This project was created as a take-home engineering assignment.