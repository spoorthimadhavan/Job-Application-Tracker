import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import TopBar from "./TopBar.jsx";

describe("TopBar", () => {
  it("shows when the mailbox was last checked and offers Refresh now", async () => {
    const onRefresh = vi.fn();
    render(<TopBar email="a@b.c" updatedAt={Date.now() / 1000 - 42} onLogout={() => {}} onRefresh={onRefresh} />);
    expect(screen.getByText(/checked 4\ds ago/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Refresh now" }));
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });
});
