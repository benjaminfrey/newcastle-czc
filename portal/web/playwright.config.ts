import { defineConfig, devices } from "@playwright/test";

// Journeys run against a live dev stack on the VM (see portal/README.md):
//   PORTAL_E2E_URL=http://127.0.0.1:5173 PORTAL_E2E_MAILPIT=http://127.0.0.1:8025 npm run e2e
export default defineConfig({
  testDir: "./e2e",
  timeout: 240_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: process.env.PORTAL_E2E_URL ?? "http://127.0.0.1:5173", trace: "retain-on-failure", actionTimeout: 15_000 },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } } },
    { name: "phone", use: { ...devices["Pixel 7"] } },
  ],
});
