// Reads the mailbox in small parallel steps. Gmail allows only about 50 mails per second and a serverless
// request lives ~10 s, so one big request cannot finish. The server lists the ids once, then classifies
// 50 at a time; results stay in this browser, so later loads and the 30 s refresh only fetch what is new.
const KEY = (email) => `jt-events:${email || ""}`;
const STEP = 50;
const PARALLEL = 3;

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

export async function scanApplications(since, { email, onProgress, step = STEP, parallel = PARALLEL } = {}, post) {
  let store = load(email);
  const listed = await post("/api/ids", { since });
  if (listed.version !== store.version) store = { version: listed.version, events: {} }; // rules changed: start over
  const ids = listed.ids;
  const todo = ids.filter((i) => !(i in store.events));
  const chunks = [];
  for (let n = 0; n < todo.length; n += step) chunks.push(todo.slice(n, n + step));

  let done = ids.length - todo.length;
  let failed = 0;
  const windowEvents = () => Object.values(store.events).filter((e) => e && e.date >= since);
  const build = async (partial) => {
    const built = await post("/api/build", { events: windowEvents() });
    return { ...built, since, partial, progress: { done, total: ids.length } };
  };

  let next = 0;
  let building = Promise.resolve();
  const worker = async () => {
    while (next < chunks.length) {
      const chunk = chunks[next++];
      let ok = false;
      for (let attempt = 0; attempt < 2 && !ok; attempt++) {
        try {
          const r = await post("/api/scan", { ids: chunk });
          Object.assign(store.events, r.events);
          const got = Object.keys(r.events).length;
          done += got;
          if (got < chunk.length) failed += chunk.length - got; // Gmail skipped some: a later load picks them up
          ok = true;
        } catch (e) {
          if (e.status === 401) throw e;
        }
      }
      if (!ok) failed += chunk.length;
      save(email, store);
      if (onProgress && next < chunks.length) building = building.then(async () => onProgress(await build(true)));
    }
  };
  await Promise.all(Array.from({ length: Math.min(parallel, chunks.length) }, worker));
  await building;
  return build(failed > 0);
}
