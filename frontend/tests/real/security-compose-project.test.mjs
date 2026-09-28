import assert from "node:assert/strict";
import { createRequire } from "node:module";
import test from "node:test";
const require = createRequire(import.meta.url);
const {
  createSecurityComposeProjectName,
  requireSecurityComposeProjectName,
} = require("./security-compose-project.cjs");

test("security Compose projects are unique, validated run identifiers", () => {
  const generated = ["1".repeat(32), "2".repeat(32)];
  let index = 0;
  const create = () =>
    createSecurityComposeProjectName({ token: () => generated[index++] });
  const first = create();
  const second = create();

  assert.match(first, /^mds01-security-[a-f0-9]{32}$/);
  assert.match(second, /^mds01-security-[a-f0-9]{32}$/);
  assert.notEqual(first, second);
  assert.equal(requireSecurityComposeProjectName(first), first);
});

test("security Compose project generation skips existing output namespaces", () => {
  const generated = ["a".repeat(32), "b".repeat(32)];
  let index = 0;
  const project = createSecurityComposeProjectName({
    token: () => generated[index++],
    exists: (name) => name.endsWith("a".repeat(32)),
  });

  assert.equal(project, `mds01-security-${"b".repeat(32)}`);
});

test("fixed and caller-chosen Compose project names are rejected", () => {
  for (const value of [undefined, "mds01-security", "other-project", "mds01-security-123"]) {
    assert.throws(() => requireSecurityComposeProjectName(value), /generated per-run/);
  }
});
