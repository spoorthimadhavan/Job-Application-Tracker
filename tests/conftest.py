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


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_gmail_cache():
    import sys

    mod = sys.modules.get("_lib.gmail")
    if mod:
        mod._CACHE.clear()
    yield
