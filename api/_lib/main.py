import os
import re
import time
from dataclasses import asdict, fields
from datetime import date

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from . import auth, demo, gmail, mailer, settings
from .classify import RULES_VERSION, Event, build_applications, classify_message, needs_body

app = FastAPI(title="Job Application Tracker")
_cache: dict[str, tuple[float, dict]] = {}
CACHE_SECONDS = 20  # polling from the browser stays cheap for Gmail


def _set_session(resp, data: dict, request: Request | None = None):
    # "created" = day this person first signed in; kept across later sign-ins
    old = auth.session(request) if request else None
    keep = old.get("created") if old and old.get("email") == data.get("email") else None
    data.setdefault("created", keep or date.today().isoformat())
    resp.set_cookie(auth.COOKIE, auth.seal(data), httponly=True, secure=settings.COOKIE_SECURE, samesite="lax", max_age=60 * 60 * 24 * 30, path="/")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/me")
def me(request: Request):
    s = auth.session(request)
    return {
        "email": s["email"] if s else None,
        "demo": bool(s and s.get("demo")),
        "member_since": s.get("created") if s else None,
        "google_configured": settings.GOOGLE_CONFIGURED,
    }


@app.get("/api/auth/login")
def login(request: Request):
    if not settings.GOOGLE_CONFIGURED:
        raise HTTPException(503, "Google sign-in is not configured on this server")
    state = auth.new_state()
    resp = RedirectResponse(auth.login_url(request, state))
    resp.set_cookie(auth.STATE_COOKIE, state, httponly=True, secure=settings.COOKIE_SECURE, samesite="lax", max_age=600, path="/")
    return resp


@app.get("/api/auth/callback")
async def callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error or not code or state != request.cookies.get(auth.STATE_COOKIE):
        return RedirectResponse("/?login=failed")
    try:
        tok = await auth.exchange_code(request, code)
    except Exception:
        return RedirectResponse("/?login=failed")
    if "gmail.readonly" not in tok.get("scope", ""):
        # Google lets people untick the Gmail box on the consent screen; without it every mailbox call fails with 403
        bad = RedirectResponse("/?login=scope")
        bad.delete_cookie(auth.STATE_COOKIE, path="/")
        return bad
    tok.pop("scope", None)
    resp = RedirectResponse("/")
    _set_session(resp, tok, request)
    resp.delete_cookie(auth.STATE_COOKIE, path="/")
    # No database, so "first sign-in" = this browser has no welcome marker yet
    if request.cookies.get(mailer.WELCOME_COOKIE) != tok["email"] and await mailer.send_welcome(tok["email"]):
        resp.set_cookie(mailer.WELCOME_COOKIE, tok["email"], httponly=True, secure=settings.COOKIE_SECURE, samesite="lax", max_age=60 * 60 * 24 * 365, path="/")
    return resp


@app.get("/api/auth/demo")
def demo_login(request: Request):
    resp = RedirectResponse("/")
    _set_session(resp, {"email": "demo@example.com", "demo": True}, request)
    return resp


@app.post("/api/auth/logout")
def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(auth.COOKIE, path="/")
    return resp


