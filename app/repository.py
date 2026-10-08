from datetime import datetime, timezone
from uuid import uuid4
import time

from app.database import get_connection
from app.models import TaskStatus


def create_task(
    name: str,
    max_retries: int,
    failure_probability: float,
    duration_min: float,
    duration_max: float,
    timeout: float | None,
) -> str:

    task_id = str(uuid4())

    now = datetime.now(timezone.utc).isoformat()

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO tasks (
    id, name, status, attempts, max_retries,
    failure_probability, duration_min, duration_max,
    timeout, created_at, updated_at, next_run_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                name,
                TaskStatus.WAITING.value,
                0,
                max_retries,
                failure_probability,
                duration_min,
                duration_max,
                timeout,
                now,
                now,
                None
            ),
        )

        connection.commit()

        return task_id

    finally:
        connection.close()


def task_exists(task_id: str) -> bool:
    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT 1
            FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        ).fetchone()

        return row is not None

    finally:
        connection.close()


def add_dependency(
    task_id: str,
    depends_on_task_id: str,
) -> None:

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO task_dependencies (
                task_id,
                depends_on_task_id
            )
            VALUES (?, ?)
            """,
            (
                task_id,
                depends_on_task_id,
            ),
        )

        connection.commit()

    finally:
        connection.close()

def delete_task(task_id: str) -> None:
    connection = get_connection()

    try:
        connection.execute(
            """
            DELETE FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        )

        connection.commit()

    finally:
        connection.close()

def get_task(task_id: str):
    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT *
            FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        ).fetchone()

        return row

    finally:
        connection.close()


def get_dependencies(task_id: str) -> list[str]:
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT depends_on_task_id
            FROM task_dependencies
            WHERE task_id = ?
            """,
            (task_id,),
        ).fetchall()

        return [
            row["depends_on_task_id"]
            for row in rows
        ]

    finally:
        connection.close()


def get_ready_tasks():
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT t.*
            FROM tasks t
            WHERE t.status = 'waiting'
              AND (
                  t.next_run_at IS NULL
                  OR t.next_run_at <= ?
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM task_dependencies d
                  JOIN tasks dependency
                    ON dependency.id = d.depends_on_task_id
                  WHERE d.task_id = t.id
                    AND dependency.status != 'succeeded'
              )
            ORDER BY t.created_at ASC
            """,
            (time.time(),),
        ).fetchall()

        return rows

    finally:
        connection.close()

def mark_task_running(task_id: str) -> bool:
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE tasks
            SET status = 'running',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND status = 'waiting'
            """,
            (task_id,),
        )

        connection.commit()

        return cursor.rowcount == 1

    finally:
        connection.close()

def mark_task_succeeded(task_id: str) -> None:
    connection = get_connection()

    try:
        connection.execute(
            """
            UPDATE tasks
            SET status = 'succeeded',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (task_id,),
        )

        connection.commit()

    finally:
        connection.close()    


def mark_task_failed(task_id: str) -> None:
    connection = get_connection()

    try:
        connection.execute(
            """
            UPDATE tasks
            SET status = 'failed',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (task_id,),
        )

        connection.commit()

    finally:
        connection.close()   


def increment_attempts(task_id: str) -> None:
    connection = get_connection()

    try:
        connection.execute(
            """
            UPDATE tasks
            SET attempts = attempts + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (task_id,),
        )

        connection.commit()

    finally:
        connection.close()    


def handle_task_failure(task_id: str) -> bool:
    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT attempts, max_retries
            FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        ).fetchone()

        if row is None:
            return False

        attempts = row["attempts"]
        max_retries = row["max_retries"]

        if attempts <= max_retries:
            delay = 2 ** (attempts - 1)
            next_run_at = time.time() + delay

            connection.execute(
                """
                UPDATE tasks
                SET status = 'waiting',
                    next_run_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (next_run_at, task_id),
            )

            connection.commit()

            print(
                f"Task {task_id} failed. "
                f"Retrying in {delay}s."
            )

            return True

        connection.execute(
            """
            UPDATE tasks
            SET status = 'failed',
                next_run_at = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (task_id,),
        )

        connection.commit()

        print(
            f"Task {task_id} permanently FAILED "
            f"after {attempts} attempts."
        )

        return False

    finally:
        connection.close()      


def mark_blocked_tasks() -> int:
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE tasks
            SET status = 'blocked',
                updated_at = CURRENT_TIMESTAMP
            WHERE status = 'waiting'
              AND EXISTS (
                  SELECT 1
                  FROM task_dependencies d
                  JOIN tasks dependency
                    ON dependency.id = d.depends_on_task_id
                  WHERE d.task_id = tasks.id
                    AND dependency.status IN ('failed', 'blocked', 'cancelled')
              )
            """
        )

        connection.commit()

        return cursor.rowcount

    finally:
        connection.close()                                       