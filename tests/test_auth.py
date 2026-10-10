from types import SimpleNamespace

import pytest
from _lib import auth, settings
from fastapi import HTTPException


def test_seal_roundtrip_and_tamper():
    token = auth.seal({"email": "a@b.c"})
    assert auth.unseal(token) == {"email": "a@b.c"}
    assert auth.unseal(token[:-3] + "xxx") is None
    assert auth.unseal(None) is None and auth.unseal("garbage") is None


def test_cookie_is_encrypted():
    assert "a@b.c" not in auth.seal({"email": "a@b.c"})


def req(headers):
    return SimpleNamespace(headers=headers, cookies={})


def test_redirect_uri_from_forwarded_headers():
    r = req({"x-forwarded-host": "tracker.example.com", "x-forwarded-proto": "https"})
    assert auth.redirect_uri(r) == "https://tracker.example.com/api/auth/callback"


def test_redirect_uri_localhost_defaults_to_http():
    assert auth.redirect_uri(req({"host": "localhost:8000"})) == "http://localhost:8000/api/auth/callback"


def test_redirect_uri_env_override(monkeypatch):
    monkeypatch.setattr(settings, "REDIRECT_URI", "https://fixed/cb")
    assert auth.redirect_uri(req({"host": "x"})) == "https://fixed/cb"


def test_login_url_has_scope_and_state(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "cid")
    url = auth.login_url(req({"host": "localhost:8000"}), "st4te")
    assert "gmail.readonly" in url and "state=st4te" in url and "client_id=cid" in url and "access_type=offline" in url


def test_require_session_401():
    with pytest.raises(HTTPException) as e:
        auth.require_session(SimpleNamespace(cookies={}))
    assert e.value.status_code == 401


@pytest.mark.asyncio
async def test_access_token_uses_valid_cached_token():
    import time

    assert await auth.access_token({"access_token": "t", "exp": time.time() + 600}) == "t"


@pytest.mark.asyncio
async def test_access_token_without_refresh_token_is_401():
    with pytest.raises(HTTPException):
        await auth.access_token({"exp": 0})


def test_new_state_is_random():
    assert auth.new_state() != auth.new_state()
