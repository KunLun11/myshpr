import { defineConfig, devices } from "@playwright/test";

/**
 * E2E runs against a real stack (Postgres + FastAPI + Next.js), usually the
 * one started by `deploy/docker-compose.yml`. The seed must be applied first.
 *
 *   make up          # or docker compose -f deploy/docker-compose.yml up
 *   make test-e2e    # npx playwright test
 *
 * `E2E_BASE_URL` overrides the target (default http://localhost:3000).
 * Tests are intentionally serial: they share one school, one teacher and the
 * duplicate-topic registry, so parallel workers would race.
 */
const baseURL = process.env.E2E_BASE_URL ?? "http://localhost:3000";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
  ],
  outputDir: "e2e-results",
  use: {
    baseURL,
    locale: "ru-RU",
    timezoneId: "Europe/Moscow",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
