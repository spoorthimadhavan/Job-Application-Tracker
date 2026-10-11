import { useCallback, useEffect, useRef, useState } from "react";
import { getApplications } from "./api.js";

const POLL_MS = 30000;

/** Loads applications and keeps them current: polls every 30s while the tab is visible. */
export function useApplications(enabled, since, onSignedOut) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const timer = useRef();
  const retries = useRef(0);

  // a new look-back range: clear the old list so the numbers never mix
  useEffect(() => setData(null), [since]);

  const load = useCallback(async () => {
    try {
      const d = await getApplications(since);
      setData(d);
      setError("");
      // the server stops early on big mailboxes; ask again soon, it carries on where it stopped
      if (d.partial && retries.current < 8) {
        retries.current += 1;
        setTimeout(load, 1500);
      } else if (!d.partial) retries.current = 0;
    } catch (e) {
      if (e.status === 401) onSignedOut();
      else setError("Could not reach your mailbox. Showing the last result.");
    }
      // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onSignedOut, since]);

  useEffect(() => {
    if (!enabled) return;
    load();
    const tick = () => document.visibilityState === "visible" && load();
    timer.current = setInterval(tick, POLL_MS);
    document.addEventListener("visibilitychange", tick);
    return () => {
      clearInterval(timer.current);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [enabled, load]);

  return { data, error };
}
