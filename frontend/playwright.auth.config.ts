import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/auth",
  fullyParallel: false,
  workers: 1,
  reporter: "line",
  use: {
    baseURL: "http://127.0.0.1:3003",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npm run dev -- --hostname 127.0.0.1 --port 3003",
    env: {
      NEXT_DIST_DIR: ".next-auth-e2e",
      NEXT_TSCONFIG_PATH: "tsconfig.e2e.json",
      NEXT_PUBLIC_USE_API_STUB: "true",
      NEXT_PUBLIC_AUTH_MODE: "backend",
    },
    url: "http://127.0.0.1:3003",
    reuseExistingServer: false,
    timeout: 120_000,
  },
  projects: [{ name: "auth-desktop", use: { ...devices["Desktop Chrome"] } }],
});
