// Manual status choices, kept in this browser per account (same place as uploaded documents).
const key = (email) => `jt-status:${email}`;

export function loadOverrides(email) {
  try {
    return JSON.parse(localStorage.getItem(key(email)) || "{}") || {};
  } catch {
    return {};
  }
}

export function saveOverrides(email, map) {
  try {
    localStorage.setItem(key(email), JSON.stringify(map));
  } catch {
    /* private mode: the choice lasts until the page closes */
  }
}

export function applyOverrides(apps, map) {
  const counts = {};
  const out = apps.map((a) => {
    const manual = map[a.id];
    const next = manual ? { ...a, status: manual, manual: true, auto: a.status, check: false, note: "Moved by you." } : a;
    counts[next.status] = (counts[next.status] || 0) + 1;
    return next;
  });
  return { apps: out, counts };
}
