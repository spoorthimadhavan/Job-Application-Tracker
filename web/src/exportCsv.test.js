import { describe, expect, it } from "vitest";
import { toCsv } from "./exportCsv.js";

describe("toCsv", () => {
  it("writes one quoted line per application with its mails", () => {
    const csv = toCsv([{ date: "2026-10-01", company: 'A "B"', role: "Dev", status: "R", sender: "x@y.z", events: [{ date: "2026-10-01", status: "R", subject: "Absage" }] }]);
    const [head, row] = csv.split("\n");
    expect(head).toContain('"company"');
    expect(row).toBe('"2026-10-01","A ""B""","Dev","R","x@y.z","2026-10-01 R Absage"');
  });
});
