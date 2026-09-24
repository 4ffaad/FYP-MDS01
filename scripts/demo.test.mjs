import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { test } from "node:test";
import { startDemo, waitForHttp } from "./demo.mjs";

test("demo setup prepares config, installs missing frontend packages, starts Docker, and waits before UI", async () => {
  const events = [];
  const frontend = { exitCode: null };
  await startDemo({
    root: "/project",
    platform: "linux",
    run: (command, args, options) => {
      events.push(["run", command, args, options.cwd]);
    },
    initializeConfig: () => {
      events.push(["setup"]);
      return ["Created .env"];
    },
    hasFrontendDependencies: () => false,
    waitForBackend: async () => events.push(["backend-ready"]),
    launchFrontend: (directory) => {
      events.push(["frontend-start", directory]);
      return frontend;
    },
    waitForFrontend: async (child) =>
      events.push(["frontend-ready", child === frontend]),
    logger: () => {},
  });

  assert.deepEqual(
    events.filter(([kind]) => kind !== "log"),
    [
      ["run", "docker", ["compose", "version"], "/project"],
      ["setup"],
      ["run", "npm", ["ci"], "/project/frontend"],
      ["run", "docker", ["compose", "up", "-d", "--build"], "/project"],
      ["backend-ready"],
      ["frontend-start", "/project/frontend"],
      ["frontend-ready", true],
    ],
  );
});

test("demo setup does not reinstall frontend dependencies already present", async () => {
  const commands = [];
  await startDemo({
    root: "/project",
    platform: "linux",
    run: (command, args) => commands.push([command, args]),
    initializeConfig: () => [],
    hasFrontendDependencies: () => true,
    waitForBackend: async () => {},
    launchFrontend: () => ({ exitCode: null }),
    waitForFrontend: async () => {},
    logger: () => {},
  });

  assert.equal(
    commands.some(([command, args]) => command === "npm" && args[0] === "ci"),
    false,
  );
});

test("demo startup stops on Docker failure instead of leaving a frontend-only demo", async () => {
  const events = [];
  await assert.rejects(
    startDemo({
      root: "/project",
      platform: "linux",
      run: (command, args) => {
        events.push([command, args]);
        if (args[0] === "compose" && args[1] === "up") {
          throw new Error("compose failed");
        }
      },
      initializeConfig: () => [],
      hasFrontendDependencies: () => true,
      waitForBackend: async () => events.push(["backend-ready"]),
      launchFrontend: () => events.push(["frontend-start"]),
      waitForFrontend: async () => {},
      logger: () => {},
    }),
    /compose failed/,
  );
  assert.equal(
    events.some(([kind]) => kind === "backend-ready"),
    false,
  );
  assert.equal(
    events.some(([kind]) => kind === "frontend-start"),
    false,
  );
});

test("health wait retries transient failures and returns on a healthy response", async () => {
  const responses = [
    { ok: false, status: 503 },
    { ok: true, status: 200 },
  ];
  let sleeps = 0;
  await waitForHttp("http://127.0.0.1:8000/health", {
    label: "FastAPI",
    maxAttempts: 3,
    intervalMs: 1,
    fetchImpl: async () => responses.shift(),
    isReady: (response) => response.ok,
    sleep: async () => {
      sleeps += 1;
    },
    logger: () => {},
  });
  assert.equal(sleeps, 1);
  assert.equal(responses.length, 0);
});

test("demo process preserves a nonzero frontend exit status", async () => {
  const originalExitCode = process.exitCode;
  const frontend = new EventEmitter();
  frontend.exitCode = null;
  frontend.kill = () => {};
  try {
    await startDemo({
      root: "/project",
      platform: "linux",
      run: () => {},
      initializeConfig: () => [],
      hasFrontendDependencies: () => true,
      waitForBackend: async () => {},
      launchFrontend: () => frontend,
      waitForFrontend: async () => {},
      logger: () => {},
    });
    frontend.emit("exit", 7, null);
    assert.equal(process.exitCode, 7);
  } finally {
    process.exitCode = originalExitCode ?? 0;
  }
});
