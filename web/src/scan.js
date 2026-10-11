// Reads the mailbox in small steps. Gmail allows only about 50 mails per second, so one big request
// cannot finish in a serverless time limit. Each step classifies a few new mails on the server; the
// results stay in this browser, so later loads and the 30 s refresh only fetch what is new.
const KEY = (email) => `jt-events:${email || ""}`;

function load(email) {
  try {
    const s = JSON.parse(localStorage.getItem(KEY(email)) || "null");
    if (s && s.events) return s;
  } catch { /* storage unavailable */ }
  return { version: "", events: {} };
}

function save(email, store) {
  try {
    localStorage.setItem(KEY(email), JSON.stringify(store));
  } catch { /* full or private mode: the next load just reads again */ }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function scanApplications(since, { email, onProgress, step = 80 } = {}, post) {
  let store = load(email);
  let attempts = 0;
  let left = 0;
  let total = 0;
  const windowEvents = () => Object.values(store.events).filter((e) => e && e.date >= since);
  const build = async (partial) => {
    const built = await post("/api/build", { events: windowEvents() });
    return { ...built, since, partial, progress: { done: Math.max(total - left, 0), total } };
  };

  for (;;) {
    const r = await post("/api/scan", { since, known: Object.keys(store.events), version: store.version, n: step });
    if (r.version !== store.version) store = { version: r.version, events: {} }; // rules changed: start over
    Object.assign(store.events, r.events);
    save(email, store);
    left = r.left;
    total = r.total;
    if (!Object.keys(r.events).length) {
      if (left <= 0) break;
      if (++attempts >= 3) return build(true); // Gmail kept refusing: show what we have, try again later
      await sleep(800);
      continue;
    }
    attempts = 0;
    if (left <= 0) break;
    if (onProgress) onProgress(await build(true));
  }
  return build(false);
}
