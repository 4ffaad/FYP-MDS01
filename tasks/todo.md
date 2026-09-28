# Task List: Reliable Patient Review Intake

## Task 1 — Reconcile streamed upload contracts

Description: Align the running Compose API with the repository's streamed binary upload routes and replace structured 422 objects with safe, actionable UI errors.

Acceptance criteria:
- [ ] The live `/api/uploads/drafts`, `/api/video-detection/jobs`, and `/api/video-detection/preflight` routes advertise `application/octet-stream` after the backend rebuild.
- [ ] A structured FastAPI validation response never becomes `[object Object]` in the browser and never exposes uploaded bytes or patient data.

Verification:
- [ ] `PYTHONPATH=. .venv/bin/python -m unittest backend.tests.test_upload_openapi backend.tests.test_stream_upload -v`
- [ ] A focused E2E test injects a structured 422 response and asserts the safe alert.
- [ ] Read the live container's OpenAPI contract after the rebuild.

Dependencies: None.
Files likely touched: `frontend/src/lib/api.ts`, related API tests; existing backend contract tests if needed.
Scope: Medium.

## Task 2 — Process every EEG and video in one case

Description: Preserve the existing one-case association, automatically include every EEG candidate, and run every video through the owner-scoped VSViG endpoint without concurrent job fan-out.

Acceptance criteria:
- [ ] Every supported EEG in the selected folder is placed in the neutral-name archive and processed independently.
- [ ] Every video is submitted to `/api/video-detection/jobs` with the same case reference, one at a time; the patient intake does not substitute privacy-preview jobs for model inference.
- [ ] Job/capacity failures remain visible and do not produce duplicate uploads or false completion claims.

Verification:
- [ ] Backend tests covering session-level multi-record processing remain green.
- [ ] Synthetic Playwright interception verifies all selected videos reach the detection API and the case review displays its analyses.
- [ ] Video contract/runtime verification uses the documented Compose command, not patient footage.

Dependencies: Task 1.
Files likely touched: `frontend/src/lib/video-detection.ts`, `frontend/src/components/PatientFolderScreen.tsx`, focused E2E tests.
Scope: Large; keep the backend contract unchanged unless investigation proves it insufficient.

## Task 3 — Simplify intake and preserve explicit detail review

Description: Separate the media/privacy step from patient-detail review, include all EEGs by default with no per-recording selection controls, and show aggregate video status instead of individual clips.

Acceptance criteria:
- [ ] The first step shows EEG/video totals and the single optional EEG signal-obfuscation control, with the full-frame-blur/audio policy explained accurately.
- [ ] No clip-by-clip list or individual EEG toggles are shown on intake.
- [ ] Patient/report fields appear only on the next step and are saved only when explicitly selected.

Verification:
- [ ] E2E covers both steps, automatic inclusion of every EEG, privacy setting, report opt-in, and no filenames/clip rows.
- [ ] Desktop and mobile screenshots show no overflow and preserve visible focus.

Dependencies: Task 2.
Files likely touched: `frontend/src/components/PatientFolderScreen.tsx`, `frontend/tests/e2e/patient-folder.spec.ts`.
Scope: Medium.

## Task 4 — Unify Workspace and Patient History navigation

Description: Give each route one active navigation item, rename Cases to Patient History, remove redundant Patients labeling, and show recent privacy-safe case summaries on Workspace.

Acceptance criteria:
- [ ] `/upload` marks only New patient review current; `/dashboard` marks only Workspace current; `/cases` marks only Patient History current.
- [ ] Workspace shows recent cases without patient names, report text, filenames, or internal case identifiers.
- [ ] Patient History retains the owner-scoped detailed review destination.

Verification:
- [ ] Playwright asserts route-specific active states and recent-case navigation.
- [ ] Rendered Workspace and Patient History are checked at desktop and mobile widths.

Dependencies: Task 3.
Files likely touched: `frontend/src/components/AppShell.tsx`, `NavLink.tsx`, `DashboardScreen.tsx`, `CasesScreen.tsx`, relevant E2E specs.
Scope: Medium.

## Task 5 — Verify privacy and runtime limits

Description: Run relevant checks, rebuild the stale API service without touching the database volume, and report which real-data/model steps remain gated by approval or input-contract limits.

Acceptance criteria:
- [ ] Existing changes are preserved; no commit, push, database-volume deletion, or source-media output occurs.
- [ ] Backend/frontend checks and the pinned VSViG runtime verification pass or have explicit, evidence-backed blockers.
- [ ] Real HUKM inference is not run until approval and any experimental adaptation/limit decision are confirmed.

Verification:
- [ ] Backend unit suite and relevant frontend formatter, lint, typecheck, E2E, and production build.
- [ ] `docker compose build backend`, `docker compose up -d --no-deps backend`, then live contract and `backend.scripts.verify_vsvig_runtime` checks.
- [ ] `git diff --check`; review changed-file scope.

Dependencies: Tasks 1–4.
Files likely touched: project files only as required.
Scope: Large.

## Checkpoint
- [ ] Upload, multi-EEG, and video detection paths are proven with synthetic fixtures.
- [ ] Privacy boundaries and model limitations are visible and accurately described.
- [ ] The user is asked before processing the supplied HUKM media through inference.
