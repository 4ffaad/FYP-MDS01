import { existsSync } from "node:fs";
import { spawn, spawnSync } from "node:child_process";
import { resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { setup } from "./setup.mjs";

const PROJECT_ROOT = fileURLToPath(new URL("../", import.meta.url));
const BACKEND_HEALTH_URL = "http://127.0.0.1:8000/health";
const FRONTEND_URL = "http://127.0.0.1:3000";
const STARTUP_ATTEMPTS = 1_800;
const HEALTH_RETRY_MS = 1_000;

function delay(milliseconds) {
  return new Promise((resolveDelay) => setTimeout(resolveDelay, milliseconds));
}

export function runCommand(
  command,
  args,
  { cwd, env = process.env, shell = false } = {},
) {
  const result = spawnSync(command, args, {
    cwd,
    env,
    stdio: "inherit",
    shell,
  });

  if (result.error) {
    throw new Error(`Could not start ${command}: ${result.error.message}`);
  }
  if (result.status !== 0) {
    throw new Error(
      `${command} exited with status ${result.status ?? "unknown"}.`,
    );
  }
}

export async function waitForHttp(
  url,
  {
    label = "service",
    maxAttempts = STARTUP_ATTEMPTS,
    intervalMs = HEALTH_RETRY_MS,
    fetchImpl = globalThis.fetch,
    isReady = (response) => response.ok,
    sleep = delay,
    child = null,
    logger = () => {},
    help = "Check the service logs and try again.",
  } = {},
) {
  if (!Number.isInteger(maxAttempts) || maxAttempts < 1) {
    throw new RangeError("maxAttempts must be a positive integer.");
  }

  let lastStatus = "no response";
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    if (child?.startupError) {
      throw new Error(
        `${label} failed to start: ${child.startupError.message}`,
      );
    }
    if (child?.exitCode !== null && child?.exitCode !== undefined) {
      throw new Error(
        `${label} exited before it became ready (code ${child.exitCode}).`,
      );
    }

    try {
      const response = await fetchImpl(url, {
        signal: AbortSignal.timeout(5_000),
      });
      if (await isReady(response)) return response;
      lastStatus = `HTTP ${response.status}`;
    } catch (error) {
      lastStatus =
        error?.name === "TimeoutError" ? "request timed out" : "not reachable";
    }

    if (attempt === 1 || attempt % 30 === 0) {
      logger(`Waiting for ${label} (${attempt}/${maxAttempts} attempts).`);
    }
    if (attempt < maxAttempts) await sleep(intervalMs);
  }

  throw new Error(
    `${label} did not become ready at ${url} (${lastStatus}). ${help}`,
  );
}

function launchFrontend(frontendDir, { platform = process.platform } = {}) {
  const isWindows = platform === "win32";
  const child = spawn(
    isWindows ? "npm.cmd" : "npm",
    ["run", "dev", "--", "--port", "3000"],
    {
      cwd: frontendDir,
      env: process.env,
      shell: isWindows,
      stdio: "inherit",
    },
  );

  child.on("error", (error) => {
    child.startupError = error;
  });
  for (const signal of ["SIGINT", "SIGTERM"]) {
    const forwardSignal = () => child.kill(signal);
    process.once(signal, forwardSignal);
    child.once("exit", () => process.off(signal, forwardSignal));
  }
  return child;
}

