import base64

import pytest
from _lib import gmail


def b64(s):
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


def test_walk_finds_html_and_text_in_nested_parts():
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/plain", "body": {"data": b64("plain äöü")}},
            {"mimeType": "multipart/related", "parts": [{"mimeType": "text/html", "body": {"data": b64("<p>hi</p>")}}]},
        ],
    }
    out = {}
    gmail._walk(payload, out)
    assert out == {"text/plain": "plain äöü", "text/html": "<p>hi</p>"}


def test_header_lookup_is_case_insensitive():
    msg = {"payload": {"headers": [{"name": "Subject", "value": "Hello"}]}}
    assert gmail._hdr(msg, "subject") == "Hello" and gmail._hdr(msg, "from") == ""


def test_iso_date_parsing_and_fallback():
    ok = {"payload": {"headers": [{"name": "Date", "value": "Tue, 06 Oct 2026 20:19:03 +0000"}]}}
    assert gmail._iso(ok).startswith("2026-10-06T20:19:03")
    fallback = {"payload": {"headers": []}, "internalDate": "1791317943000"}
    assert gmail._iso(fallback).startswith("2026-10-06")


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["../etc/passwd", "abc", "XYZ123456", ""])
async def test_get_message_rejects_bad_ids(bad):
    with pytest.raises(ValueError):
        await gmail.get_message("token", bad)


def test_query_contains_since_date():
    assert "after:2026/05/01" in gmail.QUERY.format(since="2026/05/01")


# ---- HTTP layer with httpx's mock transport ----
import httpx  # noqa: E402


def mock_client_factory(handler):
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real(*args, **kwargs)

    return factory


def batch_reply(request, make):
    """Answer a Gmail batch POST like Google does: multipart/mixed, one HTTP response per part."""
    import re

    ids = re.findall(r"GET /gmail/v1/users/me/messages/(\w+)\?", request.content.decode())
    parts = "".join(
        f"--batch_x\r\nContent-Type: application/http\r\nContent-ID: <response-{n}>\r\n\r\n"
        f"HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{make(i)}\r\n"
        for n, i in enumerate(ids)
    )
    return httpx.Response(200, headers={"content-type": "multipart/mixed; boundary=batch_x"}, text=parts + "--batch_x--")


@pytest.mark.asyncio
async def test_batch_reads_many_messages_in_one_request(monkeypatch):
    import json

    gmail._CACHE.clear()
    posts = []

    def handler(request):
        if request.method == "POST":
            posts.append(1)
            return batch_reply(
                request,
                lambda i: json.dumps({"id": i, "snippet": "s" + i, "payload": {"headers": [{"name": "Subject", "value": "S" + i}]}}),
            )
        return httpx.Response(200, json={"messages": [{"id": f"m{n}"} for n in range(120)]})

    monkeypatch.setattr(gmail.httpx, "AsyncClient", mock_client_factory(handler))
    msgs = await gmail.list_messages("tok", "2026/05/01")
    assert len(msgs) == 120 and msgs[5]["subject"] == "Sm5" and msgs[5]["snippet"] == "sm5"
    assert len(posts) == 3  # 120 messages, 50 per batch: three requests, not 120


@pytest.mark.asyncio
async def test_batch_failure_falls_back_to_single_requests(monkeypatch):
    gmail._CACHE.clear()

    def handler(request):
        if request.method == "POST":
            return httpx.Response(500)
        if "/messages/" in str(request.url):
            return httpx.Response(200, json={"id": "m1", "snippet": "x", "payload": {"headers": []}})
        return httpx.Response(200, json={"messages": [{"id": "m1"}]})

    monkeypatch.setattr(gmail.httpx, "AsyncClient", mock_client_factory(handler))
    assert [m["id"] for m in await gmail.list_messages("tok", "2026/05/01")] == ["m1"]


