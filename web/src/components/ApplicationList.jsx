import StatusPill from "./StatusPill.jsx";
import { formatDate } from "../status.js";

export default function ApplicationList({ apps, total, loading, docs, onOpen }) {
  if (loading) return <p className="muted pad">Reading your mailbox…</p>;
  return (
    <>
      <p className="count muted">{apps.length} of {total} applications. Click a row to see the email.</p>
      <div className="list">
        {!apps.length && <p className="muted pad">Nothing matches. Clear the search or pick another status.</p>}
        {!!apps.length && (
          <div className="row head" aria-hidden="true">
            <span>Date</span>
            <span>Company</span>
            <span>Sender</span>
            <span>Job title</span>
            <span>Message preview</span>
            <span>Status</span>
          </div>
        )}
        {apps.map((a) => (
          <button key={a.id} className="row" onClick={() => onOpen(a)}>
            <span className="d">{formatDate(a.date)}</span>
            <span className="co">{a.company}</span>
            <span className="se" title={a.sender}>{a.sender}</span>
            <span className="ro">
              {a.role}
              {docs[a.id] && <span className="clip" title="Resume or cover letter attached">{docs[a.id].length} file{docs[a.id].length > 1 ? "s" : ""}</span>}
              {(a.note || a.check) && (
                <small>
                  {a.check && <span className="v">check</span>}
                  {a.note}
                </small>
              )}
            </span>
            <span className="pv" title={a.preview}>{a.preview}</span>
            <StatusPill status={a.status} />
          </button>
        ))}
      </div>
    </>
  );
}
