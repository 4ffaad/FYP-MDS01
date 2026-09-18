import { execFileSync } from "node:child_process";
import { rmSync } from "node:fs";
import { resolve } from "node:path";

export default function globalTeardown() {
  const root = resolve(__dirname, "../../..");
  const securityProject =
    process.env.MDS01_SECURITY_COMPOSE_PROJECT ?? "mds01-security";
  execFileSync(
    "docker",
    [
      "compose",
      "-p",
      securityProject,
      "-f",
      "docker-compose.security.yml",
      "down",
      "-v",
      "--remove-orphans",
    ],
    { cwd: root, stdio: "inherit" },
  );
  rmSync(resolve(root, "frontend/test-results/real-e2e.zip"), { force: true });
}
