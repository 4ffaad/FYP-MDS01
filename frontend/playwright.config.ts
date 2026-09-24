import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  // A single Next.js development server compiles routes on demand. Running
  // every browser flow concurrently makes timing assertions flaky.
  fullyParallel: false,
  workers: 1,
  reporter: "html",
  use: {
    baseURL: "http://127.0.0.1:3001",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npm run dev -- --hostname 127.0.0.1 --port 3001",
    env: {
      NODE_ENV: "development",
      NEXT_DIST_DIR: process.env.NEXT_DIST_DIR ?? ".next-e2e",
      NEXT_TSCONFIG_PATH: "tsconfig.e2e.json",
      NEXT_PUBLIC_API_BASE_URL:
        process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000",
      NEXT_PUBLIC_USE_API_STUB: process.env.NEXT_PUBLIC_USE_API_STUB ?? "true",
      NEXT_PUBLIC_AUTH_MODE: process.env.NEXT_PUBLIC_AUTH_MODE ?? "stub",
    },
    url: "http://127.0.0.1:3001",
    reuseExistingServer: false,
    timeout: 120_000,
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["iPhone 13"] } },
  ],
});
