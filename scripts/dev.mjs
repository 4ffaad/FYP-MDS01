import { existsSync } from "node:fs";
import { spawn, spawnSync } from "node:child_process";
import { resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { setup } from "./setup.mjs";

const PROJECT_ROOT = fileURLToPath(new URL("../", import.meta.url));

function runCommand(command, args, { cwd, shell = false } = {}) {
  const result = spawnSync(command, args, { cwd, shell, stdio: "inherit" });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(
      `${command} exited with status ${result.status ?? "unknown"}.`,
    );
  }
}

export function ensureFrontendDependencies({
  root = PROJECT_ROOT,
  platform = process.platform,
  hasFrontendDependencies = (frontendDir) =>
    existsSync(resolve(frontendDir, "node_modules/next/package.json")),
  run = runCommand,
} = {}) {
  const frontendDir = resolve(root, "frontend");
  if (hasFrontendDependencies(frontendDir)) return false;

  run(platform === "win32" ? "npm.cmd" : "npm", ["ci"], {
    cwd: frontendDir,
    shell: platform === "win32",
  });
  return true;
}

function startFrontend({
  root = PROJECT_ROOT,
  args = process.argv.slice(2),
} = {}) {
  const frontendDir = resolve(root, "frontend");
  const isWindows = process.platform === "win32";
  const child = spawn(
    isWindows ? "npm.cmd" : "npm",
    ["run", "dev", ...(args.length ? ["--", ...args] : [])],
    { cwd: frontendDir, env: process.env, shell: isWindows, stdio: "inherit" },
  );

  child.once("error", (error) => {
    console.error(`Could not start the frontend: ${error.message}`);
    process.exitCode = 1;
  });

  for (const signal of ["SIGINT", "SIGTERM"]) {
    const forwardSignal = () => child.kill(signal);
    process.once(signal, forwardSignal);
    child.once("exit", () => process.off(signal, forwardSignal));
  }

  child.once("exit", (code, signal) => {
    process.exitCode = code ?? (signal === "SIGINT" ? 0 : 1);
  });
}

export function prepareDev({ root = PROJECT_ROOT, ...options } = {}) {
  const messages = setup(root);
  const installed = ensureFrontendDependencies({ root, ...options });
  return { messages, installed };
}

async function main() {
  const nodeMajor = Number(process.versions.node.split(".")[0]);
  if (nodeMajor < 22) {
    throw new Error("Node.js 22 or newer is required to start the frontend.");
  }

  const { messages, installed } = prepareDev();
  for (const message of messages) console.log(message);
  if (installed) console.log("Installed the locked frontend dependencies.");
  console.log("Starting the frontend at http://127.0.0.1:3000.");
  console.log(
    "Run `docker compose up --build` in another terminal for the backend.",
  );
  startFrontend();
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(resolve(process.argv[1])).href
) {
  main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
