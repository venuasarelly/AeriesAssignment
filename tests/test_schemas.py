import pytest
from pydantic import ValidationError

from app.schemas import TaskCreate


def test_valid_task():
    task = TaskCreate(
        name="extract_text",
        max_retries=3,
        failure_probability=0.2,
    )

    assert task.name == "extract_text"
    assert task.max_retries == 3


def test_invalid_failure_probability():
    with pytest.raises(ValidationError):
        TaskCreate(
            name="extract_text",
            failure_probability=2.0,
        )


def test_invalid_retry_count():
    with pytest.raises(ValidationError):
        TaskCreate(
            name="extract_text",
            max_retries=-1,
        )