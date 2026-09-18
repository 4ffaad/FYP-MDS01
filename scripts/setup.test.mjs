import assert from "node:assert/strict";
import { chmodSync, copyFileSync, mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
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
    assert.match(values.DEMO_ADMIN_PASSWORD, /^[a-f0-9]{32}$/);
    assert.equal(values.MODEL_RUNTIME, "stub");
    assert.deepEqual(setup(root), ["Kept existing .env", "Kept existing frontend/.env.local"]);
    assert.equal(readFileSync(join(root, ".env"), "utf8"), before);
    assert.equal(readFileSync(join(root, "frontend/.env.local"), "utf8"), frontend);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("setup repairs a missing password without rotating existing keys", () => {
  const root = mkdtempSync(join(tmpdir(), "mds01-setup-repair-test-"));
  try {
    mkdirSync(join(root, "frontend"));
    for (const template of [".env.example", "frontend/.env.example"]) copyFileSync(new URL(`../${template}`, import.meta.url), join(root, template));
    setup(root);
    const envPath = join(root, ".env");
    const before = readFileSync(envPath, "utf8").replace(/^POSTGRES_PASSWORD=.*$/m, "");
    writeFileSync(envPath, before, { mode: 0o600 });
    assert.deepEqual(setup(root), ["Kept existing .env", "Kept existing frontend/.env.local"]);
    const repaired = readFileSync(envPath, "utf8");
    assert.match(repaired, /^POSTGRES_PASSWORD=[a-f0-9]{48}$/m);
    assert.equal(repaired.replace(/^POSTGRES_PASSWORD=.*$/m, "").trimEnd(), before.trimEnd());
  } finally { rmSync(root, { recursive: true, force: true }); }
});

test("setup repairs empty required secret values", () => {
  const root = mkdtempSync(join(tmpdir(), "mds01-setup-empty-test-"));
  try {
    mkdirSync(join(root, "frontend"));
    for (const template of [".env.example", "frontend/.env.example"]) copyFileSync(new URL(`../${template}`, import.meta.url), join(root, template));
    setup(root);
    const envPath = join(root, ".env");
    const empty = readFileSync(envPath, "utf8")
      .replace(/^POSTGRES_PASSWORD=.*$/m, "POSTGRES_PASSWORD=")
      .replace(/^MDS01_STORAGE_KEY=.*$/m, "MDS01_STORAGE_KEY=")
      .replace(/^MDS01_TEMPLATE_KEY=.*$/m, "MDS01_TEMPLATE_KEY=");
    writeFileSync(envPath, empty, { mode: 0o600 });
    setup(root);
    const repaired = Object.fromEntries(readFileSync(envPath, "utf8").split("\n").filter((line) => /^[A-Z0-9_]+=/.test(line)).map((line) => {
      const index = line.indexOf("=");
      return [line.slice(0, index), line.slice(index + 1)];
    }));
    assert.match(repaired.POSTGRES_PASSWORD, /^[a-f0-9]{48}$/);
    assert.equal(Buffer.from(repaired.MDS01_STORAGE_KEY, "base64").length, 32);
    assert.equal(Buffer.from(repaired.MDS01_TEMPLATE_KEY, "base64").length, 32);
  } finally { rmSync(root, { recursive: true, force: true }); }
});
test("setup tightens permissions on an existing environment file", () => {
  const root = mkdtempSync(join(tmpdir(), "mds01-setup-permissions-test-"));
  try {
    mkdirSync(join(root, "frontend"));
    for (const template of [".env.example", "frontend/.env.example"]) copyFileSync(new URL(`../${template}`, import.meta.url), join(root, template));
    setup(root);
    const envPath = join(root, ".env");
    chmodSync(envPath, 0o644);
    setup(root);
    assert.equal(statSync(envPath).mode & 0o777, 0o600);
  } finally { rmSync(root, { recursive: true, force: true }); }
});
