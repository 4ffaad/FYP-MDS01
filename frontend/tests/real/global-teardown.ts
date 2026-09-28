import { execFileSync } from "node:child_process";
import { rmSync } from "node:fs";
import { createRequire } from "node:module";
import { basename, dirname, resolve } from "node:path";
import { tmpdir } from "node:os";

const require = createRequire(resolve(__dirname, "../../package.json"));
const { requireSecurityComposeProjectName } =
  require("./tests/real/security-compose-project.cjs") as {
    requireSecurityComposeProjectName: (value: string | undefined) => string;
  };

export default function globalTeardown() {
  const root = resolve(__dirname, "../../..");
  const securityProject = requireSecurityComposeProjectName(
    process.env.MDS01_SECURITY_COMPOSE_PROJECT,
  );
  const hostPatientFolder = resolve(
    process.env.MDS01_SECURITY_PATIENT_FOLDER ?? "",
  );
  const fixtureSuffix = basename(hostPatientFolder).slice(
    `${securityProject}-patient-folder-`.length,
  );
  if (
    dirname(hostPatientFolder) !== tmpdir() ||
    !basename(hostPatientFolder).startsWith(
      `${securityProject}-patient-folder-`,
    ) ||
    !/^[a-zA-Z0-9]{6,}$/.test(fixtureSuffix)
  ) {
    throw new Error(
      "Refusing to remove a non-isolated synthetic fixture path.",
    );
  }
  try {
    execFileSync(
      "docker",
      [
        "compose",
        "-p",
        securityProject,
        "--env-file",
        "/dev/null",
        "-f",
        "docker-compose.security.yml",
        "down",
        "-v",
        "--remove-orphans",
      ],
      { cwd: root, stdio: "inherit" },
    );
  } finally {
    rmSync(hostPatientFolder, { recursive: true, force: true });
  }
}
