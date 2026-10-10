import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PRESETS, loadRange, saveRange, sinceFor } from "./range.js";

describe("look-back range", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-11T12:00:00"));
  });
  afterEach(() => vi.useRealTimers());

  it("maps presets to start dates", () => {
    expect(sinceFor("1m")).toBe("2026-09-11");
    expect(sinceFor("3m")).toBe("2026-07-11");
    expect(sinceFor("6m")).toBe("2026-04-11");
    expect(sinceFor("1y")).toBe("2025-10-11");
    expect(sinceFor("all")).toBe("2004-01-01");
  });

  it("uses the sign-up day for 'signup' and falls back to today", () => {
    expect(sinceFor("signup", "", "2026-08-02")).toBe("2026-08-02");
    expect(sinceFor("signup", "", null)).toBe("2026-10-11");
  });

  it("accepts a custom date but never one in the future", () => {
    expect(sinceFor("custom", "2026-01-05")).toBe("2026-01-05");
    expect(sinceFor("custom", "2999-01-01")).toBe("2026-04-11");
    expect(sinceFor("custom", "")).toBe("2026-04-11");
  });

  it("falls back to 6 months for an unknown choice", () => {
    expect(sinceFor("nonsense")).toBe("2026-04-11");
  });

  it("remembers the choice in localStorage and ignores junk", () => {
    expect(loadRange()).toEqual({ choice: "6m", custom: "" });
    saveRange({ choice: "1y", custom: "" });
    expect(loadRange().choice).toBe("1y");
    localStorage.setItem("jt-range", "{broken");
    expect(loadRange().choice).toBe("6m");
    localStorage.setItem("jt-range", JSON.stringify({ choice: "weird" }));
    expect(loadRange().choice).toBe("6m");
  });

  it("offers every preset exactly once", () => {
    expect(new Set(PRESETS.map((p) => p.id)).size).toBe(PRESETS.length);
  });
});
