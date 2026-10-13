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
    assert classify_message(m("jobs-noreply@linkedin.com", "Your application was viewed by BoWatt")).status == "A"


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
    assert (viewed.status, viewed.company) == ("A", "TorAlarm GmbH")
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


def test_multitenant_platform_does_not_merge_companies():
    a = classify_message(
        m(
            "Rheinmetall <no-reply@rheinmetall.recruitmail.com>",
            "Ihre Bewerbung als Webentwickler (m/w/d)",
            "Vielen Dank für Ihre Bewerbung bei Rheinmetall.",
            id="1",
        )
    )
    b = classify_message(
        m(
            "ERGO <no-reply@ergo.recruitmail.com>",
            "Wir haben Ihre Bewerbung auf die Stellenausschreibung Software Engineer (m/w/d) ERGO02319 erhalten",
            "Ihre Bewerbung bei ITERGO. Sobald Ihre Unterlagen geprüft sind, folgt bei Interesse die Einladung zu einem Interview.",
            id="2",
        )
    )
    assert a.company != b.company
    assert b.status == "A"
    assert b.role == "Software Engineer (m/w/d)"


def test_recruitmail_company_from_text():
    e = classify_message(
        m("noreply@recruitmail.com", "Eingangsbestätigung", "Vielen Dank für Ihre Bewerbung bei Rheinmetall. Wir haben Ihre Bewerbung erhalten.")
    )
    assert e.company == "Rheinmetall" and e.status == "A"


def test_real_interview_invitation_still_selected():
    e = classify_message(
        m(
            "hr@acme.com",
            "Einladung zum Vorstellungsgespräch",
            "Wir laden Sie zu einem Vorstellungsgespräch ein. Falls Sie Fragen haben, rufen Sie uns an. Your application: Software Engineer",
        )
    )
    assert e.status == "S"


# ---- real mail templates found by comparing the app with the hand-checked list ----
def test_move_forward_with_another_candidate_is_rejection():
    e = classify_message(
        m(
            "recruitment@mayerfeld.consulting",
            "Update regarding your Associate Frontend Developer application",
            "Thank you for taking the time to reply. After reviewing the full pool of applicants, we've decided to move forward with another candidate for this position.",
        )
    )
    assert e.status == "R"


def test_will_not_move_you_forward_is_rejection():
    e = classify_message(
        m(
            "tctranscontinental+autoreply@talent.icims.com",
            "Thank you from Transcontinental Inc.",
            "Thank you for your interest in the Front End Developer position. After careful review of your application, we've decided that we will not move you forward",
        )
    )
    assert e.status == "R"


def test_confirmation_that_explains_rejection_is_still_a_receipt():
    e = classify_message(
        m(
            "sandvik@myworkday.com",
            "Thank you for submitting your application for Frontend Software Engineer",
            "Hello! Thank you for applying for a position with us, this is a confirmation that we received your application. Unfortunately we cannot answer everyone personally.",
        )
    )
    assert e.status == "A"


def test_incomplete_application_reminder_is_not_a_rejection():
    e = classify_message(
        m(
            "noreply@sopea-hr.com",
            "Ihre Bewerbung als Softwareentwickler (m/w/d) vom 15.05.2026 bei Espera-Werke GmbH",
            "Sie haben sich bei uns online beworben. Leider haben Sie die Eingabe Ihrer Bewerbungsdaten noch nicht vollständig abgeschlossen.",
        )
    )
    assert e.status == "C"


def test_indeed_apply_receipt_names_the_role():
    e = classify_message(m("indeedapply@indeed.com", "Bewerbung über Indeed: Personalberater Pädagogik (m/w/d)", "We'll help you get started"))
    assert (e.status, e.role, e.company) == ("A", "Personalberater Pädagogik (m/w/d)", "Via Indeed")


