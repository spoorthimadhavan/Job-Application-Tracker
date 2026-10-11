import { useCallback, useEffect, useMemo, useState } from "react";
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
import { applyOverrides, loadOverrides, saveOverrides } from "./overrides.js";

export default function App() {
  const [me, setMe] = useState(undefined); // undefined = loading, null = signed out
  const [status, setStatus] = useState("all");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("newest");
  const [open, setOpen] = useState(null);
  const [docs, setDocs] = useState({});
  const [range, setRange] = useState(loadRange);
  const [overrides, setOverrides] = useState({});

  useEffect(() => {
    getMe().then(setMe).catch(() => setMe({ email: null, google_configured: false }));
  }, []);

  const signedIn = Boolean(me && me.email);
  useEffect(() => {
    if (me && me.email) setOverrides(loadOverrides(me.email));
  }, [me]);
  const setManual = (id, st) => {
    const next = { ...overrides };
    if (st) next[id] = st;
    else delete next[id];
    setOverrides(next);
    saveOverrides(me.email, next);
  };
  const refreshDocs = useCallback(() => {
    if (me && me.email) listDocs(me.email).then(setDocs).catch(() => {});
  }, [me]);
  useEffect(refreshDocs, [refreshDocs]);
  const onSignedOut = useCallback(() => setMe((m) => ({ ...m, email: null })), []);
  const since = sinceFor(range.choice, range.custom, me && me.member_since);
  const { data, error } = useApplications(signedIn, since, onSignedOut);
  const merged = useMemo(() => applyOverrides(data ? data.applications : [], overrides), [data, overrides]);
  const changeRange = (r) => { setRange(r); saveRange(r); };

  if (me === undefined) return <p className="center muted">Loading…</p>;
  if (!signedIn) return <Login googleConfigured={me.google_configured} failed={location.search.includes("login=failed")} scopeMissing={location.search.includes("login=scope")} />;

  const apps = merged.apps;
  const q = query.trim().toLowerCase();
  const shown = apps
    .filter((a) => status === "all" || a.status === status)
    .filter((a) => !q || `${a.company} ${a.role} ${a.sender || ""}`.toLowerCase().includes(q))
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
      <StatTiles counts={merged.counts} total={apps.length} active={status} onPick={(s) => setStatus(status === s ? "all" : s)} />
      <Toolbar query={query} onQuery={setQuery} sort={sort} onSort={setSort} range={range} onRange={changeRange} memberSince={me.member_since} />
      <ApplicationList apps={shown} total={apps.length} loading={!data} docs={docs} onOpen={(a) => setOpen(a.id)} />
      {open && apps.find((a) => a.id === open) && <EmailDrawer application={apps.find((a) => a.id === open)} onStatus={setManual} email={me.email} onDocsChange={refreshDocs} onClose={() => setOpen(null)} />}
    </div>
  );
}
