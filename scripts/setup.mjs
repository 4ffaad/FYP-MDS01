import { randomBytes } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
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
        .replace(/^MDS01_TEMPLATE_KEY=.*$/m, `MDS01_TEMPLATE_KEY=${randomBytes(32).toString("base64")}`);
    }
    try {
      writeFileSync(resolve(root, destination), content, { flag: "wx", mode: 0o600 });
      return `Created ${destination}`;
    } catch (error) {
      if (error.code !== "EEXIST") throw error;
      // Repair older local files without rotating existing secrets.
      if (destination === ".env") {
        const existing = readFileSync(resolve(root, destination), "utf8");
        const additions = [];
        if (!/^POSTGRES_PASSWORD=/m.test(existing)) additions.push(`POSTGRES_PASSWORD=${randomBytes(24).toString("hex")}`);
        if (!/^MDS01_STORAGE_KEY=/m.test(existing)) additions.push(`MDS01_STORAGE_KEY=${randomBytes(32).toString("base64")}`);
        if (!/^MDS01_TEMPLATE_KEY=/m.test(existing)) additions.push(`MDS01_TEMPLATE_KEY=${randomBytes(32).toString("base64")}`);
        if (additions.length) writeFileSync(resolve(root, destination), `${existing.trimEnd()}\n${additions.join("\n")}\n`, { mode: 0o600 });
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
