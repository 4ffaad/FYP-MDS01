import { execFileSync } from "node:child_process";
import { rmSync } from "node:fs";
import { resolve } from "node:path";

export default function globalTeardown() {
  const root = resolve(__dirname, "../../..");
  execFileSync(
    "docker",
    [
      "compose",
      "-p",
      "mds01-security",
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
