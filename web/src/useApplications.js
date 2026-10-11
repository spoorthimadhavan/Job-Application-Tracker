import { useCallback, useEffect, useRef, useState } from "react";
import { getApplications } from "./api.js";

const POLL_MS = 30000;

/** Loads applications and keeps them current: polls every 30s while the tab is visible.
 *  The first load reads the mailbox in steps and shows the list as it fills; later polls only fetch new mail. */
export function useApplications(enabled, since, onSignedOut, email) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const timer = useRef();
  const latest = useRef(since);
  const running = useRef("");
  const retries = useRef(0);

  // a new look-back range: clear the old list so the numbers never mix
  useEffect(() => setData(null), [since]);

  const load = useCallback(async () => {
    latest.current = since;
    if (running.current === since) return; // a read of this range is already in progress
    running.current = since;
    try {
      const d = await getApplications(since, { email, onProgress: (p) => {
          if (latest.current !== since) return;
          setData(p);
          setError("");
        },
      });
      if (latest.current !== since) return;
      setData(d);
      setError("");
      // Gmail kept refusing some mail: try again shortly, it carries on where it stopped
      if (d.partial && retries.current < 8) {
        retries.current += 1;
        setTimeout(() => {
          running.current = "";
          load();
        }, 3000);
      } else if (d.partial) {
        // Gmail still refuses a few mails after several tries: stop the spinner and show what we have
        setData({ ...d, partial: false, skipped: true });
      } else retries.current = 0;
    } catch (e) {
      if (e.status === 401) onSignedOut();
      else {
        setError("Could not reach your mailbox. Showing the last result.");
        // never leave the page "reading" after a failure: show what we have, the next 30 s refresh tries again
        setData((d) => (d && d.partial ? { ...d, partial: false, skipped: true } : d));
      }
    } finally {
      if (running.current === since) running.current = "";
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onSignedOut, since, email]);

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
