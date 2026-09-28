import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { test } from "node:test";
import { parseDemoOptions, startDemo, waitForHttp } from "./demo.mjs";

test("the local demo defaults to H5 and keeps the development stub opt-in", () => {
  assert.deepEqual(parseDemoOptions([]), { researchH5: true });
  assert.deepEqual(parseDemoOptions(["--research-h5"]), { researchH5: true });
  assert.deepEqual(parseDemoOptions(["--development-stub"]), {
    researchH5: false,
  });
  assert.throws(
    () => parseDemoOptions(["--research-h5", "--development-stub"]),
    /cannot be combined/,
  );
});

test("the default H5 launcher fails closed before setup if its local assets are absent", async () => {
  const commands = [];
  await assert.rejects(
    startDemo({
      root: "/project",
      run: (...args) => commands.push(args),
      hasResearchH5Assets: () => false,
      initializeConfig: () => [],
    }),
    /exact ignored model artifact and reviewed contract/,
  );
  assert.deepEqual(commands, []);
});

test("demo setup prepares config, installs missing frontend packages, starts Docker, and waits before UI", async () => {
  const events = [];
  const frontend = { exitCode: null };
  await startDemo({
    root: "/project",
    platform: "linux",
    researchH5: false,
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
      [
        "run",
        "docker",
        ["compose", "-f", "docker-compose.yml", "up", "-d", "--build"],
        "/project",
      ],
      ["backend-ready"],
      ["frontend-start", "/project/frontend"],
      ["frontend-ready", true],
    ],
  );
});

test("development stub overrides inherited MODEL_RUNTIME only for the Compose child", async () => {
  const inheritedRuntime = process.env.MODEL_RUNTIME;
  let composeOptions;
  process.env.MODEL_RUNTIME = "h5";
  try {
    await startDemo({
      root: "/project",
      platform: "linux",
      researchH5: false,
      run: (command, args, options) => {
        if (command === "docker" && args.includes("up")) {
          composeOptions = options;
        }
      },
      initializeConfig: () => [],
      hasFrontendDependencies: () => true,
      waitForBackend: async () => {},
      launchFrontend: () => ({ exitCode: null }),
      waitForFrontend: async () => {},
      logger: () => {},
    });

    assert.equal(composeOptions?.env?.MODEL_RUNTIME, "stub");
    assert.equal(process.env.MODEL_RUNTIME, "h5");
  } finally {
    if (inheritedRuntime === undefined) {
      delete process.env.MODEL_RUNTIME;
    } else {
      process.env.MODEL_RUNTIME = inheritedRuntime;
    }
  }
});

test("the default H5 candidate runs through the local research overlay", async () => {
  const commands = [];
  const messages = [];
  await startDemo({
    root: "/project",
    platform: "linux",
    run: (command, args) => commands.push([command, args]),
    initializeConfig: () => [],
    hasResearchH5Assets: () => true,
    hasFrontendDependencies: () => true,
    waitForBackend: async () => {},
    launchFrontend: () => ({ exitCode: null }),
    waitForFrontend: async () => {},
    logger: (message) => messages.push(message),
  });

  assert.deepEqual(commands[1], [
    "docker",
    [
      "compose",
      "--profile",
      "local-research",
      "-f",
      "docker-compose.yml",
      "-f",
      "docker-compose.local-research.yml",
      "up",
      "-d",
      "--build",
    ],
  ]);
  assert.ok(
    messages.some((message) => /uncalibrated and non-diagnostic/.test(message)),
  );
});

test("the H5 research launcher fails closed when the exact local assets are absent", async () => {
  const commands = [];
  await assert.rejects(
    startDemo({
      root: "/project",
      researchH5: true,
      run: (...args) => commands.push(args),
      hasResearchH5Assets: () => false,
      initializeConfig: () => [],
    }),
    /exact ignored model artifact and reviewed contract/,
  );
  assert.deepEqual(commands, []);
});

test("demo setup does not reinstall frontend dependencies already present", async () => {
  const commands = [];
  await startDemo({
    root: "/project",
    platform: "linux",
    researchH5: false,
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
      researchH5: false,
      run: (command, args) => {
        events.push([command, args]);
        if (args[0] === "compose" && args.includes("up")) {
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
      researchH5: false,
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
