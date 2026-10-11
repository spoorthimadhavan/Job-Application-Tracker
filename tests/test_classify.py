import pathlib
import sys
from datetime import UTC, datetime

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "api"))
from _lib.classify import build_applications, classify_message

NOW = datetime(2026, 10, 10, tzinfo=UTC)


def m(sender, subject, snippet="", date="2026-10-01", id="1"):
    return {"id": id, "sender": sender, "subject": subject, "snippet": snippet, "date": date}


def test_linkedin_rejection_template():
    e = classify_message(m("jobs-noreply@linkedin.com", "Your application to Software developer C# (w/m/d) at Schotstek GmbH"))
    assert (e.status, e.company, e.role) == ("R", "Schotstek GmbH", "Software developer C# (w/m/d)")


def test_linkedin_sent_and_viewed():
    assert classify_message(m("jobs-noreply@linkedin.com", "Spoorthi, your application was sent to PRIOjet GmbH")).status == "A"
    assert classify_message(m("jobs-noreply@linkedin.com", "Your application was viewed by BoWatt")).status == "U"


def test_indeed_rejection_vs_open():
    r = classify_message(m("noreply@indeed.com", "Neuigkeiten zu Ihrer Bewerbung von Rhino Solar GmbH", "Leider konnte Ihre Bewerbung"))
    assert r.status == "R"
    u = classify_message(m("noreply@indeed.com", "Neuigkeiten zu Ihrer Bewerbung von X GmbH", "hat den nächsten Schritt eingeleitet"))
    assert u.status == "U" and u.check


def test_company_rejection_mail():
    e = classify_message(
        m("SpotmyEnergy <spotmyenergy-jobs@m.personio.de>", "Deine Bewerbung bei SpotmyEnergy", "Leider haben wir uns für andere Bewerber entschieden")
    )
    assert e.status == "R"


def test_noise_is_ignored():
    assert classify_message(m("info@jobagent.stepstone.de", "ProcuVia AG and 4 other companies are looking for candidates like you")) is None
    assert classify_message(m("donotreply@match.indeed.com", "Frontend @ dxm", "could be a match for this role")) is None
    assert classify_message(m("hello@shop.de", "10% Rabatt", "Sale")) is None


def test_interview_then_reject_is_I():
    evs = [
        classify_message(m("jobs@amazon.jobs", "Interview invitation for your application", "invite you to interview", "2026-06-01", "a")),
        classify_message(m("jobs@amazon.jobs", "Your application", "Unfortunately we will not move forward with your application", "2026-06-20", "b")),
    ]
    rows = build_applications([e for e in evs if e], NOW)
    assert len(rows) == 1 and rows[0]["status"] == "I"


def test_applied_turns_no_response_after_six_weeks():
    old = classify_message(m("jobs-noreply@linkedin.com", "Your application was sent to OldCo", date="2026-08-01", id="x"))
    new = classify_message(m("jobs-noreply@linkedin.com", "Your application was sent to NewCo", date="2026-10-01", id="y"))
    rows = {r["company"]: r["status"] for r in build_applications([old, new], NOW)}
    assert rows == {"OldCo": "N", "NewCo": "A"}


def test_rejection_beats_earlier_receipt():
    a = classify_message(m("jobs-noreply@linkedin.com", "Your application was sent to Hays", date="2026-07-01", id="1"))
    r = classify_message(m("jobs-noreply@linkedin.com", "Your application to Engineer at Hays", date="2026-07-12", id="2"))
    rows = build_applications([a, r], NOW)
    assert len(rows) == 1 and rows[0]["status"] == "R" and len(rows[0]["events"]) == 2


def test_stepstone_templates():
    sent = classify_message(m("StepStone <info@email.stepstone.de>", "Spoorthi, your application for FullStack Developer (m/f/d) has been sent"))
    assert (sent.status, sent.company) == ("A", "Via StepStone")
    viewed = classify_message(m("info@email.stepstone.de", "Ihre Bewerbung bei TorAlarm GmbH wurde angesehen"))
    assert (viewed.status, viewed.company) == ("U", "TorAlarm GmbH")
    news = classify_message(
        m("info@email.stepstone.de", "Spoorthi, there's news about your application for Web Frontend Developer (m/w/d)", "KM2 has processed your application")
    )
    assert news.status == "R"


