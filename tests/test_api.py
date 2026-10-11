from datetime import date, timedelta

import pytest


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_applications_require_login(client):
    assert client.get("/api/applications").status_code == 401
    assert client.get("/api/emails/d0000001").status_code == 401


def test_me_signed_out(client):
    body = client.get("/api/me").json()
    assert body["email"] is None and body["demo"] is False


def test_demo_login_and_member_since(demo_client):
    body = demo_client.get("/api/me").json()
    assert body["demo"] is True and body["member_since"] == date.today().isoformat()


def test_demo_applications_shape(demo_client):
    data = demo_client.get("/api/applications?since=2004-01-01").json()
    assert set(data["counts"]) <= set("SRINUACN") and len(data["applications"]) >= 5
    first = data["applications"][0]
    assert {"id", "company", "role", "status", "date", "events"} <= set(first)
    assert data["applications"] == sorted(data["applications"], key=lambda a: a["date"], reverse=True)


def test_since_filters_demo_mail(demo_client):
    everything = demo_client.get("/api/applications?since=2004-01-01").json()["applications"]
    recent = (date.today() - timedelta(days=10)).isoformat()
    few = demo_client.get(f"/api/applications?since={recent}").json()
    assert few["since"] == recent and 0 < len(few["applications"]) < len(everything)
    assert all(a["date"] >= recent for a in few["applications"])


@pytest.mark.parametrize("bad", ["yesterday", "2026-13-40", "2999-01-01", "2026/05/01"])
def test_bad_since_rejected(demo_client, bad):
    assert demo_client.get(f"/api/applications?since={bad}").status_code == 400


def test_email_copy_for_demo(demo_client):
    mail = demo_client.get("/api/emails/d0000003").json()
    assert "Contoso" in mail["subject"] and mail["html"]
    assert demo_client.get("/api/emails/nope").status_code == 404


def test_logout_clears_session(demo_client):
    demo_client.post("/api/auth/logout")
    assert demo_client.get("/api/me").json()["email"] is None


def test_login_unconfigured_is_503(client):
    assert client.get("/api/auth/login", follow_redirects=False).status_code == 503


def test_callback_rejects_state_mismatch(client):
    r = client.get("/api/auth/callback?code=abc&state=wrong", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"].endswith("login=failed")


# ---- signed-in (non-demo) path, Gmail replaced by a fake ----
import time  # noqa: E402

from _lib import auth, gmail, main  # noqa: E402


def signed_in(client, **extra):
    client.cookies.set(auth.COOKIE, auth.seal({"email": "me@example.com", "access_token": "t", "exp": time.time() + 3600, **extra}))
    return client


def test_real_path_reads_gmail_and_classifies(client, monkeypatch):
    seen = {}

    async def fake_list(token, since, limit=500, **kw):
        seen.update(token=token, since=since)
        return [
            {
                "id": "aa11bb22",
                "sender": "jobs-noreply@linkedin.com",
                "subject": "Your application to Dev at Foo GmbH",
                "snippet": "",
                "date": "2026-09-01T10:00:00+00:00",
            }
        ]

    monkeypatch.setattr(gmail, "list_messages", fake_list)
    data = signed_in(client).get("/api/applications?since=2026-05-01").json()
    assert seen == {"token": "t", "since": "2026/05/01"}
    assert data["counts"] == {"R": 1} and data["applications"][0]["company"] == "Foo GmbH"


def test_gmail_failure_is_502(client, monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(gmail, "list_messages", boom)
    assert signed_in(client).get("/api/applications").status_code == 502


def test_results_are_cached_briefly(client, monkeypatch):
    calls = []

    async def fake_list(token, since, limit=500, **kw):
        calls.append(1)
        return []

    monkeypatch.setattr(gmail, "list_messages", fake_list)
    c = signed_in(client)
    c.get("/api/applications?since=2026-05-01")
    c.get("/api/applications?since=2026-05-01")
    c.get("/api/applications?since=2026-06-01")  # other range = other cache entry
    assert len(calls) == 2


def test_each_user_has_own_cache(client, monkeypatch):
    async def fake_list(token, since, limit=500, **kw):
        return []

    monkeypatch.setattr(gmail, "list_messages", fake_list)
    signed_in(client).get("/api/applications?since=2026-05-01")
    assert any(k.startswith("me@example.com|") for k in main._cache)
    assert not any(k.startswith("other@example.com|") for k in main._cache)


def test_email_endpoint_real_path(client, monkeypatch):
    async def fake_get(token, msg_id):
        return {"id": msg_id, "subject": "S", "from": "f", "date": "d", "html": None, "text": "t", "gmail_url": "u"}

    monkeypatch.setattr(gmail, "get_message", fake_get)
    assert signed_in(client).get("/api/emails/aa11bb22").json()["subject"] == "S"


def test_email_bad_id_is_400(client):
    assert signed_in(client).get("/api/emails/..%2Fx").status_code in (400, 404)
    assert signed_in(client).get("/api/emails/ZZZZZZZZ").status_code == 400
