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
    r"move (forward|ahead) with other|moving (forward|ahead) with other|chosen to move ahead|pursue other (candidates|applicants)|"
    r"not (been )?selected|not be (proceeding|moving)|not shortlisted|position (has been|was) filled|not successful|"
    r"nicht in die engere|haben uns für (einen )?andere|anderen (bewerber|kandidat)|nicht berücksichtigt|konnte (ihre|deine) bewerbung|"
    r"nicht weiter(verfolgen|geführt)|müssen wir (ihnen|dir) (leider )?mitteilen",
    re.I,
)
INTERVIEW = re.compile(
    r"vorstellungsgespräch|kennenlerngespräch|einladung zum (gespräch|interview|telefoninterview)|"
    r"(invite|inviting|invitation).{0,40}(interview|call|chat|assessment)|"
    r"(schedule|book|arrange).{0,30}interview|interview (invitation|invite|request|slot|appointment)|"
    r"technical (assessment|interview)|coding (challenge|test)|take-home|terminvorschlag|"
    r"nächsten schritt.{0,40}(gespräch|call|interview)",
    re.I,
)
RECEIPT = re.compile(
    r"application was sent|thank you.{0,20}for applying|for applying (for|to) the|thank you for (your )?appl|thanks for appl|"
    r"vielen dank für (ihre|deine) bewerbung|"
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
NOISE_SENDER = re.compile(
    r"jobalerts|jobagent|match\.indeed|newsletter|marketing|nebenan|news@|promo|"
    r"lists?\.|-request@|mailman|noreply@github|notifications@(vercel|github)|glassdoor|wearedevelopers|"
    r"interviewcake|tryexponent|techprep|codemia|kajabi|scienceofpeople|unstop|lieferando|bajajfinance",
    re.I,
)
# Training / career-course sales ("Thanks for applying to our program") are not job applications
EDU_SENDER = re.compile(r"cybersteps|dsinstitute|stackfuel|edvalo|weiterbildung|startplatz|bootcamp|academy|akademie|institut", re.I)
EDU = re.compile(
    r"weiterbildung|bildungsgutschein|umschulung|bootcamp|training (program|course)|our (\w+ )?program|"
    r"career coach|karrierebegleitung|karriere-?coach|azav|agentur für arbeit|bundesagentur|webinar|masterclass|curriculum|"
    r"telefontermin|kompetenzanalyse|online-rundgang",
    re.I,
)
NOISE_SUBJECT = re.compile(r"digest|weekly problem|unsubscribe|webinar|your .{0,20}voucher|discount", re.I)
# Mail folders Gmail itself files as not-personal
SKIP_LABELS = {"SENT", "DRAFT", "SPAM", "TRASH"}
BULK_LABELS = {"CATEGORY_PROMOTIONS", "CATEGORY_FORUMS", "CATEGORY_SOCIAL"}
PERSONAL_APPLICATION = re.compile(
    r"(your|ihre|ihr|deine|dein)\s+(application|bewerbung|candidacy|candidature)|"
    r"application\s+(for|to|as|status|was|has|process)|bewerbung\s+(als|auf|bei|für|zur|ist|wurde)|"
    r"(thank you|thanks|danke).{0,20}(applying|application|bewerbung|interesse)",
    re.I,
)
# The mail must talk about an application / position, not just mention a keyword
APPLICATION_CONTEXT = re.compile(
    r"(your|ihre|ihr|deine|dein)\s+(application|bewerbung|candidacy|candidature)|"
    r"application\s+(for|to|as|status|was|has|process|materials)|bewerbung\s+(als|auf|bei|für|zur|ist|wurde)|"
    r"(applying|applied)\s+(for|to)|position|\bstelle\b|vacanc|\brole\s+(of|at)\b|junior|senior|engineer|developer|entwickler",
    re.I,
)


# Bump when the rules change: browsers keep classified mail and drop it when this differs.
RULES_VERSION = "2026-10-11b"


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
    sender: str = ""
    snippet: str = ""


def _clean(t: str | None) -> str:
    return html.unescape(t or "").strip()


def _sender_display(sender: str) -> str:
    name = re.match(r'\s*"?([^"<]+?)"?\s*<', html.unescape(sender or ""))
    if name and name.group(1).strip():
        return name.group(1).strip()
    addr = re.search(r"[^<\s]+@[^>\s]+", sender or "")
    return addr.group(0) if addr else (sender or "").strip()


ROLE_PATTERNS = (
    r"interest in the\s+(.+?)\s+(?:position|role)\b",
    r"position als\s+(.+?)\s+(?:in|bei|am|im)\s",
    r"following role:\s*(.+?)\s+\d{6,}",
    r"bewerbung als\s+(.+?)\s+\d{6,}\s+bekommen",
    r"(?:applying|applied) for the\s+(.+?)\s+position",
    r"(?:auf die )?stelle(?: als)?\s+(.+?)\s+(?:bei|in|im)\s",
    r"bewerbung\s+(?:als|für die position|für)\s+(.+?)(?:\s+(?:bei|in)\s|[.,]|$)",
    r"application (?:for|as)(?: the)?\s+(.+?)(?:\s+(?:at|with|position|role)\b|[.,]|$)",
    r"(?:for|as) the\s+(.+?)\s+(?:position|role)\b",
    r"role of\s+(.+?)\s+(?:with|at)\b",
    r"bewerbung als\s+(.+?)(?:\s+(?:bei|in|am|im|für)\b|\s+(?:erhalten|bekommen|eingegangen)\b|[!.,]|$)",
    r"applying (?:to|for) the\s+(.+?)(?:\s+(?:position|role|at|here)\b|[.!]|$)",
    r"position as(?: an?)?\s+(.+?)(?:\s+(?:at|with)\b|[.!,]|$)",
)
JUNK_ROLE = re.compile(
    r"^(als|as|soon|applying|your|dein|ihre?|for|für|the|a)\b|as possible|erhalten|freuen|speak to|interest|interesse|thank|danke|!|^\W*$",
    re.I,
)


SUBJECT_ROLE_PATTERNS = (
    r"(?:auf )?die stelle[\s\-:–]*[\"„“]?(.+?)[\"“”]?\s*$",
    r"bewerbung (?:auf|für) (?:die |den )?(?:position|stelle)?[\s\-:–]*[\"„“]?(.+?)[\"“”]?\s*$",
)


def _role(subject: str, snippet: str = "") -> str:
    for pat in SUBJECT_ROLE_PATTERNS:
        if (x := re.search(pat, subject, re.I)) and 2 < len(r := x[1].strip(' .,:;-"')) <= 90 and not JUNK_ROLE.search(r):
            return r
    # specific patterns first, across both texts, so "Danke für dein Interesse" in a subject never beats the role in the body
    for pat in ROLE_PATTERNS:
        for text in (subject, snippet):
            if x := re.search(pat, text, re.I):
                r = re.sub(r"\s+\d{6,}$", "", x[1].strip(" .,:;-…"))
                if 2 < len(r) <= 90 and not JUNK_ROLE.search(r):
                    return r
    return "Application"


def _day(m: dict) -> str:
    d = (m.get("date") or "")[:10]
    try:
        datetime.fromisoformat(d)
        return d
    except ValueError:  # a mail with no usable date must never break the list
        return datetime.now(UTC).date().isoformat()


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


FREE_MAIL = {"gmail", "googlemail", "outlook", "hotmail", "yahoo", "gmx", "web", "icloud", "t-online", "live", "proton", "protonmail"}
COMPANY_WORDS = re.compile(
    r"\b(group|team|hr|gmbh|ag|se|inc|ltd|llc|jobs|careers?|recruit\w*|karriere|consulting|solutions|systems|services|bank|holding|media|health|labs?|"
    r"software|technologies|digital|partners|talent|people|culture)\b",
    re.I,
)
PERSON = re.compile(r"[A-ZÄÖÜ][a-zäöüß'’-]+(?: [A-ZÄÖÜ][a-zäöüß'’-]+){1,2}")


def _sender_parts(sender: str) -> tuple[str, str, str]:
    sender = html.unescape(sender or "")
    n = re.match(r'\s*"?([^"<]+?)"?\s*<', sender)
    a = re.search(r"([^<\s@]+)@([^>\s]+)", sender)
    return (n.group(1).strip() if n else ""), (a[1] if a else ""), (a[2].lower() if a else "")


def _domain_company(dom: str) -> str:
    parts = [p for p in dom.split(".")[:-1] if p not in SUBDOMAINS]
    base = parts[-1] if parts else dom
    base = re.sub(r"(hq|jobs|careers|recruiting)$", "", base) or base
    return base.title()


def _company_from_text(text: str) -> str:
    for pat in (
        r"(?:position|role|stelle)\b.{0,80}?\b(?:at|bei(?: der| dem)?)\s+([A-Z][\w&.\- ]{1,40}?)(?:[.,!]|\s+(?:We|Wir|and|und)\b|$)",
        r"interest in ([A-Z][\w&.\-]+)!",
    ):
        if x := re.search(pat, text):
            return x[1].strip()
    return ""


def _company_from_sender(sender: str, subject: str = "", text: str = "") -> str:
    name, local, dom = _sender_parts(sender)
    # "Packmatic | Your Application", "Bridger I Update on your process": the company is the prefix
    if x := re.match(r"\s*([A-Z][\w&.\-]*(?: [A-Z][\w&.\-]*){0,2})\s+[|I]\s+\S", subject):
        return x[1]
    base = dom.split(".")[:-1]
    base = [p for p in base if p not in SUBDOMAINS]
    key = base[-1] if base else dom
    ats_or_free = key in ATS or key in FREE_MAIL
    personish = bool(name) and bool(PERSON.fullmatch(name)) and not COMPANY_WORDS.search(name)
    if personish:
        # a person's name is the sender, not the company
        if not ats_or_free:
            nn, nd = _norm(name), _norm(key)
            if nn not in nd and nd not in nn:
                return _domain_company(dom)
        elif found := _company_from_text(f"{subject} {text}"):
            return found
    if name:
        n = re.sub(r"\s+", " ", GENERIC.sub("", name)).strip(" -|,.")
        if len(n) > 1:
            return n
    if key in ATS:
        key = GENERIC.sub("", re.sub(r"[-_.]", " ", local)).strip() or key
    return key.strip().title()


def classify_message(m: dict) -> Event | None:
    subject, snippet = _clean(m.get("subject")), _clean(m.get("snippet"))
    sender = m.get("sender") or ""
    low = sender.lower()
    mid, day = m.get("id", ""), _day(m)

    preview = _clean(m.get("preview")) or snippet

    def ev(company, role, status, note, source, check=False):
        return Event(company.strip(" ."), role.strip(), status, day, note, check, mid, source, subject, _sender_display(sender), preview[:240])

    labels = set(m.get("labels") or [])
    if labels & SKIP_LABELS:  # your own sent mail, drafts, spam
        return None
    if NOISE_SENDER.search(low) or NOISE.search(subject) or NOISE_SUBJECT.search(subject):
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
                return ev(x[1], _role("", snippet), "R", "Indeed rejection email.", "indeed")
            if INTERVIEW.search(snippet):
                return ev(x[1], _role("", snippet), "S", "Indeed: next step.", "indeed")
            return ev(x[1], _role("", snippet), "U", "Indeed update, open the email for the decision.", "indeed", True)
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
    if EDU_SENDER.search(low) or EDU.search(blob):
        return None
    context = APPLICATION_CONTEXT.search(blob)
    # Job mail often lands in Promotions/Updates/Social, so those tabs are scanned too, but only a
    # clear statement about *your* application counts there (not "senior engineer" in a newsletter)
    if labels & BULK_LABELS and not PERSONAL_APPLICATION.search(blob):
        return None
    company = _company_from_sender(sender, subject, snippet)
    role = _role(subject, snippet)
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


LOOSE_APPLICATION = re.compile(r"bewerbung|application|candidacy|candidature|applying", re.I)


PLAIN_CONFIRMATION = re.compile(
    r"eingegangen|eingangsbestätigung|received your (application|resume|cv)|we.ve received|erhalten haben|"
    r"gerade haben wir (deine|ihre)|successfully (submitted|applied)|just received your",
    re.I,
)


def needs_body(m: dict) -> bool:
    """True when the preview alone cannot give the verdict, so the mail body should be read."""
    sender, subject = (m.get("sender") or "").lower(), _clean(m.get("subject"))
    blob = f"{subject} {_clean(m.get('snippet'))}"
    if "linkedin.com" in sender or set(m.get("labels") or []) & SKIP_LABELS:
        return False
    if NOISE_SENDER.search(sender) or NOISE.search(subject) or NOISE_SUBJECT.search(subject) or EDU_SENDER.search(sender) or EDU.search(blob):
        return False
    ev = classify_message(m)
    if ev and ev.status not in ("A", "U"):
        return False
    if ev and ev.source == "email" and PLAIN_CONFIRMATION.search(blob):
        return False  # "we received your application": nothing more in the body that changes the status
    return bool(LOOSE_APPLICATION.search(blob))


GENERIC_ROLES = {"application", "linkedin application", "role not named", ""}


def _rolekey(role: str) -> str:
    return re.sub(r"[^a-z0-9]", "", re.sub(r"\(.*?\)", "", role.lower()))


def _group(evs: list[Event]) -> list[tuple[str, list[Event]]]:
    """One application per company and role. Mails that name no role join the matching role's group."""
    specific = [e for e in evs if e.role.lower() not in GENERIC_ROLES]
    generic = [e for e in evs if e.role.lower() in GENERIC_ROLES]
    groups: list[list] = []  # [rolekey, events]
    for e in specific:
        k = _rolekey(e.role)
        hit = next((g for g in groups if g[0] == k or (min(len(g[0]), len(k)) >= 6 and (g[0] in k or k in g[0]))), None)
        if hit:
            hit[1].append(e)
        else:
            groups.append([k, [e]])
    if not groups:
        return [("", generic)] if generic else []
    for e in generic:
        before = [g for g in groups if min(x.date for x in g[1]) <= e.date]
        target = max(before, key=lambda g: min(x.date for x in g[1])) if before else min(groups, key=lambda g: min(x.date for x in g[1]))
        target[1].append(e)
    return [(g[0], g[1]) for g in groups]


def build_applications(events: list[Event], now: datetime | None = None) -> list[dict]:
    """Group events per company (per role for StepStone, which hides the company)."""
    now = now or datetime.now(UTC)
    by_company: dict[str, list[Event]] = {}
    for e in events:
        k = _norm(e.company)
        # "OH-SO" and "OH-SO Digital" are the same employer: a key that starts another (4+ chars) joins it
        same = next((x for x in by_company if x != k and min(len(x), len(k)) >= 4 and (x.startswith(k) or k.startswith(x))), None)
        if same and len(k) < len(same):
            by_company[k] = by_company.pop(same)
        elif same:
            k = same
        by_company.setdefault(k, []).append(e)
    groups: list[tuple[str, list[Event]]] = []
    for ckey, cevs in by_company.items():
        for rk, evs in _group(cevs):
            groups.append((f"{ckey}|{rk}" if rk else ckey, evs))

    rows = []
    for key, evs in groups:
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
        if status == "S":
            age = (now - datetime.fromisoformat(last.date).replace(tzinfo=UTC)).days
            if age > NO_RESPONSE_DAYS:  # interview or next step, then silence
                status, note = "N", "Interview or next step, then no reply for more than " + f"{NO_RESPONSE_DAYS // 7} weeks."
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
                "sender": last.sender,
                "preview": last.snippet,
                "events": [{k: v for k, v in asdict(e).items() if k in ("status", "date", "subject", "message_id", "source")} for e in reversed(evs)],
            }
        )
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows
