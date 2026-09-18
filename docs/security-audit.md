# Security audit — September 2026 implementation review

This report records the August 2026 repository and disposable-runtime audit. The managed Codex Security deep-scan runner could not start because this session did not provide its required managed filesystem. The audit instead used three independent source reviews, direct API tests, Bandit, dependency checks, secret/history checks, Docker inspection, Playwright, and a disposable real-backend workflow.

## Current implementation verification — September 2026

The final integration pass rechecked the repository after the historical
snapshot above:

- Backend unit/security suite: **196 passed** with one expected local codec-support skip.
- Frontend formatting, lint, TypeScript check and production build: **passed**.
- Browser-only desktop/mobile suite: **34 passed**.
- Pinned VSViG/OpenPose installer and contract-loader checks: **passed**.
- Rebuilt `linux/amd64` video image with Torch `2.14.0+cpu` and mounted-checkpoint verifier: **passed**.
- Container security posture: unprivileged user, read-only root filesystem,
  dropped capabilities, `no-new-privileges`, and a read-only named model volume.
- Synthetic patch-to-VSViG tensor smoke: **passed**.
- Live Docker API security harness: **passed**, including early body-size
  rejection, origin checks, cookie flags, logout revocation, and case scoping.

These checks use synthetic or disposable data only and do not establish
clinical accuracy, anonymity or production security.

## Security controls verified

| Area | Result |
| --- | --- |
| API authentication | Protected routers require either a server-side local account session in `AUTH_MODE=local-accounts` or a valid Cloudflare Access assertion in `AUTH_MODE=cloudflare`; `/health` and auth status remain public. Local login/registration admission is bounded by client and identifier buckets and returns `429` with `Retry-After`. Production startup rejects local authentication. |
| Local exposure | FastAPI and PostgreSQL bind to `127.0.0.1` in Docker Compose. Local authentication is intended only for this loopback development mode. |
| Identifiers | New `SES-`, `REC-`, and `UPL-` identifiers contain 128 random bits. Historical IDs remain readable. |
| Upload abuse | ZIP traversal, per-member size, member count, cumulative uncompressed size, and compression-ratio limits are enforced. |
| Request resource limits | Upload routes reject oversized request bodies before multipart parsing; each owner is limited to bounded active/pending EEG drafts. |
| Processing load | A bounded in-process semaphore rejects new analyses with `503` when the configured prototype capacity is full. |
| Video transform bounds | Video privacy processing enforces FPS, dimensions, decoded-frame, output-byte and wall-clock limits; output validation requires exact frame count/dimensions/FPS/duration and rejects audio streams. |
| Draft lifecycle | Expired drafts are swept at startup and by a background retention task; orphaned encrypted draft directories are eligible for safe cleanup. |
| Ownership | Ordinary users remain owner-scoped. Only an explicitly enabled development/local-account demo administrator has global read scope; new and destructive writes retain the authenticated account owner. |
| Private storage | New directories use mode `0700`, files use `0600`, the process uses umask `077`, and the backend container runs as an unprivileged user. A scoped initializer repairs ownership of an older Docker storage volume without deleting it. |
| Container hardening | Backend and VSViG initializer run unprivileged with `no-new-privileges`, all capabilities dropped, read-only roots and constrained `/tmp`. Postgres and one-shot initializers have explicit memory, CPU, PID and file limits. Postgres keeps only the limited capabilities required by its official root-to-postgres entrypoint; the root `storage-init` helper keeps only ownership capabilities and is one-shot. |
| Browser boundary | Explicit credentialed CORS origins support local and Cloudflare cookies. Local state changes also require a configured `Origin`. FastAPI and Next.js return framing, MIME-sniffing, referrer, and browser-permission headers. |
| Signal access | Signal preview remains disabled by default and returns `404`; enabling it is a deliberate local-development choice. |
| Video model supply chain | The official VSViG and Lightweight OpenPose files are pinned by revision and SHA-256, initialized into a named volume outside Git, mounted read-only by the backend, and loaded by a startup verification pass before Uvicorn starts. The generated contract must also match the code-pinned reviewed contract digest; a mounted bundle cannot approve its own changed metadata. |
| Video media minimization | Detection deletes source and temporary model-input work, retains only encrypted prediction results plus the explicitly approved encrypted owner-scoped privacy-safe visualization, and exposes no source-video endpoint. The visualization is audio-free, face-redacted and full-frame-blurred with a skeleton overlay; the separate video-privacy utility has a separate policy. |
| Upload staging | Multipart parsing precedes application-level AES-GCM storage; the framework's private spool is treated as short-lived sensitive work data and is cleaned with the job. |
| Video privacy runtime | New jobs support face redaction only. The legacy pose-only enum remains readable for stored records but fails closed and is not shipped as an executable privacy transform. |

## Verification evidence

- The current backend discovery suite reports **196 passed** with one expected
  local codec-support skip.
- Frontend formatting, ESLint, TypeScript, Next.js production build, and
  Playwright report **34 passed** browser tests.
