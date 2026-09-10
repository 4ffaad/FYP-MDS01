import { existsSync, mkdirSync, readFileSync } from "node:fs";
import { spawn, spawnSync } from "node:child_process";
import { resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export function readDotEnv(path) {
  if (!existsSync(path)) return {};
  return Object.fromEntries(readFileSync(path, "utf8").split(/\r?\n/).flatMap((line) => {
    const value = line.trim().replace(/^export\s+/, "");
    const index = value.indexOf("=");
    if (!value || value.startsWith("#") || index < 1) return [];
    const key = value.slice(0, index).trim();
    let parsed = value.slice(index + 1).trim();
    if ((parsed.startsWith('"') && parsed.endsWith('"')) || (parsed.startsWith("'") && parsed.endsWith("'"))) parsed = parsed.slice(1, -1);
    return [[key, parsed]];
  }));
}

export function nativeEnvironment(root, inherited = process.env) {
  const env = { ...readDotEnv(resolve(root, ".env")), ...inherited };
  env.DATABASE_URL ||= `sqlite:///${resolve(root, "backend/database/eeg.db")}`;
  env.STORAGE_DIR ||= resolve(root, "backend/storage");
  env.VIDEO_DETECTION_ENABLED ||= "true";
  env.MPLCONFIGDIR ||= resolve(root, ".cache/matplotlib");
  mkdirSync(env.MPLCONFIGDIR, { recursive: true });
  return env;
}

export function findPython(root, inherited = process.env) {
  const candidates = [
    inherited.PYTHON,
    resolve(root, ".venv/bin/python"),
    resolve(root, ".venv/Scripts/python.exe"),
    "python3.12",
    "python3",
    "python",
  ].filter(Boolean);
  const python = candidates.find((candidate) => spawnSync(candidate, ["--version"], { stdio: "ignore" }).status === 0);
  if (!python) throw new Error("Python 3.12 was not found. Create .venv or set PYTHON=/path/to/python.");
  return python;
}

export function startNative(root = resolve(fileURLToPath(new URL("../", import.meta.url)))) {
  const env = nativeEnvironment(root);
  const python = findPython(root, env);
  const migration = spawnSync(python, ["-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"], {
    cwd: root,
    env,
    stdio: "inherit",
  });
  if (migration.status !== 0) process.exit(migration.status ?? 1);
  const server = spawn(python, ["-m", "uvicorn", "backend.app.main:app", "--reload", "--reload-dir", "backend", "--host", "127.0.0.1", "--port", env.API_PORT || "8000"], {
    cwd: root,
    env,
    stdio: "inherit",
  });
  for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => server.kill(signal));
  server.on("exit", (code) => process.exit(code ?? 1));
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) startNative();