export async function startDemo({
  root = PROJECT_ROOT,
  platform = process.platform,
  researchH5 = true,
  run = runCommand,
  initializeConfig = setup,
  hasResearchH5Assets = (projectRoot) =>
    existsSync(resolve(projectRoot, "backend/model/best_seizure_model.h5")) &&
    existsSync(resolve(projectRoot, "backend/model/model-contract.json")),
  hasFrontendDependencies = (frontendDir) =>
    existsSync(resolve(frontendDir, "node_modules/next/package.json")),
  waitForBackend = (logger) =>
    waitForHttp(BACKEND_HEALTH_URL, {
      label: "FastAPI backend",
      maxAttempts: STARTUP_ATTEMPTS,
      intervalMs: HEALTH_RETRY_MS,
      isReady: async (response) => {
        if (!response.ok) return false;
        const body = await response.json().catch(() => null);
        return body?.status === "ok";
      },
      logger,
      help: "Inspect `docker compose ps` and `docker compose logs backend`.",
    }),
  launchFrontend: startFrontend = launchFrontend,
  waitForFrontend = (child, logger) =>
    waitForHttp(FRONTEND_URL, {
      label: "Next.js frontend",
      maxAttempts: 180,
      intervalMs: HEALTH_RETRY_MS,
      child,
      logger,
      help: "Check whether port 3000 is available and inspect the frontend output.",
    }),
  logger = console.log,
} = {}) {
  const nodeMajor = Number(process.versions.node.split(".")[0]);
  if (nodeMajor < 22) {
    throw new Error("Node.js 22 or newer is required to start the demo.");
  }

  if (researchH5 && !hasResearchH5Assets(root)) {
    throw new Error(
      "The local H5 research profile requires the exact ignored model artifact and reviewed contract; no substitute is enabled.",
    );
  }

  run("docker", ["compose", "version"], { cwd: root });
  for (const message of initializeConfig(root)) logger(message);

  const frontendDir = resolve(root, "frontend");
  if (!hasFrontendDependencies(frontendDir)) {
    logger("Installing the locked frontend dependencies...");
    run(platform === "win32" ? "npm.cmd" : "npm", ["ci"], {
      cwd: frontendDir,
      shell: platform === "win32",
    });
  }

  logger(
    researchH5
      ? "Building and starting the pinned local H5 research profile..."
      : "Building and starting PostgreSQL, model assets, and FastAPI...",
  );
  const composeProfileArgs = researchH5
    ? [
        "--profile",
        "local-research",
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.local-research.yml",
      ]
    : ["-f", "docker-compose.yml"];
  const composeRunOptions = { cwd: root };
  if (!researchH5) {
    composeRunOptions.env = { ...process.env, MODEL_RUNTIME: "stub" };
  }
  run(
    "docker",
    ["compose", ...composeProfileArgs, "up", "-d", "--build"],
    composeRunOptions,
  );
  logger("Waiting for the backend health check...");
  await waitForBackend(logger);

  logger("Starting the browser interface...");
  const frontend = startFrontend(frontendDir, { platform });
  frontend?.once?.("exit", (code, signal) => {
    process.exitCode = code ?? (signal === "SIGINT" ? 0 : 1);
  });
  try {
    await waitForFrontend(frontend, logger);
  } catch (error) {
    frontend?.kill?.();
    throw error;
  }

  logger(`MDS01 is ready at ${FRONTEND_URL}.`);
  logger(`Backend health: ${BACKEND_HEALTH_URL}`);
  logger(
    "Sign in or create a local account, then upload only approved demo data.",
  );
  logger(
    "Analysis outputs are research-only; pairing and synchronization are not verified automatically.",
  );
  if (researchH5) {
    logger(
      "H5 scores are uncalibrated and non-diagnostic; the backend validates the pinned artifact and reviewed contract at startup.",
    );
  }
  logger(
    "Ctrl-C stops the frontend. Docker services and their data remain; use `docker compose down` to stop them.",
  );
  return frontend;
}

export function parseDemoOptions(arguments_) {
  const supportedOptions = new Set(["--research-h5", "--development-stub"]);
  const unknownOption = arguments_.find(
    (argument) => !supportedOptions.has(argument),
  );
  if (unknownOption) throw new Error(`Unknown option: ${unknownOption}`);

  if (
    arguments_.includes("--research-h5") &&
    arguments_.includes("--development-stub")
  ) {
    throw new Error("--research-h5 and --development-stub cannot be combined.");
  }

  return { researchH5: !arguments_.includes("--development-stub") };
}

async function main() {
  await startDemo(parseDemoOptions(process.argv.slice(2)));
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(resolve(process.argv[1])).href
) {
  main().catch((error) => {
    console.error(`MDS01 demo startup failed: ${error.message}`);
    process.exitCode = 1;
  });
}
