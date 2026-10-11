import demo from "./demoData.js";
import { scanApplications } from "./scan.js";

// Demo build (no server): answer from the bundled sample mailbox, filtering by date like the API does.
function demoRequest(path) {
  if (path === "/api/me") return Promise.resolve({ ...demo.me, email: demo.me.email, member_since: new Date().toISOString().slice(0, 10) });
  if (path.startsWith("/api/applications")) {
    const since = new URL(path, "http://x").searchParams.get("since") || "2004-01-01";
    const apps = demo.apps.applications.filter((a) => a.date >= since);
    const counts = {};
    apps.forEach((a) => (counts[a.status] = (counts[a.status] || 0) + 1));
    return Promise.resolve({ ...demo.apps, since, counts, applications: apps, updated_at: Date.now() / 1000 });
  }
  if (path.startsWith("/api/emails/")) return Promise.resolve(demo.emails[decodeURIComponent(path.split("/").pop())]);
  return Promise.resolve({ ok: true });
}

async function request(path, options) {
  if (import.meta.env.VITE_DEMO) return demoRequest(path);
  const res = await fetch(path, { credentials: "same-origin", ...options });
  if (!res.ok) {
    const err = new Error(res.status === 401 ? "signed-out" : `Request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const getMe = () => request("/api/me");
const post = (path, body) =>
  request(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const getApplications = (since, opts = {}) =>
  import.meta.env.VITE_DEMO ? request(`/api/applications?since=${encodeURIComponent(since)}`) : scanApplications(since, opts, post);
export const getEmail = (id) => request(`/api/emails/${encodeURIComponent(id)}`);
export const logout = () => request("/api/auth/logout", { method: "POST" });