def test_amazon_roles_are_kept_apart_and_status_update_is_read():
    a = classify_message(
        m(
            "noreply@mail.amazon.jobs",
            "Bewerbung bei Amazon: Status-Update",
            "Vielen Dank für Ihre Bewerbung auf die Stelle als Software Development Engineer, Fire TV (ID: 10417193). Nach sorgfältiger Prüfung Ihrer Bewerbung haben wir uns dagegen entschieden.",
            date="2026-08-14",
            id="1",
        )
    )
    assert (a.company, a.role, a.status) == ("Amazon", "Software Development Engineer, Fire TV", "R")
    b = classify_message(
        m(
            "noreply@mail.amazon.jobs",
            "Follow-up: Amazon möchte ein Vorstellungsgespräch mit dir führen!",
            "Stelle als Software Development Engineer, AWS Security (ID: 10420668)",
            date="2026-08-01",
            id="2",
        )
    )
    assert (b.role, b.status) == ("Software Development Engineer, AWS Security", "S")
    rows = build_applications([a, b], NOW)
    assert sorted(r["status"] for r in rows) == ["N", "R"]


def test_dhl_mails_become_separate_applications():
    evs = [
        classify_message(m("DHL Recruiting - DO NOT REPLY! <noreply@dhl.com>", f"Ihre Bewerbung: {role} ID {i} bei DHL Group", "Leider", date=d, id=str(i)))
        for i, role, d in [(322474, "IT Solutions Architect (m/w/d)", "2026-09-04"), (322543, "IT Projektmanager (m/w/d)", "2026-07-06")]
    ]
    rows = build_applications(evs, NOW)
    assert len(rows) == 2 and {r["company"] for r in rows} == {"DHL"}


def test_person_sender_joins_the_company_with_same_role():
    a = classify_message(
        m(
            "ITERGO <hr@itergo.com>",
            "Wir haben Ihre Bewerbung auf die Stellenausschreibung Software Engineer (m/w/d) ERGO02319 erhalten",
            date="2026-05-10",
            id="1",
        )
    )
    b = classify_message(
        m(
            "Michael Hepe <no-reply@x.recruitmail.com>",
            "Ihre Bewerbung auf die Stellenausschreibung: Software Engineer (m/w/d)",
            "Leider müssen wir Ihnen absagen",
            date="2026-09-08",
            id="2",
        )
    )
    rows = build_applications([a, b], NOW)
    assert len(rows) == 1 and rows[0]["status"] == "R"


def test_company_cleanup_from_sender_names():
    e = classify_message(
        m("Winnie Cai - Everyman Health <w@everyman.com>", "Reply on your job application", "Unfortunately we will not be moving forward with your application")
    )
    assert e.company == "Everyman Health"
    e = classify_message(
        m("noreply@join.com", "We received your application for a position at Airteam Aerial Intelligence GmbH", "Thank you for applying for this position.")
    )
    assert e.company == "Airteam Aerial Intelligence GmbH"
    e = classify_message(
        m(
            "Andre, Elke <e@fom.de>",
            "FOM - Ihre Bewerbung für die Position Core Systems Engineer (m/w/d)",
            "Leider müssen wir Ihnen mitteilen, dass wir Ihre Bewerbung nicht weiter berücksichtigen können.",
        )
    )
    assert e.company == "FOM"


def test_not_a_job_mail():
    assert classify_message(m("No-reply-esta5@cbp.dhs.gov", "ESTA Application Number", "Your ESTA application")) is None
    assert classify_message(m("Matt Hazim <m@x.com>", "Your AI Clipping Agency application — here's what's next", "application")) is None


# ---- round 3: mismatches seen in the live list ----
def test_invisible_padding_does_not_hide_the_decision():
    pad = "͏ " * 400
    e = classify_message(
        m(
            "info@email.stepstone.de",
            "Update on your application for the role of React Developer:in (m/w/d) with GreenPocket GmbH",
            "Feedback from GreenPocket GmbH " + pad + " Unfortunately we must inform you that we cannot consider you for the next stage",
        )
    )
    assert e.status == "R"


def test_assessment_invitation_is_selected_and_company_is_the_employer():
    e = classify_message(
        m(
            "careers@procertifyhub.com",
            "Assessment Next Steps: Junior JavaScript Developer",
            "Technical Assessment A step in your application. Thank you for your application for the Junior JavaScript Developer role at Ravencoin Foundation. Your profile has moved to",
        )
    )
    assert (e.status, e.company) == ("S", "Ravencoin Foundation")


