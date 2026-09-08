import assert from "node:assert/strict";
import { copyFileSync, mkdirSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { setup } from "./setup.mjs";

test("setup generates independent keys and preserves both existing config files", () => {
  const root = mkdtempSync(join(tmpdir(), "mds01-setup-test-"));
  try {
    mkdirSync(join(root, "frontend"));
    for (const template of [".env.example", "frontend/.env.example"]) {
      copyFileSync(new URL(`../${template}`, import.meta.url), join(root, template));
    }
    assert.deepEqual(setup(root), ["Created .env", "Created frontend/.env.local"]);
    const before = readFileSync(join(root, ".env"), "utf8");
    const frontend = readFileSync(join(root, "frontend/.env.local"), "utf8");
    const values = Object.fromEntries(before.split("\n").filter((line) => /^[A-Z0-9_]+=/.test(line)).map((line) => {
      const index = line.indexOf("=");
      return [line.slice(0, index), line.slice(index + 1)];
    }));
    assert.equal(Buffer.from(values.MDS01_STORAGE_KEY, "base64").length, 32);
    assert.equal(Buffer.from(values.MDS01_TEMPLATE_KEY, "base64").length, 32);
    assert.notEqual(values.MDS01_STORAGE_KEY, values.MDS01_TEMPLATE_KEY);
    assert.match(values.POSTGRES_PASSWORD, /^[a-f0-9]{48}$/);
    assert.equal(values.MODEL_RUNTIME, "stub");
    assert.deepEqual(setup(root), ["Kept existing .env", "Kept existing frontend/.env.local"]);
    assert.equal(readFileSync(join(root, ".env"), "utf8"), before);
    assert.equal(readFileSync(join(root, "frontend/.env.local"), "utf8"), frontend);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
