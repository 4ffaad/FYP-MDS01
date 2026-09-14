import { execFileSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

export default function globalSetup() {
  process.env.POSTGRES_PASSWORD = randomBytes(24).toString("hex");
  process.env.MDS01_STORAGE_KEY = randomBytes(32).toString("base64");
  process.env.MDS01_TEMPLATE_KEY = randomBytes(32).toString("base64");
  const root = resolve(__dirname, "../../..");
  const containerArchive = "/tmp/mds01-real-e2e.zip";
  const hostArchive = "frontend/test-results/real-e2e.zip";
  mkdirSync(resolve(root, "frontend/test-results"), { recursive: true });
  const compose = [
    "compose",
    "-p",
    "mds01-security",
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
}
