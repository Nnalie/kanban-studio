import { defineConfig, devices } from "@playwright/test";

const useIntegrated =
  process.env.E2E_MODE === "integrated" || process.env.CI === "true";

export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: useIntegrated ? "http://127.0.0.1:8000" : "http://127.0.0.1:3000",
    trace: "retain-on-failure",
  },
  webServer: useIntegrated
    ? {
        command: "bash ../scripts/serve-built.sh",
        url: "http://127.0.0.1:8000",
        reuseExistingServer: true,
        timeout: 300_000,
      }
    : {
        command: "npm run dev -- --hostname 127.0.0.1 --port 3000",
        url: "http://127.0.0.1:3000",
        reuseExistingServer: true,
        timeout: 120_000,
      },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        channel: "chrome",
      },
    },
  ],
});