@app.get("/api/applications")
async def applications(request: Request, since: str = ""):
    """since = YYYY-MM-DD: only mail from that day on. Default: the server's SINCE setting."""
    s = auth.require_session(request)
    if since:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", since):
            raise HTTPException(400, "since must be YYYY-MM-DD")
        try:
            if date.fromisoformat(since) > date.today():
                raise HTTPException(400, "since is in the future")
        except ValueError:
            raise HTTPException(400, "since is not a date") from None
    else:
        since = settings.SINCE.replace("/", "-")
    cache_key = f"{s['email']}|{since}"
    hit = _cache.get(cache_key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    stats: dict = {}
    if s.get("demo"):
        msgs = [m for m in demo.MESSAGES if m["date"][:10] >= since]
    else:
        token = await auth.access_token(s)
        try:
            t0 = time.monotonic()  # Vercel stops a request after ~10 s, so stop early and let the next poll continue
            msgs = await gmail.list_messages(token, since.replace("-", "/"), deadline=t0 + 5.0, stats=stats)
            msgs = await gmail.enrich_truncated(token, msgs, needs_body, deadline=t0 + 7.5, stats=stats)
        except Exception:
            raise HTTPException(502, "Gmail could not be read right now") from None
    events = [e for e in (classify_message(m) for m in msgs) if e]
    rows = build_applications(events)
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    payload = {"updated_at": time.time(), "since": since, "counts": counts, "applications": rows, "partial": bool(stats.get("partial"))}
    if not payload["partial"]:
        _cache[cache_key] = (time.time(), payload)
    resp = JSONResponse(payload)
    if s.get("access_token") and not s.get("demo"):
        _set_session(resp, s)  # keep the refreshed token in the cookie
    return resp


@app.get("/api/emails/{message_id}")
async def email(message_id: str, request: Request):
    s = auth.require_session(request)
    if s.get("demo"):
        m = demo.body(message_id)
        if not m:
            raise HTTPException(404, "Not found")
        return m
    token = await auth.access_token(s)
    try:
        return await gmail.get_message(token, message_id)
    except ValueError:
        raise HTTPException(400, "Bad id") from None
    except Exception:
        raise HTTPException(502, "Email could not be loaded") from None


class IdsBody(BaseModel):
    since: str


def _check_since(since: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", since):
        raise HTTPException(400, "since must be YYYY-MM-DD")
    try:
        if date.fromisoformat(since) > date.today():
            raise HTTPException(400, "since is in the future")
    except ValueError:
        raise HTTPException(400, "since is not a date") from None
    return since


@app.post("/api/ids")
async def ids(request: Request, body: IdsBody):
    """Ids of all job-related mails since a date (cheap: ids only). The browser then reads them in small steps."""
    s = auth.require_session(request)
    since = _check_since(body.since)
    if s.get("demo"):
        found = [m["id"] for m in demo.MESSAGES if m["date"][:10] >= since]
    else:
        token = await auth.access_token(s)
        try:
            found = await gmail.list_ids(token, since.replace("-", "/"))
        except Exception:
            raise HTTPException(502, "Gmail could not be read right now") from None
    resp = JSONResponse({"version": RULES_VERSION, "ids": found})
    if s.get("access_token") and not s.get("demo"):
        _set_session(resp, s)
    return resp


class ScanBody(BaseModel):
    ids: list[str]


@app.post("/api/scan")
async def scan(request: Request, body: ScanBody):
    """Classify one small batch of mails. Gmail allows only ~50 mails per second, so the browser calls this
    for a few ids at a time (in parallel) and keeps the results."""
    s = auth.require_session(request)
    chunk = body.ids[:60]
    t0 = time.monotonic()
    stats: dict = {}
    if s.get("demo"):
        wanted = set(chunk)
        msgs = [m for m in demo.MESSAGES if m["id"] in wanted]
    else:
        token = await auth.access_token(s)
        try:
            msgs = await gmail.fetch_messages(token, chunk, deadline=t0 + 6.0, stats=stats)
            msgs = await gmail.enrich_truncated(token, msgs, needs_body, deadline=t0 + 8.0, stats=stats)
        except Exception:
            raise HTTPException(502, "Gmail could not be read right now") from None
    events = {}
    for m in msgs:
        e = classify_message(m)
        events[m["id"]] = asdict(e) if e else None
    resp = JSONResponse({"version": RULES_VERSION, "events": events})
    if s.get("access_token") and not s.get("demo"):
        _set_session(resp, s)
    return resp


class BuildBody(BaseModel):
    events: list[dict]


@app.post("/api/build")
async def build(request: Request, body: BuildBody):
    """Group classified mails into one row per application."""
    auth.require_session(request)
    if len(body.events) > 5000:
        raise HTTPException(400, "too many events")
    names = {f.name for f in fields(Event)}
    try:
        events = [Event(**{k: v for k, v in e.items() if k in names}) for e in body.events]
    except TypeError:
        raise HTTPException(400, "bad event") from None
    rows = build_applications(events)
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"updated_at": time.time(), "counts": counts, "applications": rows}


# Keep this LAST: the mount answers every path, so routes defined after it would never be reached.
# Docker / local single-server mode: serve the built React app too. On Vercel the static files
# come from the CDN and WEB_DIST is not set, so this does nothing there.
if settings.WEB_DIST and os.path.isdir(settings.WEB_DIST):
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=settings.WEB_DIST, html=True), name="web")
