import pytest
from _lib import main
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    main._cache.clear()
    return TestClient(main.app, base_url="https://testserver")


@pytest.fixture()
def demo_client(client):
    client.get("/api/auth/demo", follow_redirects=False)
    return client
