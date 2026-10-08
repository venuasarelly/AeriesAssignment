import sqlite3
from pathlib import Path


DATABASE_PATH = Path("data/task_runner.db")


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        DATABASE_PATH,
        check_same_thread=False,
    )

    connection.row_factory = sqlite3.Row

    # Enable foreign key validation in SQLite
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database() -> None:
    connection = get_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                max_retries INTEGER NOT NULL DEFAULT 0,
                failure_probability REAL NOT NULL DEFAULT 0.0,
                duration_min REAL NOT NULL DEFAULT 1.0,
                duration_max REAL NOT NULL DEFAULT 5.0,
                timeout REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                next_run_at REAL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS task_dependencies (
                task_id TEXT NOT NULL,
                depends_on_task_id TEXT NOT NULL,

                PRIMARY KEY (task_id, depends_on_task_id),

                FOREIGN KEY (task_id)
                    REFERENCES tasks(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (depends_on_task_id)
                    REFERENCES tasks(id)
                    ON DELETE CASCADE
            )
            """
        )

        # Migration for databases created before Phase 7.
        # If next_run_at does not exist, add it.
        columns = connection.execute(
            "PRAGMA table_info(tasks)"
        ).fetchall()

        column_names = {
            column["name"]
            for column in columns
        }

        if "next_run_at" not in column_names:
            connection.execute(
                """
                ALTER TABLE tasks
                ADD COLUMN next_run_at REAL
                """
            )

        connection.commit()

    finally:
        connection.close()