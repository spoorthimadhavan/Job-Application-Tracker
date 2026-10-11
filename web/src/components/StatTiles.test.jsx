import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import StatTiles from "./StatTiles.jsx";

describe("StatTiles", () => {
  it("shows all tiles in order, including empty ones", () => {
    render(<StatTiles counts={{ R: 3 }} total={3} active="all" onPick={() => {}} />);
    const labels = screen.getAllByRole("button").map((b) => b.querySelector("span").textContent);
    expect(labels).toEqual([
      "All",
      "Selected",
      "Rejected",
      "Rejected after interview",
      "Rejected, no response (6–8 weeks)",
      "Under review",
      "Applied (up to 6 weeks)",
      "Withdrawn by me",
      "Account created and not applied",
    ]);
    expect(screen.getByRole("button", { name: /^3\s*Rejected$/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^0\s*Selected$/ })).toBeInTheDocument();
  });

  it("marks the active tile and reports clicks", async () => {
    const onPick = vi.fn();
    render(<StatTiles counts={{ R: 1 }} total={1} active="R" onPick={onPick} />);
    expect(screen.getByRole("button", { name: /Rejected$/ })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(screen.getByRole("button", { name: /Under review/ }));
    expect(onPick).toHaveBeenCalledWith("U");
  });
});
