# Design

## 1. Architecture

The Task Runner is organized into a few small components with clear responsibilities.

```text
                    ┌─────────────────────┐
                    │      FastAPI        │
                    │      API Layer      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     Scheduler       │
                    │ dependency + queue  │
                    │ concurrency control │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       Runner        │
                    │ simulate task work  │
                    │ failure + timeout   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Repository       │
                    │ persistence + state │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       SQLite        │
                    └─────────────────────┘
```

### Components

### `main.py`

Responsible for:

- FastAPI application
- HTTP endpoints
- Startup and shutdown lifecycle
- Restart recovery

### `scheduler.py`

Responsible for:

- Finding ready tasks
- Enforcing concurrency
- Claiming tasks
- Starting task execution
- Processing execution results

### `runner.py`

Responsible for:

- Simulating task execution
- Simulating random failures
- Enforcing execution timeout
- Returning success or failure

The runner does not directly modify task state in the database.

### `repository.py`

Responsible for:

- Reading task state
- Updating task state
- Creating tasks
- Managing dependencies
- Retry scheduling
- Cancellation
- Restart recovery
- Statistics

### `dependency_service.py`

Responsible for circular dependency detection.

### `database.py`

Responsible for SQLite connection management and database initialization/migration.

---

# 2. Task Lifecycle

The primary task states are:

```text
WAITING
RUNNING
SUCCEEDED
FAILED
BLOCKED
CANCELLED
```

Typical execution:

```text
WAITING
   │
   │ dependencies satisfied
   ▼
RUNNING
   │
   ├───────────────► SUCCEEDED
   │
   └── failure
          │
          ├── retries remaining ──► WAITING
          │
          └── retries exhausted ─► FAILED
```

A waiting task can also become:

```text
WAITING → BLOCKED
```

when one of its dependencies permanently fails, is blocked, or is cancelled.

A waiting or running task can become:

```text
WAITING/RUNNING → CANCELLED
```

through the cancellation API.

---

# 3. Dependency Handling

Dependencies are stored in a separate table:

```text
task_dependencies
```

with:

```text
task_id
depends_on_task_id
```

For a task to become ready, all dependencies must have:

```text
status = succeeded
```

The scheduler queries only tasks whose dependencies have all succeeded.

This prevents a task from starting before its prerequisites are complete.

---

# 4. Circular Dependency Detection

Circular dependencies are rejected during task submission.

The implementation uses depth-first search.

For a proposed relationship:

```text
Task A depends on Task B
```

the system traverses the dependencies of `B`.

If traversal reaches `A`, adding the proposed edge would create a cycle.

Example:

```text
A → B
B → C
```

Attempting to add:

```text
C → A
```

would create:

```text
A → B → C → A
```

so the submission is rejected.

The complexity is approximately:

```text
O(V + E)
```

for the portion of the dependency graph traversed, where `V` is the number of visited tasks and `E` is the number of dependency edges.

---

# 5. Concurrency Safety

The service has two layers of concurrency protection.

## Application-level protection

The scheduler uses:

```python
asyncio.Semaphore
```

with a configurable maximum concurrency.

For example:

```text
MAX_CONCURRENCY=3
```

allows at most three task executions at a time.

Conceptually:

```text
Task A ──┐
Task B ──┼──► Semaphore(3)
Task C ──┤
Task D ──┘
```

Only three execution slots can be acquired simultaneously.

## Database-level protection

The scheduler does not simply read a task and assume it owns it.

It atomically changes:

```text
WAITING → RUNNING
```

using a conditional SQL update:

```sql
UPDATE tasks
SET status = 'running'
WHERE id = ?
  AND status = 'waiting'
```

The repository checks the number of affected rows.

If the result is:

```text
1
```

the task was successfully claimed.

If the result is:

```text
0
```

another scheduler operation already changed the task state.

This prevents duplicate task claiming.

---

# 6. Correctness Invariant

The primary correctness invariant is:

> A task may enter `RUNNING` only if all of its dependencies are `SUCCEEDED` and the scheduler has acquired a concurrency slot.

This is enforced in two places.

First, `get_ready_tasks()` only returns tasks where no dependency has a non-successful state.

Second, `schedule_ready_tasks()` acquires the semaphore before claiming the task.

Finally, `mark_task_running()` uses an atomic:

```text
WAITING → RUNNING
```

database transition.

This means task execution cannot be started merely because a task was previously observed as waiting.

---

# 7. Scheduling Rule

The scheduler uses:

> FIFO ordering among currently ready tasks.

Ready tasks are ordered by:

```text
created_at ASC
```

Therefore, older eligible tasks are considered before newer eligible tasks.

Example:

```text
Task A created at 10:00
Task B created at 10:01
Task C created at 10:02
```

If all three are ready:

```text
A → B → C
```

---

# 8. Bad Scheduling Example

FIFO is intentionally simple, but it is not optimal for every workload.

Suppose the concurrency limit is:

```text
2
```

and the ready queue is:

```text
Task A = 60 seconds
Task B = 60 seconds
Task C = 1 second
```

FIFO starts:

```text
A + B
```

while:

```text
C
```

waits.

Even though `C` could finish very quickly, it cannot start until a concurrency slot becomes available.

A shortest-job-first policy could improve average completion time in this scenario.

However, FIFO was selected because it is:

- deterministic
- easy to understand
- easy to test
- fair based on submission order
- appropriate for the small scope of this assignment

---

# 9. Retry Strategy

Failures are handled by the scheduler and repository rather than by the runner.

The runner returns:

```text
True
```

for success and:

```text
False
```

for failure.

