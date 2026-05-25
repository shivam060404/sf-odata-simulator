from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ["API_TOKEN"] = "test-token"

from app.database import JsonStore, get_store
from app.main import app


@pytest.fixture
def client(tmp_path):
    store = JsonStore(path=str(tmp_path / "data.json"))

    def override_get_store():
        return store

    app.dependency_overrides[get_store] = override_get_store
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
