import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import { defineConfig, devices } from "@playwright/test";

const require = createRequire(resolve(process.cwd(), "package.json"));
const { createSecurityComposeProjectName } = require(
  "./tests/real/security-compose-project.cjs",
) as {
  createSecurityComposeProjectName: (options: {
    exists: (projectName: string) => boolean;
  }) => string;
};

function findFreeLoopbackPort(): string {
  return execFileSync(
    process.execPath,
    [
      "-e",
      "const net=require('node:net');const server=net.createServer();server.listen(0,'127.0.0.1',()=>{process.stdout.write(String(server.address().port));server.close();});",
    ],
    { encoding: "utf8" },
  ).trim();
}

const securityPort = process.env.MDS01_SECURITY_PORT ?? findFreeLoopbackPort();
const securityProject = createSecurityComposeProjectName({
  exists: (projectName) =>
    existsSync(resolve(__dirname, "test-results", projectName)),
});
const securityOutputDir = `test-results/${securityProject}`;
const securityApiBaseUrl = `http://127.0.0.1:${securityPort}`;
process.env.MDS01_SECURITY_PORT = securityPort;
process.env.SECURITY_BACKEND_PORT = securityPort;
process.env.MDS01_SECURITY_API_BASE_URL = securityApiBaseUrl;
process.env.MDS01_SECURITY_COMPOSE_PROJECT = securityProject;
export default defineConfig({
  testDir: "./tests/real",
  outputDir: securityOutputDir,
  workers: 1,
  timeout: 150_000,
  reporter: "line",
  globalSetup: "./tests/real/global-setup.ts",
  globalTeardown: "./tests/real/global-teardown.ts",
  use: {
    baseURL: "http://127.0.0.1:3002",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npm run dev -- --hostname 127.0.0.1 --port 3002",
    env: {
      NODE_ENV: "development",
      NEXT_DIST_DIR: ".next-real",
      NEXT_TSCONFIG_PATH: "tsconfig.e2e.json",
      NEXT_PUBLIC_API_BASE_URL: securityApiBaseUrl,
      NEXT_PUBLIC_USE_API_STUB: "false",
      NEXT_PUBLIC_ENABLE_SIGNAL_PREVIEW: "false",
      NEXT_PUBLIC_ENABLE_FULL_SIGNAL_PREVIEW: "false",
    },
    url: "http://127.0.0.1:3002",
    reuseExistingServer: false,
    timeout: 120_000,
  },
  projects: [{ name: "real-backend", use: { ...devices["Desktop Chrome"] } }],
});
