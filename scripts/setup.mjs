import { randomBytes } from "node:crypto";
import { chmodSync, lstatSync, readFileSync, writeFileSync } from "node:fs";
import { delimiter, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const BASE_COMPOSE_FILE = "docker-compose.yml";
const LOCAL_RESEARCH_COMPOSE_FILES = [
  BASE_COMPOSE_FILE,
  "docker-compose.local-research.yml",
].join(delimiter);

function defaultComposeSelection(runtime) {
  const configuredRuntime = runtime?.trim();
  // Configs without a runtime retain the legacy H5 default.
  if (!configuredRuntime || configuredRuntime === "h5") {
    return {
      composeFile: LOCAL_RESEARCH_COMPOSE_FILES,
      composeProfiles: "local-research",
    };
  }
  return { composeFile: BASE_COMPOSE_FILE, composeProfiles: "" };
}

/** Create local configuration once; never rotate an existing installation's keys. */
export function setup(root) {
  const configurations = [
    [".env.example", ".env"],
    ["frontend/.env.example", "frontend/.env.local"],
  ];
  return configurations.map(([template, destination]) => {
    let content = readFileSync(resolve(root, template), "utf8");
    if (destination === ".env") {
      const templateRuntime = content.match(/^MODEL_RUNTIME=(.*)$/m)?.[1];
      const composeSelection = defaultComposeSelection(templateRuntime);
      content = content
        .replace(
          /^COMPOSE_FILE=.*$/m,
          `COMPOSE_FILE=${composeSelection.composeFile}`,
        )
        .replace(
          /^COMPOSE_PROFILES=.*$/m,
          `COMPOSE_PROFILES=${composeSelection.composeProfiles}`,
        )
        .replace(
          /^POSTGRES_PASSWORD=.*$/m,
          `POSTGRES_PASSWORD=${randomBytes(24).toString("hex")}`,
        )
        .replace(
          /^MDS01_STORAGE_KEY=.*$/m,
          `MDS01_STORAGE_KEY=${randomBytes(32).toString("base64")}`,
        )
        .replace(
          /^MDS01_TEMPLATE_KEY=.*$/m,
          `MDS01_TEMPLATE_KEY=${randomBytes(32).toString("base64")}`,
        )
        .replace(
          /^DEMO_ADMIN_PASSWORD=.*$/m,
          `DEMO_ADMIN_PASSWORD=${randomBytes(16).toString("hex")}`,
        );
    }
    try {
      writeFileSync(resolve(root, destination), content, {
        flag: "wx",
        mode: 0o600,
      });
      return `Created ${destination}`;
    } catch (error) {
      if (error.code !== "EEXIST") throw error;
      // Repair older local files without rotating existing secrets.
      const existingPath = resolve(root, destination);
      const existingStats = lstatSync(existingPath);
      if (existingStats.isSymbolicLink() || !existingStats.isFile()) {
        throw new Error(
          `${destination} must be a regular file, not a symlink or directory`,
        );
      }
      chmodSync(existingPath, 0o600);
      if (destination === ".env") {
        const existing = readFileSync(existingPath, "utf8");
        const contractHash = content
          .match(/^VSVIG_CONTRACT_SHA256=(.+)$/m)?.[1]
          ?.trim();
        if (!contractHash) {
          throw new Error(".env.example must define VSVIG_CONTRACT_SHA256");
        }
        const additions = [];
        let repaired = existing;
        const existingRuntime = existing.match(/^MODEL_RUNTIME=(.*)$/m)?.[1];
        const composeSelection = defaultComposeSelection(existingRuntime);
        const generators = {
          COMPOSE_FILE: () => composeSelection.composeFile,
          COMPOSE_PROFILES: () => composeSelection.composeProfiles,
          POSTGRES_PASSWORD: () => randomBytes(24).toString("hex"),
          MDS01_STORAGE_KEY: () => randomBytes(32).toString("base64"),
          MDS01_TEMPLATE_KEY: () => randomBytes(32).toString("base64"),
          DEMO_ADMIN_PASSWORD: () => randomBytes(16).toString("hex"),
          VSVIG_CONTRACT_SHA256: () => contractHash,
        };
        for (const [key, generate] of Object.entries(generators)) {
          const match = existing.match(new RegExp(`^${key}=(.*)$`, "m"));
          if (!match) {
            additions.push(`${key}=${generate()}`);
          } else if (
            key === "COMPOSE_FILE" &&
            match[1].trim() === "__MDS01_COMPOSE_FILES__"
          ) {
            repaired = repaired.replace(
              new RegExp(`^${key}=.*$`, "m"),
              `${key}=${generate()}`,
            );
          } else if (
            !match[1].trim() ||
            match[1].trim().startsWith("replace-with-")
          ) {
            repaired = repaired.replace(
              new RegExp(`^${key}=.*$`, "m"),
              `${key}=${generate()}`,
            );
          }
        }
        if (additions.length || repaired !== existing)
          writeFileSync(
            existingPath,
            `${repaired.trimEnd()}\n${additions.join("\n")}\n`,
            { mode: 0o600 },
          );
      }
      return `Kept existing ${destination}`;
    }
  });
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(resolve(process.argv[1])).href
) {
  const root = fileURLToPath(new URL("../", import.meta.url));
  for (const message of setup(root)) console.log(message);
  console.log(
    "Next: run npm run dev, then docker compose up --build in a second terminal, or use the native setup flow.",
  );
}
