import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.jsx";
import * as api from "./api.js";
import { apps, counts } from "./test/fixtures.js";

vi.mock("./api.js");

const payload = { updated_at: Date.now() / 1000, since: "2026-04-11", counts, applications: apps };

function signedIn() {
  api.getMe.mockResolvedValue({ email: "me@example.com", demo: false, member_since: "2026-10-01", google_configured: true });
  api.getApplications.mockResolvedValue(payload);
  api.getEmail.mockResolvedValue({ id: "m2", subject: "Your application to Frontend Developer at Contoso", from: "LinkedIn", date: "2026-09-20T10:00:00Z", html: null, text: "Thank you for your interest", gmail_url: "https://mail.google.com/x" });
  api.logout.mockResolvedValue({ ok: true });
}

beforeEach(() => vi.resetAllMocks());

describe("App", () => {
  it("shows the login page when signed out", async () => {
    api.getMe.mockResolvedValue({ email: null, google_configured: true });
    render(<App />);
    expect(await screen.findByRole("link", { name: "Sign in with Google" })).toHaveAttribute("href", "/api/auth/login");
    expect(screen.getByRole("link", { name: "Try the demo" })).toBeInTheDocument();
  });

  it("explains when Google sign-in is not configured", async () => {
    api.getMe.mockResolvedValue({ email: null, google_configured: false });
    render(<App />);
    expect(await screen.findByText(/not set up on this server/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Sign in with Google" })).toBeNull();
  });

  it("loads applications for the chosen look-back range", async () => {
    signedIn();
    render(<App />);
    expect(await screen.findByText("Contoso")).toBeInTheDocument();
    expect(api.getApplications).toHaveBeenCalledWith(expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/), expect.anything());
    await userEvent.selectOptions(screen.getByLabelText("Look back"), "all");
    await waitFor(() => expect(api.getApplications).toHaveBeenLastCalledWith("2004-01-01", expect.anything()));
  });

  it("filters by tile and by search text", async () => {
    signedIn();
    render(<App />);
    await screen.findByText("Contoso");
    await userEvent.click(screen.getByRole("button", { name: /^1\s*Rejected$/ }));
    expect(screen.queryByText("Wide World")).toBeNull();
    expect(screen.getByText("Contoso")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /^1\s*Rejected$/ })); // click again = all
    expect(screen.getByText("Wide World")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Search company or role"), "tail");
    expect(screen.getByText("Tailspin Toys")).toBeInTheDocument();
    expect(screen.queryByText("Contoso")).toBeNull();
  });

  it("sorts by company name", async () => {
    signedIn();
    render(<App />);
    await screen.findByText("Contoso");
    await userEvent.selectOptions(screen.getByLabelText("Sort"), "company");
    const names = screen.getAllByRole("button").filter((b) => b.className === "row").map((b) => within(b).getByText(/Contoso|Northwind|Tailspin|Wide World/).textContent);
    expect(names).toEqual(["Contoso", "Northwind Labs", "Tailspin Toys", "Wide World"]);
  });

  it("opens the email copy and closes it with Escape", async () => {
    signedIn();
    render(<App />);
    await userEvent.click(await screen.findByText("Contoso"));
    expect(await screen.findByText("Thank you for your interest")).toBeInTheDocument();
    expect(api.getEmail).toHaveBeenCalledWith("m2");
    expect(screen.getByRole("link", { name: "Open in Gmail" })).toHaveAttribute("href", "https://mail.google.com/x");
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("shows a friendly message when the mailbox cannot be read", async () => {
    signedIn();
    api.getApplications.mockRejectedValue(Object.assign(new Error("x"), { status: 502 }));
    render(<App />);
    expect(await screen.findByText(/Could not reach your mailbox/)).toBeInTheDocument();
  });

  it("returns to the login page when the session expires", async () => {
    signedIn();
    api.getApplications.mockRejectedValue(Object.assign(new Error("signed-out"), { status: 401 }));
    render(<App />);
    expect(await screen.findByRole("link", { name: "Try the demo" })).toBeInTheDocument();
  });

  it("signs out", async () => {
    signedIn();
    render(<App />);
    await screen.findByText("Contoso");
    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(api.logout).toHaveBeenCalled();
    expect(await screen.findByRole("link", { name: "Try the demo" })).toBeInTheDocument();
  });
});
