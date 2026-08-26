import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

export default function globalSetup() {
  const root = resolve(__dirname, "../../..");
  const compose = ["compose", "-p", "mds01-security", "-f", "docker-compose.security.yml"];
  execFileSync("docker", [...compose, "down", "-v", "--remove-orphans"], { cwd: root, stdio: "inherit" });
  execFileSync("docker", [...compose, "up", "--build", "-d", "--wait"], { cwd: root, stdio: "inherit" });
  execFileSync(
    resolve(root, ".venv/bin/python"),
    ["backend/tests/generate_e2e_archive.py", "frontend/test-results/real-e2e.zip"],
    { cwd: root, stdio: "inherit", env: { ...process.env, PYTHONPATH: "." } },
  );
}
