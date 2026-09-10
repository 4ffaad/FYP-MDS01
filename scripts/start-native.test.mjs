import assert from "node:assert/strict";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { nativeEnvironment, readDotEnv } from "./start-native.mjs";

test("native mode loads local config, keeps explicit shell values, and defaults to SQLite", () => {
  const root = mkdtempSync(join(tmpdir(), "mds01-native-test-"));
  try {
    writeFileSync(join(root, ".env"), "AUTH_MODE=local-accounts\nDATABASE_URL=\"sqlite:///from-file.db\"\n# ignored\n");
    assert.deepEqual(readDotEnv(join(root, ".env")), { AUTH_MODE: "local-accounts", DATABASE_URL: "sqlite:///from-file.db" });
    const env = nativeEnvironment(root, { AUTH_MODE: "local", MDS01_STORAGE_KEY: "test" });
    assert.equal(env.AUTH_MODE, "local");
    assert.equal(env.DATABASE_URL, "sqlite:///from-file.db");
    assert.equal(env.VIDEO_DETECTION_ENABLED, "true");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
