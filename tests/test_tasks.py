from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_create_task():
    response = client.post(
        "/tasks",
        json={
            "name": "Upload Document",
            "dependencies": [],
            "max_retries": 3,
            "failure_probability": 0.2,
            "duration_min": 1,
            "duration_max": 3,
            "timeout": 30,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Upload Document"
    assert data["status"] == "waiting"
    assert data["attempts"] == 0
    assert data["max_retries"] == 3
    assert data["dependencies"] == []


def test_create_task_with_dependency():

    first_response = client.post(
        "/tasks",
        json={
            "name": "Upload Document",
            "dependencies": [],
        },
    )

    assert first_response.status_code == 200

    first_task_id = first_response.json()["id"]

    second_response = client.post(
        "/tasks",
        json={
            "name": "Extract Text",
            "dependencies": [first_task_id],
        },
    )

    assert second_response.status_code == 200

    data = second_response.json()

    assert data["name"] == "Extract Text"
    assert data["dependencies"] == [first_task_id]


def test_dependency_must_exist():

    response = client.post(
        "/tasks",
        json={
            "name": "Extract Text",
            "dependencies": ["invalid-task-id"],
        },
    )

    assert response.status_code == 400


def test_get_task():

    create_response = client.post(
        "/tasks",
        json={
            "name": "Upload Document",
            "dependencies": [],
        },
    )

    task_id = create_response.json()["id"]

    response = client.get(
        f"/tasks/{task_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == task_id
    assert data["name"] == "Upload Document"
    assert data["status"] == "waiting"