import { useEffect, useRef, useState } from "react";
import { KINDS, MAX_BYTES, getDoc, removeDoc, saveDoc } from "../docs.js";

const ACCEPT = ".pdf,.doc,.docx,.txt,.rtf,.odt";

function Slot({ email, appId, kind, onChange }) {
  const [doc, setDoc] = useState(undefined); // undefined = loading, null = none
  const [err, setErr] = useState("");
  const input = useRef();

  useEffect(() => {
    getDoc(email, appId, kind).then((d) => setDoc(d || null)).catch(() => setDoc(null));
  }, [email, appId, kind]);

  async function pick(e) {
    const file = e.target.files[0];
    e.target.value = "";
    if (!file) return;
    if (file.size > MAX_BYTES) return setErr("File is larger than 5 MB.");
    try {
      await saveDoc(email, appId, kind, file);
      setDoc(await getDoc(email, appId, kind));
      setErr("");
      onChange();
    } catch {
      setErr("This browser could not save the file.");
    }
  }

  function download() {
    const url = URL.createObjectURL(doc.blob);
    const a = Object.assign(document.createElement("a"), { href: url, download: doc.name });
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function remove() {
    await removeDoc(email, appId, kind);
    setDoc(null);
    onChange();
  }

  return (
    <div className="slot">
      <div>
        <b>{KINDS[kind]}</b>
        <p className="muted">{doc === undefined ? "…" : doc ? `${doc.name} · ${Math.max(1, Math.round(doc.size / 1024))} KB` : "Nothing uploaded"}</p>
        {err && <p className="err">{err}</p>}
      </div>
      <div className="slot-actions">
        <input ref={input} type="file" accept={ACCEPT} hidden onChange={pick} />
        <button className="btn small" onClick={() => input.current.click()}>{doc ? "Replace" : "Upload"}</button>
        {doc && <button className="btn ghost small" onClick={download}>Download</button>}
        {doc && <button className="btn ghost small" onClick={remove}>Remove</button>}
      </div>
    </div>
  );
}

export default function Documents({ email, appId, onChange }) {
  return (
    <section className="docs">
      <h3>Documents used for this job</h3>
      {Object.keys(KINDS).map((k) => (
        <Slot key={k} email={email} appId={appId} kind={k} onChange={onChange} />
      ))}
      <p className="fine">Saved in this browser only, for your account. Other devices won't see them.</p>
    </section>
  );
}
