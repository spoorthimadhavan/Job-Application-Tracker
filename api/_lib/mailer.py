"""Welcome email through Resend's HTTP API. Never raises: a mail problem must not block sign-in."""

from __future__ import annotations

import html
import logging

import httpx

from . import settings

log = logging.getLogger("jobtracker.mail")
WELCOME_COOKIE = "jt_welcomed"


def welcome_message(to: str) -> dict:
    safe = html.escape(to)
    return {
        "from": settings.MAIL_FROM,
        "to": [to],
        "subject": "Welcome to Job Application Tracker",
        "text": (
            f"Hi,\n\nYou just signed in to Job Application Tracker with {to}.\n"
            "The app reads your job emails (read-only) and keeps one live list of your applications.\n"
            "Nothing is stored on our server.\n\nIf this wasn't you, revoke access at https://myaccount.google.com/permissions\n"
        ),
        "html": (
            f"<p>Hi,</p><p>You just signed in to <b>Job Application Tracker</b> with {safe}.</p>"
            "<p>The app reads your job emails (read-only) and keeps one live list of your applications. Nothing is stored on our server.</p>"
            '<p style="color:#666">If this wasn\'t you, revoke access at '
            '<a href="https://myaccount.google.com/permissions">myaccount.google.com/permissions</a>.</p>'
        ),
    }


async def send_welcome(to: str) -> bool:
    if not settings.RESEND_API_KEY or not to:
        return False
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.post("https://api.resend.com/emails", headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"}, json=welcome_message(to))
        if r.status_code >= 300:
            log.warning("Resend rejected the welcome email: %s", r.status_code)
            return False
        return True
    except Exception:  # network, DNS, timeout: sign-in still succeeds
        log.warning("Welcome email failed", exc_info=True)
        return False
