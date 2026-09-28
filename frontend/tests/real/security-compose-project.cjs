const { randomBytes } = require("node:crypto");

const PROJECT_PATTERN = /^mds01-security-[a-f0-9]{32}$/;
const TOKEN_PATTERN = /^[a-f0-9]{32}$/;
const MAX_ATTEMPTS = 8;

function createSecurityComposeProjectName({
  token = () => randomBytes(16).toString("hex"),
  exists = () => false,
} = {}) {
  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt += 1) {
    const randomToken = token();
    if (!TOKEN_PATTERN.test(randomToken)) {
      throw new Error("The security test run token must be 128-bit lowercase hex.");
    }
    const projectName = `mds01-security-${randomToken}`;
    if (!exists(projectName)) return projectName;
  }
  throw new Error("Could not allocate an unused security test run namespace.");
}

function requireSecurityComposeProjectName(value) {
  if (typeof value !== "string" || !PROJECT_PATTERN.test(value)) {
    throw new Error(
      "The real-backend test requires a generated per-run security Compose project.",
    );
  }
  return value;
}

module.exports = {
  createSecurityComposeProjectName,
  requireSecurityComposeProjectName,
};
