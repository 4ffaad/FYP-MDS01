import { randomBytes } from "node:crypto";
import { chmodSync, lstatSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

/** Create local configuration once; never rotate an existing installation's keys. */
export function setup(root) {
  const configurations = [
    [".env.example", ".env"],
    ["frontend/.env.example", "frontend/.env.local"],
  ];
  return configurations.map(([template, destination]) => {
    let content = readFileSync(resolve(root, template), "utf8");
    if (destination === ".env") {
      content = content
        .replace(/^POSTGRES_PASSWORD=.*$/m, `POSTGRES_PASSWORD=${randomBytes(24).toString("hex")}`)
        .replace(/^MDS01_STORAGE_KEY=.*$/m, `MDS01_STORAGE_KEY=${randomBytes(32).toString("base64")}`)
        .replace(/^MDS01_TEMPLATE_KEY=.*$/m, `MDS01_TEMPLATE_KEY=${randomBytes(32).toString("base64")}`)
        .replace(/^DEMO_ADMIN_PASSWORD=.*$/m, `DEMO_ADMIN_PASSWORD=${randomBytes(16).toString("hex")}`);
    }
    try {
      writeFileSync(resolve(root, destination), content, { flag: "wx", mode: 0o600 });
      return `Created ${destination}`;
    } catch (error) {
      if (error.code !== "EEXIST") throw error;
      // Repair older local files without rotating existing secrets.
      const existingPath = resolve(root, destination);
      const existingStats = lstatSync(existingPath);
      if (existingStats.isSymbolicLink() || !existingStats.isFile()) {
        throw new Error(`${destination} must be a regular file, not a symlink or directory`);
      }
      chmodSync(existingPath, 0o600);
      if (destination === ".env") {
        const existing = readFileSync(existingPath, "utf8");
        const additions = [];
        let repaired = existing;
        const generators = {
          POSTGRES_PASSWORD: () => randomBytes(24).toString("hex"),
          MDS01_STORAGE_KEY: () => randomBytes(32).toString("base64"),
          MDS01_TEMPLATE_KEY: () => randomBytes(32).toString("base64"),
          DEMO_ADMIN_PASSWORD: () => randomBytes(16).toString("hex"),
        };
        for (const [key, generate] of Object.entries(generators)) {
          const match = existing.match(new RegExp(`^${key}=(.*)$`, "m"));
          if (!match) {
            additions.push(`${key}=${generate()}`);
          } else if (!match[1].trim() || match[1].trim().startsWith("replace-with-")) {
            repaired = repaired.replace(new RegExp(`^${key}=.*$`, "m"), `${key}=${generate()}`);
          }
        }
        if (additions.length || repaired !== existing) writeFileSync(existingPath, `${repaired.trimEnd()}\n${additions.join("\n")}\n`, { mode: 0o600 });
      }
      return `Kept existing ${destination}`;
    }
  });
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const root = fileURLToPath(new URL("../", import.meta.url));
  for (const message of setup(root)) console.log(message);
  console.log("Next: docker compose up --build, or node scripts/start-native.mjs after native Python setup. In another terminal: cd frontend && npm ci && npm run dev");
}