The scheduler then decides what to do.

Retry delays use exponential backoff:

```text
Retry 1 → 1 second
Retry 2 → 2 seconds
Retry 3 → 4 seconds
```

The next retry time is stored as:

```text
next_run_at
```

in SQLite.

The scheduler only selects waiting tasks whose retry time has arrived.

This prevents the scheduler from repeatedly executing a task before its retry delay has elapsed.

---

# 10. Retry Count Semantics

`max_retries` represents the number of retries **after the initial attempt**.

For:

```text
max_retries = 3
```

the maximum number of executions is:

```text
1 initial attempt
+ 3 retries
= 4 attempts
```

The `attempts` field is persisted in SQLite.

This means restart recovery does not reset the retry history.

---

# 11. Failed Dependency Propagation

A task becomes `BLOCKED` when one of its dependencies is:

```text
FAILED
BLOCKED
CANCELLED
```

This is processed by the scheduler.

Example:

```text
A → FAILED
│
▼
B → BLOCKED
│
▼
C → BLOCKED
```

Because the blocking operation is applied repeatedly, blocked status propagates through longer dependency chains.

This guarantees that downstream tasks do not remain in `WAITING` forever when their required work can no longer succeed.

---

# 12. Cancellation Semantics

Cancellation is cooperative.

The API can change:

```text
WAITING → CANCELLED
```

or:

```text
RUNNING → CANCELLED
```

A running coroutine may continue until its current simulated execution finishes.

However, successful completion uses a conditional update:

```sql
UPDATE tasks
SET status = 'succeeded'
WHERE id = ?
  AND status = 'running'
```

Therefore, if the task has already been cancelled:

```text
CANCELLED
```

the later completion cannot overwrite the state with:

```text
SUCCEEDED
```

Dependents of a cancelled task become `BLOCKED`.

This behavior favors correctness of persisted state over forcibly terminating arbitrary work.

---

# 13. Timeout Design

Each task may specify a timeout.

The runner wraps simulated execution with:

```python
asyncio.wait_for(...)
```

If execution exceeds the configured timeout:

```text
TimeoutError
```

is converted into a failed execution result.

The scheduler then applies the normal retry policy.

Therefore:

```text
RUNNING
   ↓
TIMEOUT
   ↓
FAILED ATTEMPT
   ↓
retry if available
```

This keeps timeout handling integrated with the existing failure/retry mechanism.

---

# 14. Restart Behavior

The service persists task state in SQLite.

During application startup, tasks that were:

```text
RUNNING
```

are changed to:

```text
WAITING
```

before the scheduler starts.

Other states are left unchanged:

```text
SUCCEEDED → SUCCEEDED
FAILED    → FAILED
BLOCKED   → BLOCKED
CANCELLED → CANCELLED
WAITING   → WAITING
RUNNING   → WAITING
```

Attempts are not reset.

## Why?

The system uses an **at-least-once execution model**.

Consider this sequence:

```text
1. Task performs work
2. Process crashes
3. Success state was not persisted
```

After restart, the task appears unfinished and may execute again.

This can create duplicate work.

However, the alternative would be risking silent loss of unfinished work.

For this small task runner, at-least-once execution was chosen because it is easier to reason about and avoids silently dropping tasks.

In a production system, individual tasks should ideally be idempotent.

---

# 15. Persistence

SQLite is used because the assignment requires persistent state across restarts but does not require a distributed database.

The database contains:

### `tasks`

Stores:

- task ID
- name
- status
- attempts
- retry configuration
- failure probability
- execution duration
- timeout
- creation/update timestamps
- next retry time

### `task_dependencies`

Stores relationships between tasks.

Foreign keys use cascading deletion so removing a task also removes its dependency records.

---

# 16. Database Migration

The application checks whether the `next_run_at` column exists.

If an older database was created before retry scheduling was added, the application adds the missing column using:

```sql
ALTER TABLE tasks
ADD COLUMN next_run_at REAL
```

This prevents an existing local database from breaking after the schema change.

---

# 17. Testing Strategy

Tests cover the major correctness properties of the service.

### Database

- database creation
- task persistence

### API

- health endpoint
- task submission
- task status

### Dependencies

- valid dependency chains
- circular dependency rejection

### Scheduler

- concurrency limit

### Execution

- successful execution
- failed execution
- timeout behavior

### Retry

- retry scheduling
- exponential backoff
- permanent failure

### Blocking

- failed dependency
- blocked dependency propagation

### Cancellation

- waiting task cancellation
- completed task cancellation rejection
- cancelled dependency blocking

### Restart

- running task recovery
- completed task preservation
- terminal state preservation

### Statistics

- task counts by state

Tests use isolated temporary SQLite databases through `tests/conftest.py`, preventing tests from sharing persistent application state.

---

# 18. Graceful Shutdown

The FastAPI lifespan manages the scheduler.

On startup:

```text
Initialize database
       ↓
Recover RUNNING tasks
       ↓
Start scheduler
```

On shutdown:

```text
Stop scheduler
       ↓
Wait for running executions
       ↓
Application exits
```

This reduces the chance of leaving active asyncio tasks behind during normal application shutdown.

---

# 19. Separation of Responsibilities

A key design decision is keeping execution separate from persistence.

The runner answers:

> Did this execution succeed?

The scheduler answers:

> What should happen next?

The repository answers:

> How should that state be persisted?

For example:

```text
runner.py
   ↓
False
   ↓
scheduler.py
   ↓
handle_task_failure()
   ↓
repository.py
   ↓
WAITING / FAILED
```

This makes the components easier to test independently and avoids embedding database logic inside task execution code.