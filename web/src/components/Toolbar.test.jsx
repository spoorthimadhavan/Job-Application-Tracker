import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import Toolbar from "./Toolbar.jsx";

const base = { query: "", onQuery: () => {}, sort: "newest", onSort: () => {}, range: { choice: "6m", custom: "" }, onRange: () => {}, memberSince: "2026-10-11" };

describe("Toolbar", () => {
  it("shows the sign-up date in the look-back list", () => {
    render(<Toolbar {...base} />);
    expect(screen.getByRole("option", { name: "Since I signed up (2026-10-11)" })).toBeInTheDocument();
  });

  it("reports a new look-back choice", async () => {
    const onRange = vi.fn();
    render(<Toolbar {...base} onRange={onRange} />);
    await userEvent.selectOptions(screen.getByLabelText("Look back"), "1y");
    expect(onRange).toHaveBeenCalledWith({ choice: "1y", custom: "" });
  });

  it("shows a date field only for a custom range", () => {
    const { rerender } = render(<Toolbar {...base} />);
    expect(screen.queryByLabelText("From date")).toBeNull();
    rerender(<Toolbar {...base} range={{ choice: "custom", custom: "2026-01-01" }} />);
    expect(screen.getByLabelText("From date")).toHaveValue("2026-01-01");
  });

  it("reports typing in search and sort changes", async () => {
    const onQuery = vi.fn();
    const onSort = vi.fn();
    render(<Toolbar {...base} onQuery={onQuery} onSort={onSort} />);
    await userEvent.type(screen.getByLabelText("Search company or role"), "x");
    expect(onQuery).toHaveBeenCalledWith("x");
    await userEvent.selectOptions(screen.getByLabelText("Sort"), "company");
    expect(onSort).toHaveBeenCalledWith("company");
  });
});

describe("Toolbar download", () => {
  const base = { query: "", onQuery() {}, sort: "newest", onSort() {}, range: { choice: "3m", custom: "" }, onRange() {} };
  it("is disabled with a hint until the list is completely loaded", () => {
    const { rerender } = render(<Toolbar {...base} canDownload={false} onDownload={() => {}} />);
    const btn = screen.getByRole("button", { name: "Download CSV" });
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute("title", expect.stringMatching(/wait/i));
    rerender(<Toolbar {...base} canDownload onDownload={() => {}} />);
    expect(screen.getByRole("button", { name: "Download CSV" })).toBeEnabled();
  });
});
