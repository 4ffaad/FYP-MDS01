import { execFileSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

export default function globalSetup() {
  process.env.POSTGRES_PASSWORD = randomBytes(24).toString("hex");
  process.env.MDS01_STORAGE_KEY = randomBytes(32).toString("base64");
  process.env.MDS01_TEMPLATE_KEY = randomBytes(32).toString("base64");
  if (!process.env.MDS01_SECURITY_PORT) {
    throw new Error("MDS01_SECURITY_PORT is required");
  }
  process.env.SECURITY_BACKEND_PORT = process.env.MDS01_SECURITY_PORT;
  const root = resolve(__dirname, "../../..");
  const securityProject =
    process.env.MDS01_SECURITY_COMPOSE_PROJECT ?? "mds01-security";
  const containerArchive = "/app/backend/storage/.mds01-real-e2e.zip";
  const hostArchive = "frontend/test-results/real-e2e.zip";
  mkdirSync(resolve(root, "frontend/test-results"), { recursive: true });
  const compose = [
    "compose",
    "-p",
    securityProject,
    "-f",
    "docker-compose.security.yml",
  ];
  execFileSync("docker", [...compose, "down", "-v", "--remove-orphans"], {
    cwd: root,
    stdio: "inherit",
  });
  execFileSync("docker", [...compose, "up", "--build", "-d", "--wait"], {
    cwd: root,
    stdio: "inherit",
  });
  execFileSync(
    "docker",
    [
      ...compose,
      "exec",
      "-T",
      "backend",
      "python",
      "backend/tests/generate_e2e_archive.py",
      containerArchive,
    ],
    { cwd: root, stdio: "inherit" },
  );
  execFileSync(
    "docker",
    [...compose, "cp", `backend:${containerArchive}`, hostArchive],
    {
      cwd: root,
      stdio: "inherit",
    },
  );
  execFileSync(
    "docker",
    [...compose, "exec", "-T", "backend", "rm", "-f", containerArchive],
    { cwd: root, stdio: "inherit" },
  );
}
