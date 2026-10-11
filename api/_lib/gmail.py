"""Thin Gmail REST client: list job-related mail, fetch one message body."""

import asyncio
import base64
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx

API = "https://gmail.googleapis.com/gmail/v1/users/me"
QUERY = (
    "after:{since} (Bewerbung OR application OR candidacy OR Absage OR interview OR "
    'Vorstellungsgespräch OR "your application" OR Neuigkeiten OR "thank you for applying")'
)


def _hdr(msg: dict, name: str) -> str:
    for h in msg.get("payload", {}).get("headers", []):
        if h["name"].lower() == name:
            return h["value"]
    return ""


def _iso(msg: dict) -> str:
    try:
        return parsedate_to_datetime(_hdr(msg, "date")).astimezone(UTC).isoformat()
    except (TypeError, ValueError):
        return datetime.fromtimestamp(int(msg.get("internalDate", 0)) / 1000, UTC).isoformat()


_CACHE: dict[str, dict] = {}  # message metadata never changes, so warm instances skip refetching
_CACHE_MAX = 3000


async def list_messages(token: str, since: str, limit: int = 500) -> list[dict]:
    h = {"Authorization": f"Bearer {token}"}
    ids, page = [], None
    async with httpx.AsyncClient(timeout=30, headers=h) as c:
        while len(ids) < limit:
            params = {"q": QUERY.format(since=since), "maxResults": 100}
            if page:
                params["pageToken"] = page
            r = await c.get(f"{API}/messages", params=params)
            r.raise_for_status()
            data = r.json()
            ids += [m["id"] for m in data.get("messages", [])]
            page = data.get("nextPageToken")
            if not page:
                break
        sem = asyncio.Semaphore(40)

        async def one(i):
            if i in _CACHE:
                return _CACHE[i]
            async with sem:
                r = await c.get(
                    f"{API}/messages/{i}",
                    params=[("format", "metadata"), ("metadataHeaders", "From"), ("metadataHeaders", "Subject"), ("metadataHeaders", "Date")],
                )
                if r.status_code != 200:
                    return None
                if len(_CACHE) >= _CACHE_MAX:
                    _CACHE.clear()
                _CACHE[i] = r.json()
                return _CACHE[i]

        raw = await asyncio.gather(*[one(i) for i in ids[:limit]])
    return [
        {
            "id": m["id"],
            "sender": _hdr(m, "from"),
            "subject": _hdr(m, "subject"),
            "snippet": m.get("snippet", ""),
            "date": _iso(m),
            "labels": m.get("labelIds", []),
        }
        for m in raw
        if m
    ]


def _walk(part: dict, out: dict):
    mime, body = part.get("mimeType", ""), part.get("body", {})
    if body.get("data") and mime in ("text/html", "text/plain"):
        txt = base64.urlsafe_b64decode(body["data"] + "==").decode("utf-8", "replace")
        out.setdefault(mime, txt)
    for p in part.get("parts", []) or []:
        _walk(p, out)


async def get_message(token: str, msg_id: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{8,32}", msg_id):
        raise ValueError("bad id")
    async with httpx.AsyncClient(timeout=30, headers={"Authorization": f"Bearer {token}"}) as c:
        r = await c.get(f"{API}/messages/{msg_id}", params={"format": "full"})
        r.raise_for_status()
    m = r.json()
    out: dict = {}
    _walk(m.get("payload", {}), out)
    return {
        "id": msg_id,
        "subject": _hdr(m, "subject"),
        "from": _hdr(m, "from"),
        "date": _iso(m),
        "html": out.get("text/html"),
        "text": out.get("text/plain") or m.get("snippet", ""),
        "gmail_url": f"https://mail.google.com/mail/u/0/#all/{msg_id}",
    }
