import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { getDoc } from "../docs.js";
import Documents from "./Documents.jsx";

describe("Documents", () => {
  it("uploads, shows and removes a resume", async () => {
    const onChange = vi.fn();
    const { container } = render(<Documents email="u@x.com" appId="a1" onChange={onChange} />);
    await waitFor(() => expect(screen.getAllByText("Nothing uploaded")).toHaveLength(2));

    const input = container.querySelectorAll("input[type=file]")[0];
    await userEvent.upload(input, new File(["pdf"], "cv.pdf", { type: "application/pdf" }));
    expect(await screen.findByText(/cv\.pdf/)).toBeInTheDocument();
    expect(onChange).toHaveBeenCalled();
    expect((await getDoc("u@x.com", "a1", "resume")).name).toBe("cv.pdf");

    await userEvent.click(screen.getByRole("button", { name: "Remove" }));
    await waitFor(() => expect(screen.getAllByText("Nothing uploaded")).toHaveLength(2));
  });

  it("rejects files over 5 MB", async () => {
    const { container } = render(<Documents email="u@x.com" appId="a2" onChange={() => {}} />);
    const big = new File(["x"], "big.pdf", { type: "application/pdf" });
    Object.defineProperty(big, "size", { value: 6 * 1024 * 1024 });
    await userEvent.upload(container.querySelectorAll("input[type=file]")[1], big, { applyAccept: false });
    expect(await screen.findByText("File is larger than 5 MB.")).toBeInTheDocument();
    expect(await getDoc("u@x.com", "a2", "cover")).toBeUndefined();
  });
});
