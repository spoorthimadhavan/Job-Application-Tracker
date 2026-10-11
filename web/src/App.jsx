import { useCallback, useEffect, useState } from "react";
import { getMe, logout } from "./api.js";
import { useApplications } from "./useApplications.js";
import Login from "./components/Login.jsx";
import TopBar from "./components/TopBar.jsx";
import StatTiles from "./components/StatTiles.jsx";
import Toolbar from "./components/Toolbar.jsx";
import ApplicationList from "./components/ApplicationList.jsx";
import { listDocs } from "./docs.js";
import { loadRange, saveRange, sinceFor } from "./range.js";
import EmailDrawer from "./components/EmailDrawer.jsx";

export default function App() {
  const [me, setMe] = useState(undefined); // undefined = loading, null = signed out
  const [status, setStatus] = useState("all");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("newest");
  const [open, setOpen] = useState(null);
  const [docs, setDocs] = useState({});
  const [range, setRange] = useState(loadRange);

  useEffect(() => {
    getMe().then(setMe).catch(() => setMe({ email: null, google_configured: false }));
  }, []);

  const signedIn = Boolean(me && me.email);
  const refreshDocs = useCallback(() => {
    if (me && me.email) listDocs(me.email).then(setDocs).catch(() => {});
  }, [me]);
  useEffect(refreshDocs, [refreshDocs]);
  const onSignedOut = useCallback(() => setMe((m) => ({ ...m, email: null })), []);
  const since = sinceFor(range.choice, range.custom, me && me.member_since);
  const { data, error } = useApplications(signedIn, since, onSignedOut);
  const changeRange = (r) => { setRange(r); saveRange(r); };

  if (me === undefined) return <p className="center muted">Loading…</p>;
  if (!signedIn) return <Login googleConfigured={me.google_configured} failed={location.search.includes("login=failed")} scopeMissing={location.search.includes("login=scope")} />;

  const apps = data ? data.applications : [];
  const q = query.trim().toLowerCase();
  const shown = apps
    .filter((a) => status === "all" || a.status === status)
    .filter((a) => !q || `${a.company} ${a.role}`.toLowerCase().includes(q))
    .sort((a, b) =>
      sort === "company" ? a.company.localeCompare(b.company) : sort === "oldest" ? a.date.localeCompare(b.date) : b.date.localeCompare(a.date)
    );

  return (
    <div className="wrap">
      <TopBar
        email={me.email}
        demo={me.demo}
        updatedAt={data && data.updated_at}
        since={data && data.since}
        onLogout={() => logout().then(() => setMe({ ...me, email: null }))}
      />
      {error && <p className="banner">{error}</p>}
      <StatTiles counts={data ? data.counts : {}} total={apps.length} active={status} onPick={(s) => setStatus(status === s ? "all" : s)} />
      <Toolbar query={query} onQuery={setQuery} sort={sort} onSort={setSort} range={range} onRange={changeRange} memberSince={me.member_since} />
      <ApplicationList apps={shown} total={apps.length} loading={!data} docs={docs} onOpen={setOpen} />
      {open && <EmailDrawer application={open} email={me.email} onDocsChange={refreshDocs} onClose={() => setOpen(null)} />}
    </div>
  );
}
