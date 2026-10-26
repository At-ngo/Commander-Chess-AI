import pytest
from fastapi.testclient import TestClient
from apps.api.src.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