@pytest.mark.asyncio
async def test_list_messages_pages_and_reads_metadata(monkeypatch):
    def handler(request: httpx.Request):
        url = str(request.url)
        assert request.headers["authorization"] == "Bearer tok"
        if url.endswith("/messages") or "/messages?" in url:
            assert "after%3A2026%2F05%2F01" in url or "after:2026/05/01" in url
            return httpx.Response(200, json={"messages": [{"id": "m1"}, {"id": "m2"}]})
        if request.method == "POST":
            import json as _json

            return batch_reply(request, lambda i: _json.dumps(meta(i)))
        mid = url.split("/messages/")[1].split("?")[0]
        return httpx.Response(200, json=meta(mid))

    def meta(mid):
        return {
            "id": mid,
            "snippet": "snip " + mid,
            "payload": {
                "headers": [
                    {"name": "From", "value": "a@b.c"},
                    {"name": "Subject", "value": "Subj " + mid},
                    {"name": "Date", "value": "Tue, 06 Oct 2026 20:19:03 +0000"},
                ]
            },
        }

    monkeypatch.setattr(gmail.httpx, "AsyncClient", mock_client_factory(handler))
    msgs = await gmail.list_messages("tok", "2026/05/01")
    assert [m["id"] for m in msgs] == ["m1", "m2"] and msgs[0]["subject"] == "Subj m1" and msgs[1]["snippet"] == "snip m2"


@pytest.mark.asyncio
async def test_list_messages_skips_failed_fetches(monkeypatch):
    def handler(request):
        if "/messages/" in str(request.url):
            return httpx.Response(404)
        return httpx.Response(200, json={"messages": [{"id": "m1"}]})

    monkeypatch.setattr(gmail.httpx, "AsyncClient", mock_client_factory(handler))
    assert await gmail.list_messages("tok", "2026/05/01") == []


@pytest.mark.asyncio
async def test_get_message_returns_html_and_text(monkeypatch):
    body = {
        "id": "abcdef12",
        "snippet": "s",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [{"name": "Subject", "value": "Hi"}, {"name": "From", "value": "x@y.z"}, {"name": "Date", "value": "Tue, 06 Oct 2026 20:19:03 +0000"}],
            "parts": [{"mimeType": "text/html", "body": {"data": b64("<b>x</b>")}}],
        },
    }
    monkeypatch.setattr(gmail.httpx, "AsyncClient", mock_client_factory(lambda r: httpx.Response(200, json=body)))
    m = await gmail.get_message("tok", "abcdef12")
    assert m["html"] == "<b>x</b>" and m["subject"] == "Hi" and m["gmail_url"].endswith("abcdef12")


def test_plain_strips_html_doctype():
    from _lib.gmail import _plain

    out = {
        "text/html": '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"><html><head><style>a{}</style></head><body><p>Leider konnte Ihre Bewerbung &amp; mehr</p></body></html>'
    }
    assert _plain(out) == "Leider konnte Ihre Bewerbung & mehr"
    assert _plain({"text/plain": "<!DOCTYPE html><html><body>Hi</body></html>"}) == "Hi"


@pytest.mark.asyncio
async def test_list_messages_stops_at_deadline_and_reports_partial():
    import time

    from _lib import gmail

    gmail._CACHE.clear()
    stats = {}
    orig = httpx.AsyncClient
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if request.url.path.endswith("/messages"):
            return httpx.Response(200, json={"messages": [{"id": "a1"}, {"id": "b2"}]})
        return httpx.Response(200, json={"id": "x", "payload": {"headers": []}, "snippet": ""})

    transport = httpx.MockTransport(handler)
    gmail.httpx.AsyncClient = lambda **kw: orig(transport=transport, **kw)
    try:
        out = await gmail.list_messages("t", "2026/05/01", deadline=time.monotonic() - 1, stats=stats)
    finally:
        gmail.httpx.AsyncClient = orig
    assert out == [] and stats["partial"] is True