def test_company_names_never_merge_by_loose_role_match():
    apple = classify_message(
        m(
            "Apple Worldwide Recruiting <a@email.apple.com>",
            "Danke für dein Interesse an Apple.",
            "Frontend Engineer, Annotation Platform für die Position",
            id="1",
        )
    )
    pigment = classify_message(
        m(
            "Pigment <no-reply@hire.lever.co>",
            "Thanks for your interest in Pigment, Spoorthi",
            "Thank you for your application. After reviewing your work we decided to not move forward",
            id="2",
        )
    )
    pigment.role = "Front-end Engineer"
    apple.role = "AIML - Frontend Engineer, Annotation Platform & Agentic UI Experiences"
    rows = build_applications([apple, pigment], NOW)
    assert len(rows) == 2


def test_withdrawn_stays_withdrawn():
    e = classify_message(
        m("noreply@mail.amazon.jobs", "You've withdrawn your Amazon job application!", "position of Quality Assurance Engineer-I (ID: 604179)")
    )
    assert e.status == "W"
    assert build_applications([e], NOW)[0]["status"] == "W"


def test_promo_complete_your_application_is_not_a_job():
    assert (
        classify_message(m("noreply@axisbank.com", "Hi Congrats - Complete your Application to have your card dispatched", "Complete your application")) is None
    )


def test_company_from_subject_end_and_icims_suffix():
    e = classify_message(
        m(
            "System <noreply@sopea-hr.com>",
            "Ihre Bewerbung als Softwareentwickler (m/w/d) vom 15.05.2026 bei Espera-Werke GmbH",
            "Sie haben die Eingabe noch nicht vollständig abgeschlossen. Bewerbung",
        )
    )
    assert e.company == "Espera-Werke GmbH"
    e = classify_message(
        m(
            "Transcontinental Inc. @ icims <x+autoreply@talent.icims.com>",
            "Thank you from Transcontinental Inc.",
            "we will not move you forward with your application",
        )
    )
    assert e.company.startswith("Transcontinental")


def test_platform_sender_is_not_the_employer():
    e = classify_message(
        m(
            "Pro Certify Career Update <careers@procertifyhub.com>",
            "Assessment Next Steps: Junior JavaScript Developer",
            "Technical Assessment. Thank you for your application for the Junior JavaScript Developer role at Ravencoin Foundation. Your profile has moved to",
        )
    )
    assert e.company == "Ravencoin Foundation"


def test_mailbox_name_on_workday_is_the_employer_and_never_merges_by_role():
    a = classify_message(m("creditreform@myworkday.com", "Deine Bewerbung als Software Entwickler (m/w/d)", "Leider", id="1"))
    b = classify_message(
        m(
            "Melanie <hr@optadata.de>",
            "Danke für Deine Bewerbung als Softwareentwickler (w/m/x)",
            "Vielen Dank für Ihre Bewerbung, wir haben Ihre Bewerbung erhalten und melden uns.",
            id="2",
        )
    )
    assert a.company == "Creditreform" and not a.weak
    assert len(build_applications([a, b], NOW)) == 2


def test_person_name_sender_joins_bilingual_title_of_same_job():
    a = classify_message(
        m(
            "Reifenhäuser NEXT <j@rexx-systems.com>",
            "Deine Bewerbung als (Junior) Software Developer (m/w/d) / Your application as (Junior) Software Developer (m/w/d)",
            "Vielen Dank für Ihre Bewerbung, wir haben Ihre Bewerbung erhalten.",
            date="2026-07-14",
            id="1",
        )
    )
    b = classify_message(
        m(
            "Jennifer Kroll <j@rexx-systems.com>",
            "Deine Bewerbung als (Junior) Software Developer (m/w/d)",
            "Leider müssen wir Ihnen mitteilen, dass wir Ihre Bewerbung nicht weiter berücksichtigen können.",
            date="2026-07-23",
            id="2",
        )
    )
    rows = build_applications([a, b], NOW)
    assert len(rows) == 1 and rows[0]["status"] == "R"


def test_an_offer_or_long_correspondence_never_fades_to_no_response():
    a = classify_message(
        m(
            "jobs@acme-gmbh.de",
            "Ihre Bewerbung - Zusage und Arbeitsvertrag",
            "Wir freuen uns, Ihnen den Arbeitsvertrag zu senden. Bewerbung als Entwickler",
            date="2023-01-10",
            id="1",
        )
    )
    assert a and a.status == "S" and a.offer
    assert build_applications([a], NOW)[0]["status"] == "S"


def test_marketing_about_job_offers_is_not_an_offer():
    a = classify_message(
        m(
            "hello@careercamp.codingninjas.com",
            "Update: Confirm your application to build Data Science skills",
            "Some professionals wait for one job offer. Others get to choose. Your application",
            id="1",
        )
    )
    assert a is None
    b = classify_message(
        m(
            "sandvik@myworkday.com",
            "Thank you for submitting your application for Frontend Software Engineer",
            "Thank you for your application. You may receive a job offer later. Unfortunately we cannot answer everyone.",
            id="2",
        )
    )
    assert b.status == "A"


def test_polite_acknowledgement_titled_ihre_bewerbung_is_applied():
    e = classify_message(
        m(
            "bewerbungen@betzemeier.de",
            "Ihre Bewerbung als Softwareentwickler Frontend (m/w/d)",
            "Sehr geehrte Frau Madhavan, wir freuen uns über Ihr Interesse an einer Tätigkeit bei uns und bedanken uns für Ihre Bewerbung. Bitte haben Sie Verständnis dafür, dass wir für eine Rückmeldung noch etwas",
            date="2026-10-11",
        )
    )
    assert e and e.status == "A" and e.company.lower().startswith("betzemeier")


def test_german_recruiter_call_invite_is_selected():
    e = classify_message(
        m(
            "cornelia.hoesler@victoria-consulting.de",
            "CH/TEAMS-Interview Frau Madhavan als SW Entwickler Monitoring-Software Erlangen",
            "Hallo Frau Madhavan, wie soeben telefonisch kurz abgestimmt, freue ich mich auf den Kennenlern-Call mit Ihnen am Mittwoch, 14.10.2026 um 14 Uhr und Sie erhalten nachfolgend den entsprechenden TEAMS-",
            date="2026-10-13",
        )
    )
    assert e and e.status == "S"


def test_successfactors_confirmation_reads_role_from_quoted_subject():
    e = classify_message(
        m(
            "system@successfactors.com",
            'Ihre Bewerbung auf die Stelle als "Fachinformatiker (m/w/d) Schwerpunkt Softwaretest"',
            "Eingangsbestätigung Sehr geehrte/r Spoorthi, wir danken Ihnen für die Zusendung Ihrer Bewerbung",
        )
    )
    assert e.status == "A" and e.role == "Fachinformatiker (m/w/d) Schwerpunkt Softwaretest"
    assert classify_message(m("system@successfactors.com", "KNDS-Group: Anlage Ihres Bewerberkontos", "Willkommen bei KNDS, Ihre Registrierung")).status == "C"


def test_platform_mail_reads_the_employer_from_the_footer():
    subject = 'Ihre Bewerbung auf die Stelle als "Fachinformatiker (m/w/d) Schwerpunkt Softwaretest"'
    preview = "Eingangsbestätigung Sehr geehrte/r Spoorthi, wir danken Ihnen für die Zusendung Ihrer Bewerbung"
    first = m("system@successfactors.com", subject, preview)
    assert needs_body(first)  # the platform name is only a guess: read the full text
    body = preview + " Mit freundlichen Grüßen Human Resources KNDS Deutschland GmbH & Co. KG © KNDS Deutschland. Alle Rechte vorbehalten."
    e = classify_message(m("system@successfactors.com", subject, body))
    assert e.company.startswith("KNDS") and not e.weak