- Node setup/start-native tests report **3 passed**.
- Compose configuration validation and Python compilation pass.
- Targeted Bandit scanning of the changed video detection modules reports zero
  findings.
- `npm audit` reports zero known moderate-or-higher frontend vulnerabilities.
- `pip-audit` reports zero known vulnerabilities for the base, development, and
  research requirement sets. The rebuilt image upgrades pip to `26.2.1`, and
  an image-level audit reports no known vulnerabilities. PyTorch CPU wheels are
  hosted outside PyPI and are audited separately from their pinned requirement
  file; pip-audit records them as skipped in the image-level run.
- The video requirement set uses the newest available official CPU wheels,
  Torch `2.14.0+cpu` and torchvision `0.29.0+cpu`. The Torch audit matrix found
  no known vulnerabilities for this pair; the model bundle is still
  SHA-256-verified before its `weights_only` loads. Re-run the audit whenever a
  newer official wheel is published.
- The Docker image build, confined startup, mounted VSViG verifier, and
  synthetic video-runtime check pass on `linux/amd64`.
- A live disposable Docker API harness passed authentication, CSRF/origin,
  cookie, body-limit, logout, and owner-boundary assertions.
- Privacy canaries placed in the synthetic EDF filename, patient fields, equipment fields, annotations, and signal-header text did not appear in the browser or tested API responses.
- Disposable security containers were stopped without deleting their isolated
  volumes; no normal project data was touched.
- Python requirements are bounded/pinned at the direct-dependency level, but
  there is not yet a complete hashed lock set for every platform wheel.

Earlier entries in this page are retained as historical context. The current
counts and controls above are the active implementation evidence; rerun the
checks below after changes. For current startup and test commands, use
[setup](setup.md).

Run the permanent checks with:

```bash
PYTHONPATH=. .venv/bin/python -m unittest discover -s backend/tests -v
cd frontend && npm run lint && npm run build && npm run test:e2e
npm run test:e2e:real
```

`test:e2e:real` creates and destroys only the Compose project named
`mds01-security` by default; set `MDS01_SECURITY_COMPOSE_PROJECT` for an
explicit disposable project name. It requires Docker and npm; its synthetic
EEG fixture is generated inside the backend container. The setup/teardown use
`down -v`, so run only against a disposable project.

## Remaining deployment work

These are not blockers for loopback-only local development. They must be handled before exposing the application to teammates or the internet.

| Severity | Requirement | Action |
| --- | --- | --- |
| High | Cloudflare policy and secrets are external configuration. | Create the Access application/policy, set `APP_ENV=production`, `AUTH_MODE=cloudflare`, the team-domain hostname, and application audience. Never put these values in `NEXT_PUBLIC_*`. |
| High | Legacy local storage may contain plaintext prototype artifacts. | Review and remove legacy data manually. It was not deleted automatically because it may be user-generated. |
| Medium | FastAPI `BackgroundTasks` can be interrupted by a restart. | Accept for the prototype; use a durable queue before production-scale or clinically relied-upon processing. |
| Medium | A process kill can leave temporary work until cleanup runs. | Move temporary plaintext work to ephemeral storage and add stale-work cleanup before handling real patient data. |
| Medium | Dependencies are not locked and the migration role is the runtime DB role. | Add lock files/image update policy and separate migration credentials for a production deployment. |
| Medium | The video Torch wheel still has two OSV advisories for APIs outside this service's call graph. | Keep the runtime on the newest official wheel, maintain the SHA-256 model contract and container confinement, and upgrade when a fixed official wheel is available. |
| Medium | Cloudflare edge rate limits are not repository code. | Configure upload/request rate limits in Cloudflare in addition to the local processing-capacity guard. |
| Medium | Video privacy and model performance are not yet validated on the target camera/site. | Run patient-disjoint face-redaction and VSViG evaluations with reviewed onset/offset labels before making accuracy or anonymity claims. |
| Low | AES-GCM artifacts do not use versioned session/artifact associated data. | Bind future encrypted artifact versions to their expected context during encryption and decryption. |


## Manual actions deliberately not performed

- No normal PostgreSQL volume, session data, retained EEG artifact, or legacy file was deleted. Disposable security containers and volumes were removed after verification; normal project data was untouched.
- The tracked `frontend/.env.local` and generated `frontend/tsconfig.tsbuildinfo`
  are now removed from the working tree and ignored. Git history was not
  rewritten; rotate any value that was ever a real secret before publishing
  the repository.
- Cloudflare DNS, tunnel, Access policy, and secret-manager configuration were not changed.
- The deterministic seizure model remains a non-clinical development stub; this audit provides no medical-accuracy assurance.

## Decision

The app is suitable for local prototype testing on loopback. It is **not yet suitable for public deployment** until Cloudflare Access and the listed high-severity deployment actions are completed. Security reduces risk; it does not establish HIPAA compliance, anonymity, or clinical safety.
