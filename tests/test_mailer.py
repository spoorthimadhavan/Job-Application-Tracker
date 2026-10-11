import httpx
import pytest
from _lib import auth, mailer, settings


def _mock(monkeypatch, handler):
    real = httpx.AsyncClient
    monkeypatch.setattr(mailer.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))


@pytest.mark.asyncio
async def test_disabled_without_key(monkeypatch):
    monkeypatch.setattr(settings, "RESEND_API_KEY", "")
    assert await mailer.send_welcome("a@b.com") is False


@pytest.mark.asyncio
async def test_sends_to_resend(monkeypatch):
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_test")
    seen = {}

    def handler(req):
        seen["auth"], seen["body"] = req.headers["authorization"], req.read().decode()
        return httpx.Response(200, json={"id": "1"})

    _mock(monkeypatch, handler)
    assert await mailer.send_welcome("a@b.com") is True
    assert seen["auth"] == "Bearer re_test" and "a@b.com" in seen["body"]


@pytest.mark.asyncio
@pytest.mark.parametrize("handler", [lambda r: httpx.Response(422), lambda r: (_ for _ in ()).throw(httpx.ConnectError("down"))])
async def test_failures_never_raise(monkeypatch, handler):
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_test")
    _mock(monkeypatch, handler)
    assert await mailer.send_welcome("a@b.com") is False


def test_html_is_escaped():
    assert "<script>" not in mailer.welcome_message("<script>@x.com")["html"]


def test_callback_sends_welcome_once(client, monkeypatch):
    sent = []

    async def fake_exchange(request, code):
        return {"email": "me@x.com", "access_token": "t", "refresh_token": "r", "exp": 9e9, "scope": "https://www.googleapis.com/auth/gmail.readonly"}

    async def fake_send(to):
        sent.append(to)
        return True

    monkeypatch.setattr(auth, "exchange_code", fake_exchange)
    monkeypatch.setattr(mailer, "send_welcome", fake_send)
    client.cookies.set(auth.STATE_COOKIE, "s")
    assert client.get("/api/auth/callback?code=c&state=s", follow_redirects=False).status_code == 307
    client.cookies.set(auth.STATE_COOKIE, "s")
    client.get("/api/auth/callback?code=c&state=s", follow_redirects=False)
    assert sent == ["me@x.com"]  # second login in same browser: marker cookie, no second mail


def test_callback_without_gmail_scope_is_rejected(client, monkeypatch):
    async def fake_exchange(request, code):
        return {"email": "me@x.com", "access_token": "t", "exp": 9e9, "scope": "openid email"}

    monkeypatch.setattr(auth, "exchange_code", fake_exchange)
    client.cookies.set(auth.STATE_COOKIE, "s")
    r = client.get("/api/auth/callback?code=c&state=s", follow_redirects=False)
    assert r.headers["location"] == "/?login=scope"
    assert auth.COOKIE not in r.headers.get("set-cookie", "")
