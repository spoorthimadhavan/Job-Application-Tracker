import { beforeEach, describe, expect, it, vi } from "vitest";
import { scanApplications } from "./scan.js";

const ev = (id, date = "2026-09-01") => ({ message_id: id, date, status: "R", company: "C" + id });

function server(batches) {
  const calls = [];
  const post = vi.fn(async (path, body) => {
    calls.push([path, body]);
    if (path === "/api/build") return { counts: {}, applications: body.events.map((e) => ({ id: e.message_id })) };
    const next = batches.shift();
    return { version: "v1", total: 4, ...next };
  });
  return { post, calls };
}

describe("scanApplications", () => {
  beforeEach(() => localStorage.clear());

  it("loops over steps, shows progress and returns the built list", async () => {
    const { post } = server([{ events: { a: ev("a"), b: null }, left: 2 }, { events: { c: ev("c"), d: ev("d") }, left: 0 }]);
    const progress = vi.fn();
    const out = await scanApplications("2026-05-01", { email: "u@x.com", onProgress: progress }, post);
    expect(progress).toHaveBeenCalledTimes(1);
    expect(progress.mock.calls[0][0].partial).toBe(true);
    expect(out.partial).toBe(false);
    expect(out.applications.map((a) => a.id)).toEqual(["a", "c", "d"]);
  });

  it("remembers mail in the browser and only asks for what is new", async () => {
    const first = server([{ events: { a: ev("a"), b: null }, left: 0 }]);
    await scanApplications("2026-05-01", { email: "u@x.com" }, first.post);
    const second = server([{ events: { c: ev("c") }, left: 0 }]);
    await scanApplications("2026-05-01", { email: "u@x.com" }, second.post);
    const scanBody = second.calls.find(([p]) => p === "/api/scan")[1];
    expect(scanBody.known.sort()).toEqual(["a", "b"]);
    const built = second.calls.find(([p]) => p === "/api/build")[1];
    expect(built.events.map((e) => e.message_id).sort()).toEqual(["a", "c"]);
  });

  it("starts over when the server rules changed and keeps accounts apart", async () => {
    await scanApplications("2026-05-01", { email: "u@x.com" }, server([{ events: { a: ev("a") }, left: 0 }]).post);
    const s = server([{ version: "v2", events: { z: ev("z") }, left: 0 }]);
    await scanApplications("2026-05-01", { email: "u@x.com" }, s.post);
    expect(s.calls.find(([p]) => p === "/api/build")[1].events.map((e) => e.message_id)).toEqual(["z"]);
    const other = server([{ events: { q: ev("q") }, left: 0 }]);
    await scanApplications("2026-05-01", { email: "other@x.com" }, other.post);
    expect(other.calls.find(([p]) => p === "/api/scan")[1].known).toEqual([]);
  });

  it("cuts the list to the chosen start date", async () => {
    const { post, calls } = server([{ events: { a: ev("a", "2026-03-01"), b: ev("b", "2026-08-01") }, left: 0 }]);
    await scanApplications("2026-05-01", { email: "u@x.com" }, post);
    expect(calls.find(([p]) => p === "/api/build")[1].events.map((e) => e.message_id)).toEqual(["b"]);
  });

  it("gives up after repeated empty steps and reports partial", async () => {
    vi.useFakeTimers();
    const { post } = server([{ events: {}, left: 3 }, { events: {}, left: 3 }, { events: {}, left: 3 }]);
    const p = scanApplications("2026-05-01", { email: "u@x.com" }, post);
    await vi.runAllTimersAsync();
    expect((await p).partial).toBe(true);
    vi.useRealTimers();
  });
});
