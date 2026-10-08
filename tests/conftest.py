import pytest

from app.database import initialize_database


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    test_database = tmp_path / "test.db"

    monkeypatch.setattr(
        "app.database.DATABASE_PATH",
        test_database,
    )

    initialize_database()