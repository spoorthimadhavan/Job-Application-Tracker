import { beforeEach, describe, expect, it, vi } from "vitest";
import { scanApplications } from "./scan.js";

const ev = (id, date = "2026-09-01") => ({ message_id: id, date, status: "R", company: "C" + id });

// ids: what the server lists; events: what each scanned id turns into (null = not a job mail)
function server(ids, events, { version = "v1", fail = () => false, needBody = [], bodyEvents = {} } = {}) {
  const calls = [];
  const post = vi.fn(async (path, body) => {
    calls.push([path, body]);
    if (path === "/api/ids") return { version, ids };
    if (path === "/api/build") return { counts: {}, applications: body.events.map((e) => ({ id: e.message_id })) };
    if (fail(body)) throw new Error("boom");
    const src = body.bodies ? { ...events, ...bodyEvents } : events;
    return {
      version,
      events: Object.fromEntries(body.ids.map((i) => [i, src[i] ?? null])),
      pending: body.bodies ? [] : body.ids.filter((i) => needBody.includes(i)),
    };
  });
  return { post, calls };
}
const scanned = (calls, bodies = false) => calls.filter(([p, b]) => p === "/api/scan" && b.bodies === bodies).flatMap(([, b]) => b.ids);
const built = (calls) => calls.filter(([p]) => p === "/api/build").at(-1)[1].events.map((e) => e.message_id).sort();

describe("scanApplications", () => {
  beforeEach(() => localStorage.clear());

  it("reads the ids in small steps and builds the list", async () => {
    const { post, calls } = server(["a", "b", "c", "d", "e"], { a: ev("a"), c: ev("c"), e: ev("e") });
    const progress = vi.fn();
    const out = await scanApplications("2026-05-01", { email: "u@x.com", step: 2, parallel: 2, onProgress: progress }, post);
    expect(scanned(calls).sort()).toEqual(["a", "b", "c", "d", "e"]);
    expect(calls.filter(([p]) => p === "/api/scan").every(([, b]) => b.ids.length <= 2)).toBe(true);
    expect(progress).toHaveBeenCalled();
    expect(progress.mock.calls[0][0].partial).toBe(true);
    expect(out.partial).toBe(false);
    expect(out.applications.map((a) => a.id).sort()).toEqual(["a", "c", "e"]);
    expect(out.progress).toEqual({ done: 5, total: 5, phase: "done" });
  });

  it("shows the list from previews first, then corrects mails whose decision is in the full text", async () => {
    const { post, calls } = server(["a", "b"], { a: { ...ev("a"), status: "U" }, b: ev("b") }, { needBody: ["a"], bodyEvents: { a: { ...ev("a"), status: "R" } } });
    const progress = vi.fn();
    const out = await scanApplications("2026-05-01", { email: "u@x.com", onProgress: progress, step: 1, parallel: 1 }, post);
    expect(scanned(calls, false).sort()).toEqual(["a", "b"]);
    expect(scanned(calls, true)).toEqual(["a"]); // only the mail that needs it is read in full
    expect(progress.mock.calls.some(([p]) => p.progress.phase === "preview")).toBe(true);
    expect(calls.filter(([p]) => p === "/api/build").at(-1)[1].events.find((e) => e.message_id === "a").status).toBe("R");
    expect(out.partial).toBe(false);
    // a second visit reads nothing again
    const again = server(["a", "b"], {});
    await scanApplications("2026-05-01", { email: "u@x.com" }, again.post);
    expect(again.calls.filter(([p]) => p === "/api/scan")).toHaveLength(0);
  });

  it("remembers mail in the browser and only reads what is new", async () => {
    await scanApplications("2026-05-01", { email: "u@x.com" }, server(["a", "b"], { a: ev("a") }).post);
    const second = server(["a", "b", "c"], { c: ev("c") });
    await scanApplications("2026-05-01", { email: "u@x.com" }, second.post);
    expect(scanned(second.calls)).toEqual(["c"]);
    expect(built(second.calls)).toEqual(["a", "c"]);
  });

  it("starts over when the server rules changed and keeps accounts apart", async () => {
    await scanApplications("2026-05-01", { email: "u@x.com" }, server(["a"], { a: ev("a") }).post);
    const s = server(["a", "z"], { a: ev("a"), z: ev("z") }, { version: "v2" });
    await scanApplications("2026-05-01", { email: "u@x.com" }, s.post);
    expect(scanned(s.calls).sort()).toEqual(["a", "z"]);
    const other = server(["q"], { q: ev("q") });
    await scanApplications("2026-05-01", { email: "other@x.com" }, other.post);
    expect(built(other.calls)).toEqual(["q"]);
  });

  it("cuts the list to the chosen start date", async () => {
    const { post, calls } = server(["a", "b"], { a: ev("a", "2026-03-01"), b: ev("b", "2026-08-01") });
    await scanApplications("2026-05-01", { email: "u@x.com" }, post);
    expect(built(calls)).toEqual(["b"]);
  });

  it("retries a failed step once, then reports partial and keeps the rest", async () => {
    let tries = 0;
    const { post, calls } = server(["a", "b"], { a: ev("a"), b: ev("b") }, { fail: (b) => b.ids.includes("b") && ++tries <= 2 });
    const out = await scanApplications("2026-05-01", { email: "u@x.com", step: 1, parallel: 1 }, post);
    expect(out.partial).toBe(true);
    expect(built(calls)).toEqual(["a"]);
    const again = server(["a", "b"], { b: ev("b") });
    const ok = await scanApplications("2026-05-01", { email: "u@x.com" }, again.post);
    expect(scanned(again.calls)).toEqual(["b"]);
    expect(ok.partial).toBe(false);
  });

  it("passes a signed-out error up", async () => {
    const post = vi.fn(async (path) => {
      if (path === "/api/ids") return { version: "v1", ids: ["a"] };
      const e = new Error("signed-out");
      e.status = 401;
      throw e;
    });
    await expect(scanApplications("2026-05-01", { email: "u@x.com" }, post)).rejects.toMatchObject({ status: 401 });
  });
});
