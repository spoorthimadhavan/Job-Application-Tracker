import { useEffect, useState } from "react";
import StatusPill from "./StatusPill.jsx";
import { formatDate } from "../status.js";

export const PAGE_SIZE = 10;

export default function ApplicationList({ apps, total, loading, docs, onOpen }) {
  const [page, setPage] = useState(0);
  const pages = Math.max(1, Math.ceil(apps.length / PAGE_SIZE));
  // a new filter, search or scan result starts again at the first page
  useEffect(() => setPage(0), [apps]);
  if (loading) return <p className="muted pad">Reading your mailbox…</p>;
  const current = Math.min(page, pages - 1);
  const shown = apps.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE);
  const open = (e, a) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onOpen(a);
    }
  };
  return (
    <>
      <p className="count muted">
        {apps.length} of {total} applications. Click a row to see the email.
      </p>
      {!apps.length && <p className="muted pad list">Nothing matches. Clear the search or pick another status.</p>}
      {!!apps.length && (
        <div className="list">
          <table className="grid">
            <caption className="sr">Job applications, {PAGE_SIZE} per page</caption>
            <thead>
              <tr>
                <th scope="col">Date</th>
                <th scope="col">Company</th>
                <th scope="col" className="c-se">Sender</th>
                <th scope="col">Job title</th>
                <th scope="col" className="c-pv">Message preview</th>
                <th scope="col">Status</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((a) => (
                <tr key={a.id} className="row" tabIndex={0} onClick={() => onOpen(a)} onKeyDown={(e) => open(e, a)}>
                  <td className="d">{formatDate(a.date)}</td>
                  <th scope="row" className="co">{a.company}</th>
                  <td className="se c-se" title={a.sender}>{a.sender}</td>
                  <td className="ro">
                    {a.role}
                    {docs[a.id] && <span className="clip" title="Resume or cover letter attached">{docs[a.id].length} file{docs[a.id].length > 1 ? "s" : ""}</span>}
                    {(a.note || a.check) && (
                      <small>
                        {a.check && <span className="v">check</span>}
                        {a.note}
                      </small>
                    )}
                  </td>
                  <td className="pv c-pv" title={a.preview}>{a.preview}</td>
                  <td className="st"><StatusPill status={a.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
          <nav className="pager" aria-label="Pagination">
            <button type="button" className="btn ghost small" disabled={current === 0} onClick={() => setPage(current - 1)}>Previous</button>
            <span className="muted" aria-live="polite">
              Page {current + 1} of {pages}
            </span>
            <button type="button" className="btn ghost small" disabled={current >= pages - 1} onClick={() => setPage(current + 1)}>Next</button>
          </nav>
        </div>
      )}
    </>
  );
}
