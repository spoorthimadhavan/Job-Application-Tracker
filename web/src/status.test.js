import { describe, expect, it } from "vitest";
import { STATUS, TILE_ORDER, formatDate } from "./status.js";

describe("status", () => {
  it("lists the tiles in the agreed order", () => {
    expect(TILE_ORDER.map((k) => STATUS[k].tile)).toEqual([
      "Selected",
      "Rejected",
      "Rejected after interview",
      "Rejected, no response (6–8 weeks)",
      "Under review",
      "Applied (up to 6 weeks)",
      "Account created and not applied",
    ]);
  });

  it("gives every status a label and a colour", () => {
    for (const k of TILE_ORDER) {
      expect(STATUS[k].label).toBeTruthy();
      expect(STATUS[k].color).toBeTruthy();
    }
  });

  it("formats dates without timezone drift", () => {
    expect(formatDate("2026-10-01")).toBe("1 Oct 2026");
    expect(formatDate("2026-01-31")).toBe("31 Jan 2026");
  });
});
