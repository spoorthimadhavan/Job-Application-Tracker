"""Made-up mailbox so the app can be tried without Google keys. Goes through the real classifier."""

from datetime import UTC, datetime, timedelta

_now = datetime.now(UTC)


def _d(days):
    return (_now - timedelta(days=days)).isoformat()


_LI = "LinkedIn <jobs-noreply@linkedin.com>"
MESSAGES = [
    {
        "id": "d0000001",
        "sender": _LI,
        "subject": "Spoorthi, your application was sent to Northwind Labs",
        "snippet": "Your application was sent",
        "date": _d(5),
    },
    {
        "id": "d0000002",
        "sender": _LI,
        "subject": "Your application was viewed by Fabrikam Digital",
        "snippet": "Fabrikam viewed your application",
        "date": _d(9),
    },
    {
        "id": "d0000003",
        "sender": _LI,
        "subject": "Your application to Frontend Developer React at Contoso",
        "snippet": "Thank you for your interest",
        "date": _d(20),
    },
    {
        "id": "d0000004",
        "sender": "Indeed <noreply@indeed.com>",
        "subject": "Neuigkeiten zu Ihrer Bewerbung von Muster Solar GmbH",
        "snippet": "Leider konnte Ihre Bewerbung dieses Mal nicht berücksichtigt werden",
        "date": _d(14),
    },
    {
        "id": "d0000005",
        "sender": "StepStone <info@email.stepstone.de>",
        "subject": "Alex, there's news about your application for Web Developer (m/w/d)",
        "snippet": "A company has processed your application",
        "date": _d(30),
    },
    {
        "id": "d0000006",
        "sender": "Adventure Works Recruiting <jobs@m.personio.de>",
        "subject": "Interview invitation: Backend Engineer",
        "snippet": "We would like to invite you to an interview about your application",
        "date": _d(25),
    },
    {
        "id": "d0000007",
        "sender": "Adventure Works Recruiting <jobs@m.personio.de>",
        "subject": "Your application at Adventure Works",
        "snippet": "Unfortunately we will not move forward with your application",
        "date": _d(12),
    },
    {
        "id": "d0000008",
        "sender": _LI,
        "subject": "Spoorthi, your application was sent to Tailspin Toys",
        "snippet": "Your application was sent",
        "date": _d(70),
    },
    {
        "id": "d0000009",
        "sender": "Wide World <careers@wideworld.com>",
        "subject": "Interview invitation for Platform Engineer",
        "snippet": "We would like to invite you to an interview for the position",
        "date": _d(3),
    },
    {
        "id": "d0000010",
        "sender": "Globex Career Site <DoNotReply@globex.com>",
        "subject": "Ihr Account wurde erfolgreich erstellt",
        "snippet": "Ihr Account wurde erfolgreich erstellt",
        "date": _d(8),
    },
    {
        "id": "d0000011",
        "sender": "info@jobagent.stepstone.de",
        "subject": "Acme and 4 other companies are looking for candidates like you",
        "snippet": "Don't miss out",
        "date": _d(1),
    },
]


def body(msg_id: str) -> dict | None:
    for m in MESSAGES:
        if m["id"] == msg_id:
            html = (
                f"<div style='font-family:system-ui,sans-serif;max-width:560px;padding:16px'>"
                f"<h3>{m['subject']}</h3><p>{m['snippet']}.</p>"
                f"<p style='color:#666'>Demo email. Sign in with Google to see your real mail.</p></div>"
            )
            return {"id": msg_id, "subject": m["subject"], "from": m["sender"], "date": m["date"], "html": html, "text": m["snippet"], "gmail_url": None}
    return None
