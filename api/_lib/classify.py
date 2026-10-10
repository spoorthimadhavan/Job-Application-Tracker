"""Turns raw email metadata into job-application events, then into one row per application.

Rule based on purpose: the emails come from a handful of templates (LinkedIn, Indeed,
StepStone, applicant systems), so rules are exact, fast, free and easy to test.
Statuses: S selected, U under review, A applied, N rejected (no response),
R rejected, I rejected after interview, C account created, not applied.
"""

from __future__ import annotations

import hashlib
import html
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from .settings import NO_RESPONSE_DAYS

REJECT = re.compile(
    r"leider|unfortunately|regret|not (be )?mov(e|ing) forward|other candidates|andere bewerber|"
    r"absage|nicht berücksichtigen|decided not to|will not move you|didn.t make it|"
    r"nicht weiter(verfolgen|geführt)|müssen wir (ihnen|dir) (leider )?mitteilen",
    re.I,
)
INTERVIEW = re.compile(
    r"interview|vorstellungsgespräch|kennenlerngespräch|einladung zum gespräch|assessment|"
    r"terminvorschlag|next step|nächsten schritt.*(gespräch|call)|invite you to",
    re.I,
)
RECEIPT = re.compile(
    r"application was sent|thank you for (your )?appl|thanks for appl|vielen dank für (ihre|deine) bewerbung|"
    r"eingangsbestätigung|we received your application|has been sent|bewerbung (ist )?eingegangen|"
    r"we.ve received your application|danke für dein interesse",
    re.I,
)
ACCOUNT = re.compile(r"account (wurde )?(erfolgreich )?(erstellt|created)|one-time passcode|konto.*erstellt", re.I)
NOISE = re.compile(
    r"looking for candidates|job opportunities|is hiring|new jobs|job alert|newsletter|"
    r"similar to|expiring|recommended|saved jobs|could be a match|jetzt bewerben|top choice",
    re.I,
)
NOISE_SENDER = re.compile(r"jobalerts|jobagent|match\.indeed|newsletter|marketing|nebenan|news@|promo", re.I)


@dataclass
class Event:
    company: str
    role: str
    status: str
    date: str  # YYYY-MM-DD
    note: str
    check: bool
    message_id: str
    source: str
    subject: str


def _clean(t: str | None) -> str:
    return html.unescape(t or "").strip()


def _day(m: dict) -> str:
    return (m.get("date") or "")[:10]


GENERIC = re.compile(
    r"\b(no.?reply|do.?not.?reply|jobs?|talent|career site|careers?|recruit(ing|ment|er)?|hr|team|karriere|bewerbung(en)?|notifications?)\b", re.I
)
ATS = {
    "personio",
    "lever",
    "smartrecruiters",
    "join",
    "icims",
    "ashbyhq",
    "successfactors",
    "greenhouse",
    "workable",
    "recruitee",
    "teamtailor",
    "softgarden",
    "d-vinci",
}
SUBDOMAINS = {"m", "mail", "email", "info", "jobs", "e", "msg", "talent", "hire", "notifications", "mg", "em"}


def _company_from_sender(sender: str) -> str:
    name = re.match(r'\s*"?([^"<]+?)"?\s*<', sender)
    if name:
        n = re.sub(r"\s+", " ", GENERIC.sub("", name.group(1))).strip(" -|,.")
        if len(n) > 1:
            return n
    addr = re.search(r"([^<\s@]+)@([^>\s]+)", sender)
    local, dom = (addr[1], addr[2]) if addr else ("", sender)
    parts = [p for p in dom.lower().split(".")[:-1] if p not in SUBDOMAINS]
    base = parts[-1] if parts else dom
    if base in ATS:
        base = GENERIC.sub("", re.sub(r"[-_.]", " ", local)).strip() or base
    return base.strip().title()


