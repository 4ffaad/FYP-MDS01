import assert from "node:assert/strict";
import { test } from "node:test";
import { ensureFrontendDependencies } from "./dev.mjs";

test("frontend dev reuses installed locked dependencies", () => {
  const commands = [];
  const installed = ensureFrontendDependencies({
    root: "/workspace",
    platform: "linux",
    hasFrontendDependencies: () => true,
    run: (...args) => commands.push(args),
  });

  assert.equal(installed, false);
  assert.deepEqual(commands, []);
});

test("frontend dev installs the locked dependencies when Next is absent", () => {
  const commands = [];
  const installed = ensureFrontendDependencies({
    root: "/workspace",
    platform: "linux",
    hasFrontendDependencies: () => false,
    run: (...args) => commands.push(args),
  });

  assert.equal(installed, true);
  assert.deepEqual(commands, [
    ["npm", ["ci"], { cwd: "/workspace/frontend", shell: false }],
  ]);
});
