import os

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://expense:dev_only_password@127.0.0.1:5432/expenses_test",
)
# Safety check: never run tests (which delete data) against a real database.
assert TEST_DB_URL.rsplit("/", 1)[-1].endswith("_test"), "refusing to test a non-test DB"

# Environment variables beat .env, so these pin the app's settings for tests.
# This must happen BEFORE the app is imported.
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["FX_BASE_URL"] = "https://api.frankfurter.dev/v1"
os.environ["FX_TIMEOUT_SECONDS"] = "5"
os.environ["LOG_LEVEL"] = "WARNING"

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from app.database import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    """Build the test database's tables using the real migrations."""
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(autouse=True)
def clean_tables():
    """Start every test with an empty table and ids counting from 1."""
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE expenses RESTART IDENTITY"))


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def create_expense(client):
    def _create(**overrides):
        payload = {
            "description": "Lunch",
            "amount_minor": 45050,
            "category": "food",
            **overrides,
        }
        response = client.post("/expenses", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _create
