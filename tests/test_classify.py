import pathlib
import sys
from datetime import UTC, datetime

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "api"))
from _lib.classify import build_applications, classify_message, needs_body

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


def test_job_mail_in_promotions_updates_social_is_kept():
    for label in ("CATEGORY_PROMOTIONS", "CATEGORY_UPDATES", "CATEGORY_SOCIAL", "CATEGORY_FORUMS"):
        e = classify_message(ml("hr@acme.com", "Your application for Backend Engineer", "We regret to inform you that we chose other candidates", [label]))
        assert e is not None and e.status == "R"


def test_newsletter_in_promotions_still_ignored():
    assert classify_message(ml("jobs@board.com", "10 senior engineer roles this week", "senior developer position", ["CATEGORY_PROMOTIONS"])) is None


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


def test_indeed_role_company_sender_preview():
    snip = "Vielen Dank für Ihre Bewerbung auf die Stelle als Personalberater Pädagogik (m/w/d) bei Acme GmbH & Co KG. Acme hat den nächsten Schritt eingeleitet. Leider konnte Ihre Bewerbung dieses Mal nicht berücksichtigt werden."
    mail = m('"Acme GmbH &amp; Co KG" <noreply@indeed.com>', "Neuigkeiten zu Ihrer Bewerbung von Acme GmbH &amp; Co KG", snip)
    e = classify_message(mail)
    assert (e.status, e.company, e.role) == ("R", "Acme GmbH & Co KG", "Personalberater Pädagogik (m/w/d)")
    row = build_applications([e], NOW)[0]
    assert row["sender"] == "Acme GmbH & Co KG" and row["preview"].startswith("Vielen Dank")


def test_packmatic_body_rejection_and_linkedin_receipt_merge():
    body = "Hello Spoorthi, Thank you very much for applying for the Software Engineer (w/m/d) - B2B Saas I Berlin (hybrid) position and for trusting our company! We reviewed your application materials carefully and were impressed. However, after careful consideration we have decided to move forward with other applicants."
    rej = {**m("luise.schilling@packmatic.io", "Packmatic I Your Application", body), "date": "2026-10-07", "preview": body[:100]}
    sent = {**m("jobs-noreply@linkedin.com", "Spoorthi, your application was sent to Packmatic", "x", id="2"), "date": "2026-10-05"}
    rows = build_applications([classify_message(rej), classify_message(sent)], NOW)
    assert len(rows) == 1 and rows[0]["status"] == "R" and rows[0]["company"] == "Packmatic"
    assert rows[0]["role"].startswith("Software Engineer")


def test_needs_body_for_truncated_receipt():
    short = "Hello Spoorthi, Thank you very much for applying for the Software Engineer position and for trusting our company! We reviewed your application materials carefully"
    assert needs_body(m("luise@packmatic.io", "Packmatic I Your Application", short))
    assert not needs_body(m("jobs-noreply@linkedin.com", "Your application to X at Y"))


def test_two_roles_same_company_stay_separate():
    a = m(
        "appleworldwiderecruiting@email.apple.com",
        "Danke für dein Interesse an Apple.",
        "gerade haben wir deinen Lebenslauf zusammen mit deiner Bewerbung als AIML - Frontend Engineer, Annotation Platform & Agentic UI Experiences 200680114 bekommen.",
        id="1",
    )
    b = m(
        "appleworldwiderecruiting@email.apple.com",
        "Danke für dein Interesse an Apple.",
        "gerade haben wir deinen Lebenslauf zusammen mit deiner Bewerbung als DevOps / Infrastructure Engineer — Firmware Validation (f/m/d) 200687419 bekommen.",
        id="2",
    )
    rows = build_applications([classify_message(a), classify_message(b)], NOW)
    assert len(rows) == 2
    assert {r["role"] for r in rows} == {
        "AIML - Frontend Engineer, Annotation Platform & Agentic UI Experiences",
        "DevOps / Infrastructure Engineer — Firmware Validation (f/m/d)",
    }


def test_rejection_only_hits_its_own_role():
    a = {**m("recruiting@acme.com", "Your application for Frontend Engineer", "We received your application", id="1"), "date": "2026-09-01"}
    b = {**m("recruiting@acme.com", "Your application for Backend Engineer", "We received your application", id="2"), "date": "2026-09-02"}
    c = {**m("recruiting@acme.com", "Your application for Frontend Engineer", "Unfortunately we will not move forward", id="3"), "date": "2026-09-10"}
    rows = {r["role"]: r["status"] for r in build_applications([classify_message(x) for x in (a, b, c)], NOW)}
    assert rows == {"Frontend Engineer": "R", "Backend Engineer": "A"}


def test_person_sender_is_not_the_company():
    e = classify_message(
        m(
            "Olga Raskovic <olga.raskovic@nortal.com>",
            "Spoorthi , thank you for your interest in Nortal!",
            "Hello Spoorthi! Thank you for your interest in the Frontend Developer (m/w/d) position at Nortal. After a thorough review, we regret to inform you",
        )
    )
    assert (e.company, e.role, e.status, e.sender) == ("Nortal", "Frontend Developer (m/w/d)", "R", "Olga Raskovic")


