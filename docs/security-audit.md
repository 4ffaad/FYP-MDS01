# Security audit — August 2026 snapshot

This report records the August 2026 repository and disposable-runtime audit. The managed Codex Security deep-scan runner could not start because this session did not provide its required managed filesystem. The audit instead used three independent source reviews, direct API tests, Bandit, dependency checks, secret/history checks, Docker inspection, Playwright, and a disposable real-backend workflow.

## Current implementation verification — September 2026

The local multi-user authentication update was rechecked after the historical
snapshot above:

- Backend unit/security suite: **101 passed**.
- Frontend lint, type check and production build: **passed**.
- Browser-only desktop/mobile suite: **20 passed**.
- Authenticated login/register/logout browser suite: **1 passed**.
- Disposable real Docker workflow, including browser registration: **1 passed**.

These checks use synthetic or disposable data only and do not establish
clinical accuracy, anonymity or production security.

## Security controls verified

| Area | Result |
| --- | --- |
| API authentication | Protected routers require either a server-side local account session in `AUTH_MODE=local-accounts` or a valid Cloudflare Access assertion in `AUTH_MODE=cloudflare`; `/health` and auth status remain public. Production startup rejects local authentication. |
| Local exposure | FastAPI and PostgreSQL bind to `127.0.0.1` in Docker Compose. Local authentication is intended only for this loopback development mode. |
| Identifiers | New `SES-`, `REC-`, and `UPL-` identifiers contain 128 random bits. Historical IDs remain readable. |
| Upload abuse | ZIP traversal, per-member size, member count, cumulative uncompressed size, and compression-ratio limits are enforced. |
| Processing load | A bounded in-process semaphore rejects new analyses with `503` when the configured prototype capacity is full. |
| Private storage | New directories use mode `0700`, files use `0600`, the process uses umask `077`, and the backend container runs as an unprivileged user. A scoped initializer repairs ownership of an older Docker storage volume without deleting it. |
| Browser boundary | Explicit credentialed CORS origins support local and Cloudflare cookies. Local state changes also require a configured `Origin`. FastAPI and Next.js return framing, MIME-sniffing, referrer, and browser-permission headers. |
| Signal access | Signal preview remains disabled by default and returns `404`; enabling it is a deliberate local-development choice. |

## Verification evidence

- Backend unit and security suite: **54 passed** at the time of the August snapshot.
- Frontend ESLint and production Next.js build: **passed**.
- Stub Playwright desktop/mobile suite: **12 passed** at the time of the August snapshot.
- Disposable real-backend Playwright workflow: **1 passed**. It exercised encrypted draft upload, privacy selection, PostgreSQL migrations, background processing, session/result APIs, signal denial, and deletion.
- Privacy canaries placed in the synthetic EDF filename, patient fields, equipment fields, annotations, and signal-header text did not appear in the browser or tested API responses.
- The disposable PostgreSQL and storage volumes were removed after the test.
- Bandit previously reported no Python source findings; `npm audit` previously reported no known frontend dependency vulnerabilities.
- The Python dependency check did not establish a fully reproducible lock-file audit; application dependencies are still range/unpinned requirements.

This is historical evidence, not the current test count or a fresh security
assessment. The local-account controls above are part of the current
implementation; rerun the checks below after changes. For current startup and
test commands, use [setup](setup.md).

Run the permanent checks with:

```bash
PYTHONPATH=. .venv/bin/python -m unittest discover -s backend/tests -v
cd frontend && npm run lint && npm run build && npm run test:e2e
npm run test:e2e:real
```

`test:e2e:real` creates and destroys only the Compose project named `mds01-security`. It requires Docker and npm; its synthetic EEG fixture is generated inside the backend container.

## Remaining deployment work

These are not blockers for loopback-only local development. They must be handled before exposing the application to teammates or the internet.

| Severity | Requirement | Action |
| --- | --- | --- |
| High | Cloudflare policy and secrets are external configuration. | Create the Access application/policy, set `APP_ENV=production`, `AUTH_MODE=cloudflare`, the team-domain hostname, and application audience. Never put these values in `NEXT_PUBLIC_*`. |
| High | Legacy local storage may contain plaintext prototype artifacts. | Review and remove legacy data manually. It was not deleted automatically because it may be user-generated. |
| Medium | FastAPI `BackgroundTasks` can be interrupted by a restart. | Accept for the prototype; use a durable queue before production-scale or clinically relied-upon processing. |
| Medium | A process kill can leave temporary work until cleanup runs. | Move temporary plaintext work to ephemeral storage and add stale-work cleanup before handling real patient data. |
| Medium | Dependencies are not locked and the migration role is the runtime DB role. | Add lock files/image update policy and separate migration credentials for a production deployment. |
| Medium | Cloudflare edge rate limits are not repository code. | Configure upload/request rate limits in Cloudflare in addition to the local processing-capacity guard. |
| Low | AES-GCM artifacts do not use versioned session/artifact associated data. | Bind future encrypted artifact versions to their expected context during encryption and decryption. |
| Low | Draft expiry cleanup is request-driven. | Add scheduled expiry cleanup if abandoned drafts become common. |

## Manual actions deliberately not performed

- No normal PostgreSQL volume, session data, retained EEG artifact, or legacy file was deleted.
- The tracked `frontend/.env.local` and generated `frontend/tsconfig.tsbuildinfo`
  are now removed from the working tree and ignored. Git history was not
  rewritten; rotate any value that was ever a real secret before publishing
  the repository.
- Cloudflare DNS, tunnel, Access policy, and secret-manager configuration were not changed.
- The deterministic seizure model remains a non-clinical development stub; this audit provides no medical-accuracy assurance.

## Decision

The app is suitable for local prototype testing on loopback. It is **not yet suitable for public deployment** until Cloudflare Access and the listed high-severity deployment actions are completed. Security reduces risk; it does not establish HIPAA compliance, anonymity, or clinical safety.
