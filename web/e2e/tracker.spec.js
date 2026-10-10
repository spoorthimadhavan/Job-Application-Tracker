import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Try the demo" }).click();
  await expect(page.getByText("Demo data")).toBeVisible();
  await expect(page.locator(".row").first()).toBeVisible();
});

test("signed-out visitors see the login page", async ({ browser }) => {
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Job Application Tracker" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Try the demo" })).toBeVisible();
  await ctx.close();
});

test("tiles appear in the agreed order with the agreed labels", async ({ page }) => {
  const labels = await page.locator(".stat span").allTextContents();
  expect(labels).toEqual([
    "All",
    "Selected",
    "Rejected",
    "Rejected after interview",
    "Rejected, no response (6–8 weeks)",
    "Under review",
    "Applied (up to 6 weeks)",
    "Account created and not applied",
  ]);
});

test("clicking a tile filters the list and clicking again clears it", async ({ page }) => {
  const total = await page.locator(".row").count();
  const tile = page.locator(".stat", { hasText: "Rejected after interview" });
  await tile.click();
  await expect(tile).toHaveAttribute("aria-pressed", "true");
  const filtered = await page.locator(".row").count();
  expect(filtered).toBeLessThan(total);
  await tile.click();
  await expect(page.locator(".row")).toHaveCount(total);
});

test("search narrows the list", async ({ page }) => {
  const total = await page.locator(".row").count();
  await page.getByLabel("Search company or role").fill("zzz-no-such-company");
  await expect(page.getByText("Nothing matches")).toBeVisible();
  await page.getByLabel("Search company or role").fill("");
  await expect(page.locator(".row")).toHaveCount(total);
});

test("look-back offers the signup, months, years and custom choices", async ({ page }) => {
  const options = await page.getByLabel("Look back").locator("option").allTextContents();
  expect(options.join(" ")).toMatch(/signed up/i);
  expect(options.join(" ")).toMatch(/month/i);
  expect(options.join(" ")).toMatch(/year/i);
  expect(options.join(" ")).toMatch(/custom/i);
  await page.getByLabel("Look back").selectOption("custom");
  await expect(page.getByLabel("From date")).toBeVisible();
});

test("a row opens the email copy and Escape closes it", async ({ page }) => {
  await page.locator(".row").first().click();
  const drawer = page.getByRole("dialog", { name: "Email" });
  await expect(drawer).toBeVisible();
  await expect(drawer.locator("section.mail")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(drawer).toBeHidden();
});

test("a resume can be attached to a job and survives a reload", async ({ page }) => {
  await page.locator(".row").first().click();
  const drawer = page.getByRole("dialog", { name: "Email" });
  await drawer.locator("input[type=file]").first().setInputFiles({ name: "my-cv.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4 test") });
  await expect(drawer.getByText(/my-cv\.pdf/)).toBeVisible();
  await drawer.getByRole("button", { name: "Close" }).click();
  await expect(page.locator(".row .clip").first()).toBeVisible();

  await page.reload();
  await expect(page.locator(".row .clip").first()).toBeVisible();
});

test("signing out returns to the login page", async ({ page }) => {
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("link", { name: "Try the demo" })).toBeVisible();
});

test("API rejects anonymous calls", async ({ playwright }) => {
  const api = await playwright.request.newContext({ baseURL: "http://127.0.0.1:8000" });
  expect((await api.get("/api/applications")).status()).toBe(401);
  expect((await api.get("/api/health")).ok()).toBeTruthy();
  await api.dispose();
});
