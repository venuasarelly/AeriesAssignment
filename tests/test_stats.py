import sqlite3

from app.database import DATABASE_PATH
from app.repository import (
    create_task,
    get_task_stats,
)


def setup_function():
    connection = sqlite3.connect(DATABASE_PATH)

    try:
        connection.execute(
            "DELETE FROM task_dependencies"
        )
        connection.execute(
            "DELETE FROM tasks"
        )
        connection.commit()
    finally:
        connection.close()


def test_task_stats():
    create_task(
        name="Task 1",
        max_retries=0,
        failure_probability=0,
        duration_min=1,
        duration_max=1,
        timeout=30,
    )

    create_task(
        name="Task 2",
        max_retries=0,
        failure_probability=0,
        duration_min=1,
        duration_max=1,
        timeout=30,
    )

    stats = get_task_stats()

    assert stats["total"] == 2
    assert stats["waiting"] == 2
    assert stats["running"] == 0
    assert stats["succeeded"] == 0
    assert stats["failed"] == 0
    assert stats["blocked"] == 0
    assert stats["cancelled"] == 0