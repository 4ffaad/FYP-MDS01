import { execFileSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import { chmodSync, mkdtempSync, rmSync } from "node:fs";
import { createRequire } from "node:module";
import { join, resolve } from "node:path";
import { tmpdir } from "node:os";

const require = createRequire(resolve(__dirname, "../../package.json"));
const { requireSecurityComposeProjectName } =
  require("./tests/real/security-compose-project.cjs") as {
    requireSecurityComposeProjectName: (value: string | undefined) => string;
  };

export default function globalSetup() {
  process.env.POSTGRES_PASSWORD = randomBytes(24).toString("hex");
  process.env.MDS01_STORAGE_KEY = randomBytes(32).toString("base64");
  process.env.MDS01_TEMPLATE_KEY = randomBytes(32).toString("base64");
  if (!process.env.MDS01_SECURITY_PORT) {
    throw new Error("MDS01_SECURITY_PORT is required");
  }
  process.env.SECURITY_BACKEND_PORT = process.env.MDS01_SECURITY_PORT;
  const root = resolve(__dirname, "../../..");
  const securityProject = requireSecurityComposeProjectName(
    process.env.MDS01_SECURITY_COMPOSE_PROJECT,
  );
  const containerPatientFolder = "/tmp/mds01-real-e2e-patient-folder";
  const hostPatientFolder = mkdtempSync(
    join(tmpdir(), `${securityProject}-patient-folder-`),
  );
  chmodSync(hostPatientFolder, 0o700);
  process.env.MDS01_SECURITY_PATIENT_FOLDER = hostPatientFolder;
  const compose = [
    "compose",
    "-p",
    securityProject,
    "--env-file",
    "/dev/null",
    "-f",
    "docker-compose.security.yml",
  ];
  try {
    execFileSync("docker", [...compose, "up", "--build", "-d", "--wait"], {
      cwd: root,
      stdio: "inherit",
    });
    execFileSync(
      "docker",
      [
        ...compose,
        "exec",
        "-T",
        "backend",
        "python",
        "backend/tests/generate_e2e_archive.py",
        "--synthetic-veeg-folder",
        containerPatientFolder,
      ],
      { cwd: root, stdio: "inherit" },
    );
    const fixtureArchive = execFileSync(
      "docker",
      [
        ...compose,
        "exec",
        "-T",
        "backend",
        "tar",
        "-C",
        containerPatientFolder,
        "-cf",
        "-",
        "synthetic-veeg.edf",
        "synthetic-report.docx",
      ],
      { cwd: root, maxBuffer: 5 * 1024 * 1024 },
    );
    const fixtureEntries = execFileSync("tar", ["-tf", "-"], {
      cwd: root,
      encoding: "utf8",
      input: fixtureArchive,
    })
      .split(/\r?\n/)
      .filter(Boolean)
      .sort();
    const expectedEntries = ["synthetic-report.docx", "synthetic-veeg.edf"];
    if (fixtureEntries.join("\n") !== expectedEntries.join("\n")) {
      throw new Error(
        "The synthetic backend fixture archive has unexpected files.",
      );
    }
    execFileSync("tar", ["-xf", "-", "-C", hostPatientFolder], {
      cwd: root,
      input: fixtureArchive,
    });
    chmodSync(hostPatientFolder, 0o700);
    for (const name of expectedEntries) {
      chmodSync(resolve(hostPatientFolder, name), 0o600);
    }
  } catch (error) {
    const setupError =
      error instanceof Error
        ? error
        : new Error("Real-backend test setup failed.");
    try {
      execFileSync("docker", [...compose, "down", "-v", "--remove-orphans"], {
        cwd: root,
        stdio: "inherit",
      });
    } catch (cleanupError) {
      const detail =
        cleanupError instanceof Error
          ? cleanupError.message
          : "unknown cleanup error";
      setupError.message = `${setupError.message}; isolated test stack cleanup failed: ${detail}`;
    } finally {
      rmSync(hostPatientFolder, { recursive: true, force: true });
    }
    throw setupError;
  }
}
