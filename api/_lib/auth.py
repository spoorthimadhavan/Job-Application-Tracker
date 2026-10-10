"""Google sign-in and an encrypted cookie session (no database needed)."""

import json
import secrets
import time
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, Request

from . import settings

_f = Fernet(settings.FERNET_KEY)
COOKIE = "jt_session"
STATE_COOKIE = "jt_state"
SCOPES = "openid email https://www.googleapis.com/auth/gmail.readonly"


def seal(data: dict) -> str:
    return _f.encrypt(json.dumps(data).encode()).decode()


def unseal(token: str | None) -> dict | None:
    if not token:
        return None
    try:
        return json.loads(_f.decrypt(token.encode()))
    except (InvalidToken, ValueError):
        return None


def session(request: Request) -> dict | None:
    return unseal(request.cookies.get(COOKIE))


def require_session(request: Request) -> dict:
    s = session(request)
    if not s:
        raise HTTPException(401, "Not signed in")
    return s


def redirect_uri(request: Request) -> str:
    if settings.REDIRECT_URI:
        return settings.REDIRECT_URI
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    proto = request.headers.get("x-forwarded-proto", "https" if "localhost" not in host else "http")
    return f"{proto}://{host}/api/auth/callback"


def login_url(request: Request, state: str) -> str:
    q = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri(request),
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(q)


async def exchange_code(request: Request, code: str) -> dict:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri(request),
                "grant_type": "authorization_code",
            },
        )
        r.raise_for_status()
        tok = r.json()
        u = await c.get("https://openidconnect.googleapis.com/v1/userinfo", headers={"Authorization": f"Bearer {tok['access_token']}"})
        u.raise_for_status()
    return {
        "email": u.json()["email"],
        "refresh_token": tok.get("refresh_token"),
        "access_token": tok["access_token"],
        "exp": time.time() + tok.get("expires_in", 3000),
    }


async def access_token(s: dict) -> str:
    if s.get("access_token") and s.get("exp", 0) > time.time() + 60:
        return s["access_token"]
    if not s.get("refresh_token"):
        raise HTTPException(401, "Sign in again")
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": s["refresh_token"],
                "grant_type": "refresh_token",
            },
        )
    if r.status_code != 200:
        raise HTTPException(401, "Google access expired, sign in again")
    tok = r.json()
    s["access_token"], s["exp"] = tok["access_token"], time.time() + tok.get("expires_in", 3000)
    return s["access_token"]


def new_state() -> str:
    return secrets.token_urlsafe(24)