def test_subject_prefix_company_beats_person_name():
    e = classify_message(
        m(
            "Jasmina Abdou <admin@bridgerhq.com>",
            "Bridger | Update on your process with Bundesliga Media",
            "Unfortunately, they have decided not to move forward with your application",
        )
    )
    assert e.company == "Bridger" and e.status == "R" and e.sender == "Jasmina Abdou"


def test_company_named_sender_kept():
    e = classify_message(
        m("Athletic Sport Sponsoring <ass-jobs@m.personio.de>", "Deine Bewerbung als Fullstack Developer (m/w/d)", "vielen Dank für deine Bewerbung")
    )
    assert e.company == "Athletic Sport Sponsoring"


def test_aldi_receipt_and_rejection_merge():
    rcpt = {
        **m(
            "noreply@aldi-nord.de",
            "Eingangsbestätigung: Deine Bewerbung auf die Stelle - Software Engineer – Data Platforms (m/w/d)",
            "Hallo, vielen Dank für deine Bewerbung auf die Stelle &quot;Software Engineer – Data Platforms (m/w/d)&quot; und dein Interesse, deine Power bei ALDI Nord einzubringen.",
            id="1",
        ),
        "date": "2026-09-12",
    }
    rej = {
        **m(
            "noreply@aldi-nord.de",
            "Deine Bewerbung auf die Stelle Software Engineer – Data Platforms (m/w/d)",
            "nochmals vielen Dank für deine Bewerbung und dein Interesse, deine Power bei ALDI Nord einzubringen. Nach eingehender Prüfung deiner Unterlagen müssen wir dir leider mitteilen,",
            id="2",
        ),
        "date": "2026-10-08",
    }
    rows = build_applications([classify_message(rcpt), classify_message(rej)], NOW)
    assert len(rows) == 1 and rows[0]["status"] == "R" and rows[0]["role"] == "Software Engineer – Data Platforms (m/w/d)"
    assert "&quot;" not in rows[0]["preview"]


def test_oh_so_company_variants_merge():
    a = {
        **m(
            "OH-SO Digital <talent@oh-so.com>",
            "OH-SO - Thank you for your application // OH-SO Vielen Dank für Deine Bewerbung",
            "Thank you so much for your application. Your application documents have been received",
            id="1",
        ),
        "date": "2026-09-12",
    }
    b = {
        **m(
            "talent@oh-so.com",
            "OH-SO - Feedback on your application",
            "After careful consideration of your application, we regret to inform you that we have chosen other candidates",
            id="2",
        ),
        "date": "2026-10-02",
    }
    rows = build_applications([classify_message(a), classify_message(b)], NOW)
    assert len(rows) == 1 and rows[0]["status"] == "R"


def test_interview_then_silence_becomes_no_response():
    iv = {**m("hr@amazon.jobs", "Invitation to interview for Security Engineer", "We would like to invite you to an interview", id="1"), "date": "2026-08-17"}
    row = build_applications([classify_message(iv)], NOW)[0]
    assert row["status"] == "N" and "no reply" in row["note"]
    fresh = {**iv, "date": "2026-10-05"}
    assert build_applications([classify_message(fresh)], NOW)[0]["status"] == "S"


def test_german_indeed_rejection_read_from_body():
    body = "Vielen Dank für Ihre Bewerbung als Mitarbeiter/in (m/w/d) für den Empfang bei Praxis X. Praxis X hat den nächsten Schritt im Bewerbungsprozess eingeleitet. Leider konnte Ihre Bewerbung dieses Mal nicht berücksichtigt werden."
    e = classify_message({**m("noreply@indeed.com", "Neuigkeiten zu Ihrer Bewerbung von Praxis X", body), "preview": body[:80]})
    assert e.status == "R" and e.snippet.startswith("Vielen Dank")


def test_junk_is_never_used_as_job_title():
    from _lib.classify import _role

    for text in (
        "Hallo Spoorthi Satish, vielen Dank für Dein Interesse an einer Karriere bei uns! Wir haben Deine Bewerbung als Softwareentwickler (m/w/d) erhalten und freuen uns",
        "Thank you for applying to EvenUp! We will contact you as soon as possible and speak to the relevant department",
    ):
        assert not _role("Thanks for applying to EvenUp!", text).lower().startswith(("als", "applying", "soon"))
    assert _role("", "Wir haben Deine Bewerbung als Softwareentwickler (m/w/d) erhalten und freuen uns") == "Softwareentwickler (m/w/d)"
    assert (
        _role("Thanks for applying to EvenUp!", "Thank you for applying to the Frontend Engineer, Growth & Agents role here at EvenUp! We've")
        == "Frontend Engineer, Growth & Agents"
    )
    assert _role("Thanks", "Thank you for applying to the Backend Engineer position at Almedia") == "Backend Engineer"


def test_mail_without_a_date_does_not_break_grouping():
    e = classify_message({**m("jobs-noreply@linkedin.com", "Your application to Dev at Foo GmbH"), "date": ""})
    assert e.date and build_applications([e], NOW)[0]["company"] == "Foo GmbH"
