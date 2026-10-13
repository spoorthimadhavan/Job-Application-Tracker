import { useEffect, useState } from "react";

export default function TopBar({ email, demo, updatedAt, since, onLogout, onRefresh }) {
  const [, force] = useState(0);
  useEffect(() => {
    const t = setInterval(() => force((n) => n + 1), 10000);
    return () => clearInterval(t);
  }, []);
  const secs = updatedAt ? Math.max(0, Math.round(Date.now() / 1000 - updatedAt)) : null;
  return (
    <header className="top">
      <div>
        <h1>Job Application Tracker</h1>
        <p className="muted">
          <span className="live" aria-hidden="true" />
          Live{secs !== null ? `, checked ${secs < 5 ? "just now" : secs + "s ago"}` : ""}
          {since ? ` · mail since ${since.replaceAll("/", "-")}` : ""}
        </p>
      </div>
      <div className="who">
        {onRefresh && <button className="btn ghost small" onClick={onRefresh}>Refresh now</button>}
        <span className="muted">{demo ? "Demo data" : email}</span>
        <button className="btn ghost small" onClick={onLogout}>Sign out</button>
      </div>
    </header>
  );
}
