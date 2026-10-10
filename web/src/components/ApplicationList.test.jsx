import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { apps } from "../test/fixtures.js";
import ApplicationList from "./ApplicationList.jsx";

describe("ApplicationList", () => {
  it("renders one row per application with date, status and note", () => {
    render(<ApplicationList apps={apps} total={4} loading={false} docs={{}} onOpen={() => {}} />);
    expect(screen.getAllByRole("button")).toHaveLength(4);
    expect(screen.getByText("Wide World")).toBeInTheDocument();
    expect(screen.getByText("7 Oct 2026")).toBeInTheDocument();
    expect(screen.getByText("Selected")).toBeInTheDocument();
    expect(screen.getByText("4 of 4 applications.", { exact: false })).toBeInTheDocument();
  });

  it("flags rows that need a manual check", () => {
    render(<ApplicationList apps={apps} total={4} loading={false} docs={{}} onOpen={() => {}} />);
    expect(screen.getAllByText("check")).toHaveLength(1);
  });

  it("shows a badge for rows with uploaded documents", () => {
    render(<ApplicationList apps={apps} total={4} loading={false} docs={{ 1: ["resume", "cover"], 2: ["resume"] }} onOpen={() => {}} />);
    expect(screen.getByText("2 files")).toBeInTheDocument();
    expect(screen.getByText("1 file")).toBeInTheDocument();
  });

  it("opens a row on click", async () => {
    const onOpen = vi.fn();
    render(<ApplicationList apps={apps} total={4} loading={false} docs={{}} onOpen={onOpen} />);
    await userEvent.click(screen.getByText("Contoso"));
    expect(onOpen).toHaveBeenCalledWith(apps[1]);
  });

  it("handles loading and empty results", () => {
    const { rerender } = render(<ApplicationList apps={[]} total={0} loading docs={{}} onOpen={() => {}} />);
    expect(screen.getByText("Reading your mailbox…")).toBeInTheDocument();
    rerender(<ApplicationList apps={[]} total={4} loading={false} docs={{}} onOpen={() => {}} />);
    expect(screen.getByText(/Nothing matches/)).toBeInTheDocument();
  });
});
