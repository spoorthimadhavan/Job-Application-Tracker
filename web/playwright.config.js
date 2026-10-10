import { defineConfig, devices } from "@playwright/test";
import fs from "node:fs";

// The e2e suite runs the REAL stack: the built React app served by the FastAPI server,
// signed in through the built-in demo mailbox (no Google keys needed).
const local = "/opt/pw-browsers/chromium";
const executablePath = !process.env.CI && fs.existsSync(local) ? local : undefined;

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: { baseURL: "http://127.0.0.1:8000", trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], launchOptions: { executablePath } } }],
  webServer: {
    command: "python -m uvicorn index:app --app-dir ../api --port 8000 --host 127.0.0.1",
    url: "http://127.0.0.1:8000/api/health",
    reuseExistingServer: !process.env.CI,
    env: { WEB_DIST: "dist", COOKIE_SECURE: "false", SECRET_KEY: "e2e-secret", SINCE: "2026/05/01" },
  },
});
