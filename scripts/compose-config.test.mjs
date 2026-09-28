import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const PROJECT_ROOT = fileURLToPath(new URL("../", import.meta.url));

test("merged local research Compose config exposes no writable EEG model mounts", () => {
  const composeEnvironment = {
    PATH: process.env.PATH,
    HOME: process.env.HOME,
    POSTGRES_PASSWORD: "compose-config-test-only",
    MDS01_STORAGE_KEY: "compose-config-test-only-storage-key",
    MDS01_TEMPLATE_KEY: "compose-config-test-only-template-key",
    VSVIG_CONTRACT_SHA256: "0".repeat(64),
  };
  const result = spawnSync(
    "docker",
    [
      "compose",
      "--env-file",
      "/dev/null",
      "--profile",
      "local-research",
      "-f",
      "docker-compose.yml",
      "-f",
      "docker-compose.local-research.yml",
      "config",
      "--format",
      "json",
    ],
    {
      cwd: resolve(PROJECT_ROOT),
      env: composeEnvironment,
      encoding: "utf8",
    },
  );

  assert.equal(result.error, undefined, "Docker Compose CLI must be available");
  assert.equal(result.status, 0, "merged Compose configuration must be valid");

  const config = JSON.parse(result.stdout);
  assert.equal(
    config.services.backend.environment.VSVIG_ALLOW_LETTERBOX_ADAPTATION,
    "true",
    "the local H5 profile must adapt smaller clips to VSViG geometry",
  );
  const modelMounts = config.services.backend.volumes.filter(({ target }) =>
    target === "/opt/eeg-model" || target.startsWith("/opt/eeg-model/"),
  );
  assert.ok(modelMounts.length > 0, "the research model must remain mounted");
  for (const mount of modelMounts) {
    assert.equal(
      mount.read_only,
      true,
      `model mount at ${mount.target} must be read-only`,
    );
  }
});