def test_account_created_is_C_and_ignored_when_applied():
    acc = classify_message(m("Globex <DoNotReply@globex.com>", "Ihr Account wurde erfolgreich erstellt", date="2026-09-01", id="a"))
    assert acc.status == "C"
    rec = classify_message(m("Globex <DoNotReply@globex.com>", "Eingangsbestätigung Ihrer Bewerbung bei Globex", date="2026-09-02", id="b"))
    rows = build_applications([acc, rec], NOW)
    assert len(rows) == 1 and rows[0]["status"] == "A"


def test_viewed_does_not_overwrite_rejection():
    r = classify_message(m("jobs-noreply@linkedin.com", "Your application to Dev at Foo", date="2026-09-01", id="1"))
    v = classify_message(m("jobs-noreply@linkedin.com", "Your application was viewed by Foo", date="2026-09-05", id="2"))
    assert build_applications([r, v], NOW)[0]["status"] == "R"


def test_reapplying_after_rejection_is_applied_again():
    r = classify_message(m("jobs-noreply@linkedin.com", "Your application to Dev at Foo", date="2026-07-01", id="1"))
    a = classify_message(m("jobs-noreply@linkedin.com", "Your application was sent to Foo", date="2026-10-05", id="2"))
    assert build_applications([r, a], NOW)[0]["status"] == "A"


def test_company_names_from_senders():
    from _lib.classify import _company_from_sender as f

    assert f("Adventure Works Recruiting <jobs@m.personio.de>") == "Adventure Works"
    assert f("SpotmyEnergy <spotmyenergy-jobs@m.personio.de>") == "SpotmyEnergy"
    assert f("olga@nortal.com") == "Nortal"


def test_exactly_six_weeks_is_still_applied():
    from datetime import timedelta

    d = (NOW - timedelta(days=42)).date().isoformat()
    e = classify_message(m("jobs-noreply@linkedin.com", "Your application was sent to Edge", date=d))
    assert build_applications([e], NOW)[0]["status"] == "A"
    d2 = (NOW - timedelta(days=43)).date().isoformat()
    e2 = classify_message(m("jobs-noreply@linkedin.com", "Your application was sent to Edge", date=d2))
    assert build_applications([e2], NOW)[0]["status"] == "N"


def ml(sender, subject, snippet="", labels=()):
    return {**m(sender, subject, snippet), "labels": list(labels)}


def test_sent_drafts_and_spam_labels_ignored():
    for label in ("SENT", "DRAFT", "SPAM", "TRASH"):
        assert classify_message(ml("me@x.com", "Application for Software Engineer", "your application", [label])) is None


def test_promotions_and_forums_ignored():
    for label in ("CATEGORY_PROMOTIONS", "CATEGORY_FORUMS", "CATEGORY_SOCIAL"):
        assert classify_message(ml("hr@acme.com", "Your application for Developer", "thanks for applying", [label])) is None


def test_training_sales_ignored():
    assert classify_message(m("team@cybersteps.de", "Thanks for applying to our Cybersecurity Program", "your application")) is None
    assert classify_message(m("hello@someinstitut.de", "Bewerbung als Entwickler: Bildungsgutschein", "Weiterbildung mit AZAV")) is None


def test_mailing_list_digest_ignored():
    assert classify_message(m("dev-request@lists.example.org", "Weekly digest", "senior developer position")) is None
    assert classify_message(m("hello@news.example.com", "Weekly problem: senior engineer interview", "")) is None


def test_prep_newsletters_and_notifications_ignored():
    assert classify_message(m("hello@interviewcake.com", "Your coding interview", "technical interview tips")) is None
    assert classify_message(m("notifications@vercel.com", "Deployment failed", "interview")) is None
    assert classify_message(m("noreply@github.com", "Run failed", "your application")) is None


def test_real_templates_still_work():
    rej = classify_message(
        m("hr@acme.de", "Ihre Bewerbung als Entwickler", "müssen wir dir leider mitteilen, dass wir uns für andere Kandidaten entschieden haben")
    )
    assert rej.status == "R"
    rej2 = classify_message(m("hr@acme.com", "Your application for Backend Engineer", "We regret to inform you that we have chosen other candidates"))
    assert rej2.status == "R"
    rec = classify_message(m("no-reply@join.com", "Your application for Backend Engineer at Acme", "We received your application"))
    assert rec.status in ("A", "U")
    iv = classify_message(m("hr@acme.com", "Invitation to interview for Backend Engineer", "We would like to invite you to an interview"))
    assert iv.status == "S"
