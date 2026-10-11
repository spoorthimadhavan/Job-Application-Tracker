"""Thin Gmail REST client: list job-related mail, fetch one message body."""

import asyncio
import base64
import html
import json
import re
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx

API = "https://gmail.googleapis.com/gmail/v1/users/me"
QUERY = (
    "after:{since} (Bewerbung OR application OR candidacy OR Absage OR interview OR "
    'Vorstellungsgespräch OR "your application" OR Neuigkeiten OR "thank you for applying") '
    "-in:sent -in:drafts -from:(jobalerts-noreply@linkedin.com OR jobalert.indeed.com OR match.indeed.com OR "
    "jobagent.stepstone.de OR noreply@github.com OR notifications@github.com OR notifications@vercel.com OR glassdoor.com)"
)
BATCH = "https://gmail.googleapis.com/batch/gmail/v1"
META = "format=metadata&metadataHeaders=From&metadataHeaders=Subject&metadataHeaders=Date"


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


def _parse_batch(resp: httpx.Response, ids: list[str]) -> dict[str, dict | None]:
    """Read Google's multipart/mixed batch answer: one HTTP response per part, keyed by Content-ID."""
    m = re.search(r"boundary=([^;\s]+)", resp.headers.get("content-type", ""))
    out: dict[str, dict | None] = {}
    if not m:
        return out
    for part in resp.text.split("--" + m.group(1).strip('"')):
        cid = re.search(r"Content-ID:\s*<response-(\d+)>", part, re.I)
        if not cid:
            continue
        i = ids[int(cid.group(1))]
        inner = part.split("\r\n\r\n", 1)[-1] if "\r\n\r\n" in part else part.split("\n\n", 1)[-1]
        status = re.match(r"\s*HTTP/[\d.]+\s+(\d+)", inner)
        body = re.split(r"\r?\n\r?\n", inner, maxsplit=1)
        try:
            out[i] = json.loads(body[1]) if status and status.group(1) == "200" and len(body) > 1 else None
        except ValueError:
            out[i] = None
        if status and status.group(1) in ("429", "500", "502", "503"):
            out[i] = {"_retry": True}
    return out


async def _fetch_chunk(c: httpx.AsyncClient, ids: list[str], query: str) -> dict[str, dict | None]:
    """Up to ~50 messages in ONE request (Gmail batch). Falls back to single requests if the batch call fails."""
    boundary = "jtbatch"
    body = (
        "".join(
            f"--{boundary}\r\nContent-Type: application/http\r\nContent-ID: <{n}>\r\n\r\nGET /gmail/v1/users/me/messages/{i}?{query}\r\n\r\n"
            for n, i in enumerate(ids)
        )
        + f"--{boundary}--"
    )
    try:
        r = await c.post(BATCH, content=body, headers={"Content-Type": f"multipart/mixed; boundary={boundary}"})
        if r.status_code == 200:
            got = _parse_batch(r, ids)
            if got:
                return got
    except httpx.HTTPError:
        pass

    async def one(i):
        r = await c.get(f"{API}/messages/{i}?{query}")
        return i, (r.json() if r.status_code == 200 else ({"_retry": True} if r.status_code in (429, 500, 502, 503) else None))

    return dict(await asyncio.gather(*[one(i) for i in ids]))


async def _fetch_many(c, ids: list[str], query: str, cache: dict, deadline, stats, chunk: int = 50, parallel: int = 4) -> None:
    todo = [i for i in ids if i not in cache]
    chunks = [todo[n : n + chunk] for n in range(0, len(todo), chunk)]
    sem = asyncio.Semaphore(parallel)

    async def run(group):
        async with sem:
            if deadline and time.monotonic() > deadline:  # out of time: the next poll continues from the cache
                if stats is not None:
                    stats["partial"] = True
                return
            got = await _fetch_chunk(c, group, query)
        for i in group:
            v = got.get(i)
            if v and not v.get("_retry"):
                if len(cache) >= _CACHE_MAX:
                    cache.clear()
                cache[i] = v
            elif stats is not None and (i not in got or (v and v.get("_retry"))):
                stats["partial"] = True

    await asyncio.gather(*[run(g) for g in chunks])


async def list_messages(token: str, since: str, limit: int = 500, deadline: float | None = None, stats: dict | None = None) -> list[dict]:
    h = {"Authorization": f"Bearer {token}"}
    ids, page = [], None
    async with httpx.AsyncClient(timeout=30, headers=h) as c:
        while len(ids) < limit:
            params = {"q": QUERY.format(since=since), "maxResults": min(500, limit)}
            if page:
                params["pageToken"] = page
            r = await c.get(f"{API}/messages", params=params)
            r.raise_for_status()
            data = r.json()
            ids += [m["id"] for m in data.get("messages", [])]
            page = data.get("nextPageToken")
            if not page:
                break
        ids = ids[:limit]
        await _fetch_many(c, ids, META, _CACHE, deadline, stats)
    return [
        {
            "id": m["id"],
            "sender": _hdr(m, "from"),
            "subject": _hdr(m, "subject"),
            "snippet": m.get("snippet", ""),
            "date": _iso(m),
            "labels": m.get("labelIds", []),
        }
        for i in ids
        if (m := _CACHE.get(i))
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
        "subject": html.unescape(_hdr(m, "subject")),
        "from": html.unescape(_hdr(m, "from")),
        "date": _iso(m),
        "html": out.get("text/html"),
        "text": out.get("text/plain") or m.get("snippet", ""),
        "gmail_url": f"https://mail.google.com/mail/u/0/#all/{msg_id}",
    }


_BODY_CACHE: dict[str, str] = {}
_FULL: dict[str, dict] = {}


def _plain(out: dict) -> str:
    txt = out.get("text/plain") or ""
    if not txt.strip() or re.match(r"\s*<(!doctype|html|head|body|table)", txt, re.I):
        txt = out.get("text/html") or txt
    txt = re.sub(r"(?is)<(head|style|script)\b.*?</\1>", " ", txt)
    txt = re.sub(r"(?s)<[^>]+>", " ", txt)
    return re.sub(r"\s+", " ", html.unescape(txt)).strip()


async def enrich_truncated(token: str, msgs: list[dict], needs_body, cap: int = 150, deadline: float | None = None, stats: dict | None = None) -> list[dict]:
    """The preview often stops before the decision ("Thank you for applying ... we reviewed ...").
    For mails where that matters, read the body and classify from it. The preview column keeps the short text."""
    todo = [m for m in sorted(msgs, key=lambda x: x["date"], reverse=True) if needs_body(m)][:cap]
    if not todo:
        return msgs
    async with httpx.AsyncClient(timeout=30, headers={"Authorization": f"Bearer {token}"}) as c:
        await _fetch_many(c, [m["id"] for m in todo], "format=full", _FULL, deadline, stats, chunk=20, parallel=4)
    for m in todo:
        m["preview"] = m["snippet"]
        if m["id"] in _BODY_CACHE:
            m["snippet"] = _BODY_CACHE[m["id"]]
        elif full := _FULL.pop(m["id"], None):
            out: dict = {}
            _walk(full.get("payload", {}), out)
            if text := _plain(out)[:1500]:
                _BODY_CACHE[m["id"]] = m["snippet"] = text
    return msgs