def classify_message(m: dict) -> Event | None:
    subject, snippet = _clean(m.get("subject")), _clean(m.get("snippet"))
    sender = m.get("sender") or ""
    low = sender.lower()
    mid, day = m.get("id", ""), _day(m)

    def ev(company, role, status, note, source, check=False):
        return Event(company.strip(" ."), role.strip(), status, day, note, check, mid, source, subject)

    if NOISE_SENDER.search(low) or NOISE.search(subject):
        return None

    if "linkedin.com" in low:
        if x := re.match(r"Your application to (.+?)\s+at\s+(.+)$", subject):
            return ev(x[2], x[1], "R", "LinkedIn rejection email.", "linkedin")
        if x := re.search(r"your application was sent to (.+)$", subject, re.I):
            return ev(x[1], "LinkedIn application", "A", "LinkedIn.", "linkedin")
        if x := re.search(r"your application was viewed by (.+)$", subject, re.I):
            return ev(x[1], "LinkedIn application", "U", "LinkedIn: your application was viewed.", "linkedin")
        return None

    if "indeed" in low:
        if x := re.search(r"Neuigkeiten zu Ihrer Bewerbung von (.+)$", subject):
            if REJECT.search(snippet):
                return ev(x[1], "Application", "R", "Indeed rejection email.", "indeed")
            if INTERVIEW.search(snippet):
                return ev(x[1], "Application", "S", "Indeed: next step.", "indeed")
            return ev(x[1], "Application", "U", "Indeed update, open the email for the decision.", "indeed", True)
        return None

    if "stepstone" in low:
        if x := re.search(r"there.s news about your application for (.+)$", subject, re.I):
            st = "R" if re.search(r"processed|didn.t make it|unfortunately", snippet, re.I) else "U"
            return ev("Via StepStone", x[1], st, "StepStone update, open the email for the decision.", "stepstone", st == "U")
        if x := re.search(r"your application for (.+?) has been sent", subject, re.I):
            return ev("Via StepStone", x[1], "A", "StepStone. Company not shown.", "stepstone")
        if x := re.search(r"Ihre Bewerbung bei (.+?) wurde angesehen", subject):
            return ev(x[1], "Application", "U", "StepStone: your application was viewed.", "stepstone")
        if x := re.search(r"Update on your application for the role of (.+?) with (.+)$", subject):
            return ev(x[2], x[1], "R" if REJECT.search(snippet) else "U", "StepStone feedback.", "stepstone", True)
        return None

    blob = f"{subject} {snippet}"
    context = re.search(r"bewerbung|application|candidacy|position|stelle|role", blob, re.I)
    company = _company_from_sender(sender)
    role = (re.search(r"(?:als|for|für)\s+(?:the\s+)?(.+?)(?:\s+(?:bei|at|position|role)\b|$)", subject, re.I) or [None, "Application"])[1]
    role = role[:90]
    if context and REJECT.search(snippet):
        return ev(company, role, "R", "Rejection email.", "email", True)
    if context and INTERVIEW.search(blob):
        return ev(company, role, "S", "Interview or next-step invite.", "email", True)
    if RECEIPT.search(blob):
        return ev(company, role, "A", "Receipt.", "email")
    if ACCOUNT.search(blob):
        return ev(company, "Role not named", "C", "Account created, application not sent.", "email")
    return None


def _norm(t: str) -> str:
    t = re.sub(r"\b(gmbh|ag|se|kg|co|inc|ltd|mbh)\b", "", t.lower())
    return re.sub(r"[^a-z0-9]", "", t)


def build_applications(events: list[Event], now: datetime | None = None) -> list[dict]:
    """Group events per company (per role for StepStone, which hides the company)."""
    now = now or datetime.now(UTC)
    groups: dict[str, list[Event]] = {}
    for e in events:
        key = _norm(e.company) + ("|" + _norm(e.role) if e.company == "Via StepStone" else "")
        groups.setdefault(key, []).append(e)

    rows = []
    for key, evs in groups.items():
        evs.sort(key=lambda e: (e.date, e.message_id))
        status, last = "", evs[0]
        seen_interview = False
        for e in evs:
            if e.status == "C" and status:
                continue
            if e.status == "A" and status in ("R", "I"):
                status = "A"  # applied again later
            elif e.status == "A" and status in ("U", "S"):
                pass
            elif e.status == "R" and (seen_interview or status == "S"):
                status = "I"
            elif e.status == "U" and status in ("R", "I", "S"):
                pass
            else:
                status = e.status
            if e.status == "S":
                seen_interview = True
            last = e
        note = last.note
        if status == "A":
            age = (now - datetime.fromisoformat(last.date).replace(tzinfo=UTC)).days
            if age > NO_RESPONSE_DAYS:
                status, note = "N", (note + " " if note else "") + f"No response after more than {NO_RESPONSE_DAYS // 7} weeks."
        company = max((e.company for e in evs), key=len)
        rows.append(
            {
                "id": hashlib.sha1(key.encode()).hexdigest()[:12],
                "company": company,
                "role": last.role if last.role != "Application" else next((e.role for e in reversed(evs) if e.role != "Application"), "Application"),
                "status": status,
                "date": last.date,
                "note": note,
                "check": last.check and status in ("R", "U", "S", "I"),
                "source": last.source,
                "events": [{k: v for k, v in asdict(e).items() if k in ("status", "date", "subject", "message_id", "source")} for e in reversed(evs)],
            }
        )
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows
