import { useEffect, useState } from "react";
import { getEmail } from "../api.js";
import StatusPill from "./StatusPill.jsx";
import Documents from "./Documents.jsx";
import { STATUS, formatDate } from "../status.js";

const SOURCE = { linkedin: "LinkedIn", indeed: "Indeed", stepstone: "StepStone", email: "Email" };

export default function EmailDrawer({ application, email, onDocsChange, onClose }) {
  const [pick, setPick] = useState(application.events[0]);
  const [mail, setMail] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    setMail(null);
    setErr("");
    getEmail(pick.message_id).then(setMail).catch(() => setErr("This email could not be loaded."));
  }, [pick]);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="scrim" onClick={onClose}>
      <aside className="drawer" role="dialog" aria-label="Email" onClick={(e) => e.stopPropagation()}>
        <header>
          <div>
            <h2>{application.company}</h2>
            <p className="muted">{application.role}</p>
          </div>
          <button className="btn ghost small" onClick={onClose}>Close</button>
        </header>

        <Documents email={email} appId={application.id} onChange={onDocsChange} />

        <ol className="timeline">
          {application.events.map((ev) => (
            <li key={ev.message_id}>
              <button aria-pressed={ev.message_id === pick.message_id} onClick={() => setPick(ev)}>
                <span className="muted">{formatDate(ev.date)} · {SOURCE[ev.source] || "Email"}</span>
                <span>{STATUS[ev.status]?.label}</span>
              </button>
            </li>
          ))}
        </ol>

        {err && <p className="banner">{err}</p>}
        {!mail && !err && <p className="muted">Loading email…</p>}
        {mail && (
          <section className="mail">
            <p><b>{mail.subject}</b></p>
            <p className="muted">From {mail.from}<br />{new Date(mail.date).toLocaleString("en-GB")}</p>
            {mail.html ? (
              /* sandbox with no flags: no scripts, no forms, no navigation */
              <iframe title="Email copy" sandbox="" srcDoc={mail.html} />
            ) : (
              <pre>{mail.text}</pre>
            )}
            {mail.gmail_url && <a className="btn small" href={mail.gmail_url} target="_blank" rel="noreferrer">Open in Gmail</a>}
          </section>
        )}
        <footer><StatusPill status={application.status} /></footer>
      </aside>
    </div>
  );
}
