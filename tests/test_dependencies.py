from fastapi.testclient import TestClient

from app.main import app
from app.dependency_service import would_create_cycle


client = TestClient(app)


def create_task(name: str, dependencies: list[str] | None = None):

    response = client.post(
        "/tasks",
        json={
            "name": name,
            "dependencies": dependencies or [],
            "max_retries": 0,
            "failure_probability": 0,
            "duration_min": 1,
            "duration_max": 2,
            "timeout": 30,
        },
    )

    return response


def test_linear_dependencies_are_allowed():

    task_a = create_task("Task A")
    assert task_a.status_code == 200

    task_a_id = task_a.json()["id"]

    task_b = create_task(
        "Task B",
        [task_a_id],
    )

    assert task_b.status_code == 200

    task_b_id = task_b.json()["id"]

    task_c = create_task(
        "Task C",
        [task_b_id],
    )

    assert task_c.status_code == 200


def test_non_circular_dependency():

    task_a = create_task("Task A")
    task_a_id = task_a.json()["id"]

    task_b = create_task(
        "Task B",
        [task_a_id],
    )

    task_b_id = task_b.json()["id"]

    assert would_create_cycle(
        task_b_id,
        task_a_id,
    ) is False

def test_cycle_detection_directly():

    task_a = create_task("Task A")
    task_a_id = task_a.json()["id"]

    task_b = create_task(
        "Task B",
        [task_a_id],
    )
    task_b_id = task_b.json()["id"]

    task_c = create_task(
        "Task C",
        [task_b_id],
    )
    task_c_id = task_c.json()["id"]

    # Current graph:
    #
    # B -> A
    # C -> B
    #
    # If A were to depend on C:
    #
    # A -> C -> B -> A
    #
    # That would create a cycle.

    assert would_create_cycle(
        task_a_id,
        task_c_id,
    ) is True