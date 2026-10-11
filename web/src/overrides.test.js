import { beforeEach, describe, expect, it } from "vitest";
import { applyOverrides, loadOverrides, saveOverrides } from "./overrides.js";

const apps = [
  { id: "a", status: "A", check: true, note: "Receipt." },
  { id: "b", status: "R" },
];

describe("manual status", () => {
  beforeEach(() => localStorage.clear());

  it("overrides one application and recounts", () => {
    const { apps: out, counts } = applyOverrides(apps, { a: "I" });
    expect(out[0]).toMatchObject({ status: "I", manual: true, auto: "A", check: false });
    expect(out[1].status).toBe("R");
    expect(counts).toEqual({ I: 1, R: 1 });
  });

  it("keeps choices per account in this browser", () => {
    saveOverrides("x@y.com", { a: "S" });
    expect(loadOverrides("x@y.com")).toEqual({ a: "S" });
    expect(loadOverrides("other@y.com")).toEqual({});
  });
});
