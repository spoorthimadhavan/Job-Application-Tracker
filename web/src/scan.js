// Reads the mailbox in small parallel steps. Gmail allows only about 50 mails per second and a serverless
// request lives ~10 s, so one big request cannot finish. Pass 1 classifies every mail from Gmail's short
// preview (fast, the list appears within seconds). Pass 2 then reads the full text of the few mails where
// the decision is hidden after the preview and corrects their status. Results stay in this browser, so
// later loads and the 30 s refresh only fetch what is new.
const KEY = (email) => `jt-events:${email || ""}`;
const STEP = 50;
const BODY_STEP = 15;
const PARALLEL = 5;

function load(email) {
  try {
    const s = JSON.parse(localStorage.getItem(KEY(email)) || "null");
    if (s && s.events) return { pending: {}, ...s };
  } catch { /* storage unavailable */ }
  return { version: "", events: {}, pending: {} };
}

function save(email, store) {
  try {
    localStorage.setItem(KEY(email), JSON.stringify(store));
  } catch { /* full or private mode: the next load just reads again */ }
}

export async function scanApplications(since, { email, onProgress, step = STEP, bodyStep = BODY_STEP, parallel = PARALLEL } = {}, post) {
  let store = load(email);
  const listed = await post("/api/ids", { since });
  if (listed.version !== store.version) store = { version: listed.version, events: {}, pending: {} }; // rules changed: start over
  const ids = listed.ids;
  const chunked = (list, n) => Array.from({ length: Math.ceil(list.length / n) }, (_, k) => list.slice(k * n, k * n + n));

  let done = 0;
  let total = 0;
  let phase = "preview";
  let failed = 0;
  const windowEvents = () => Object.values(store.events).filter((e) => e && e.date >= since);
  const build = async (partial) => {
    const built = await post("/api/build", { events: windowEvents() });
    return { ...built, since, partial, progress: { done, total, phase } };
  };
  let building = Promise.resolve();
  const preview = () => {
    if (onProgress) building = building.then(async () => onProgress(await build(true))).catch(() => {}); // a failed preview must not stop the read
  };

  const run = async (chunks, bodies) => {
    let next = 0;
    const worker = async () => {
      while (next < chunks.length) {
        const chunk = chunks[next++];
        let ok = false;
        for (let attempt = 0; attempt < 2 && !ok; attempt++) {
          try {
            const r = await post("/api/scan", { ids: chunk, bodies });
            Object.assign(store.events, r.events);
            for (const id of Object.keys(r.events)) delete store.pending[id];
            for (const id of r.pending || []) store.pending[id] = 1;
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
        if (next < chunks.length) preview();
      }
    };
    await Promise.all(Array.from({ length: Math.min(parallel, chunks.length) }, worker));
  };

  const fresh = ids.filter((i) => !(i in store.events));
  total = fresh.length;
  await run(chunked(fresh, step), false);

  // pass 2: full text for mails whose decision is hidden after the preview (also retries ones that failed earlier)
  const needBody = Object.keys(store.pending);
  phase = "full text";
  done = 0;
  total = needBody.length;
  if (needBody.length) {
    preview();
    await run(chunked(needBody, bodyStep), true);
  }
  await building;
  phase = "done";
  done = total = ids.length;
  return build(failed > 0);
}
