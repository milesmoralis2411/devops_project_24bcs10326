"""Shared pytest fixtures.

Tests never touch the application's real database: DATABASE_URL is overridden
*before* the app is imported. By default an in-memory SQLite database is used;
CI sets TEST_DATABASE_URL to a throw-away PostgreSQL service container so the
same tests also run against the production database engine.
"""

import os

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ["SEED_DEMO_DATA"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_product(client):
    """Factory that creates a product through the API and returns its JSON."""
    counter = {"n": 0}

    def _make(**overrides):
        counter["n"] += 1
        payload = {
            "sku": f"TEST-{counter['n']:03d}",
            "name": f"Test product {counter['n']}",
            "category": "Electronics",
            "supplier": "Acme",
            "location": "A-01-01",
            "quantity": 50,
            "reorder_level": 10,
            "unit_price": 100.0,
        }
        payload.update(overrides)
        response = client.post("/api/products", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _make
