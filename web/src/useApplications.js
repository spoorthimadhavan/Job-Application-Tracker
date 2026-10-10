import { useCallback, useEffect, useRef, useState } from "react";
import { getApplications } from "./api.js";

const POLL_MS = 30000;

/** Loads applications and keeps them current: polls every 30s while the tab is visible. */
export function useApplications(enabled, since, onSignedOut) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const timer = useRef();

  // a new look-back range: clear the old list so the numbers never mix
  useEffect(() => setData(null), [since]);

  const load = useCallback(async () => {
    try {
      setData(await getApplications(since));
      setError("");
    } catch (e) {
      if (e.status === 401) onSignedOut();
      else setError("Could not reach your mailbox. Showing the last result.");
    }
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
