// Resume / cover letter per application, kept in this browser (IndexedDB), separate for each signed-in user.
const DB = "job-tracker-docs";
const STORE = "files";
export const KINDS = { resume: "Resume", cover: "Cover letter" };
export const MAX_BYTES = 5 * 1024 * 1024;

function open() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function run(mode, fn) {
  const db = await open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, mode);
    const out = fn(tx.objectStore(STORE));
    tx.oncomplete = () => resolve(out && out.result !== undefined ? out.result : undefined);
    tx.onerror = () => reject(tx.error);
  });
}

const key = (email, appId, kind) => `${email}|${appId}|${kind}`;

export const saveDoc = (email, appId, kind, file) =>
  run("readwrite", (s) => s.put({ name: file.name, type: file.type, size: file.size, saved: Date.now(), blob: file }, key(email, appId, kind)));

export const getDoc = (email, appId, kind) => run("readonly", (s) => s.get(key(email, appId, kind)));

export const removeDoc = (email, appId, kind) => run("readwrite", (s) => s.delete(key(email, appId, kind)));

/** Map of applicationId -> list of kinds that have a file, for the signed-in user. */
export async function listDocs(email) {
  const db = await open();
  return new Promise((resolve, reject) => {
    const out = {};
    const req = db.transaction(STORE, "readonly").objectStore(STORE).openKeyCursor();
    req.onsuccess = () => {
      const c = req.result;
      if (!c) return resolve(out);
      const [e, id, kind] = String(c.key).split("|");
      if (e === email) (out[id] = out[id] || []).push(kind);
      c.continue();
    };
    req.onerror = () => reject(req.error);
  });
}
