# Task List: Reliable Patient Review Intake

## Task 1 — Reconcile streamed upload contracts

Description: Align the running Compose API with the repository's streamed binary upload routes and replace structured 422 objects with safe, actionable UI errors.

Acceptance criteria:
- [x] The live `/api/uploads/drafts`, `/api/video-detection/jobs`, and `/api/video-detection/preflight` routes advertise `application/octet-stream` after the backend rebuild.
- [x] A structured FastAPI validation response never becomes `[object Object]` in the browser and never exposes uploaded bytes or patient data.

Verification:
- [x] `PYTHONPATH=. .venv/bin/python -m unittest backend.tests.test_upload_openapi backend.tests.test_stream_upload backend.tests.test_stream_upload_route -v`
- [x] A focused E2E test injects a structured 422 response and asserts the safe alert.
- [x] Read the live container's OpenAPI contract after the rebuild.

Dependencies: None.
Files likely touched: `frontend/src/lib/api.ts`, related API tests; existing backend contract tests if needed.
Scope: Medium.

## Task 2 — Process every EEG and video in one case

Description: Preserve the existing one-case association, automatically include every EEG candidate, and run every video through the owner-scoped VSViG endpoint without concurrent job fan-out.

Acceptance criteria:
- [x] Every supported EEG in the selected folder is placed in the neutral-name archive and processed independently.
- [x] Every video is submitted to `/api/video-detection/jobs` with the same case reference, one at a time; the patient intake does not substitute privacy-preview jobs for model inference.
- [x] A timed-out/uncertain upload is never submitted again automatically; job/capacity failures remain visible without false completion claims.

Verification:
- [x] Backend tests covering session-level multi-record processing remain green.
- [x] Synthetic Playwright interception verifies all selected videos reach the detection API and the case review displays its analyses.
- [x] Video contract/runtime verification uses the documented Compose command, not patient footage.

Dependencies: Task 1.
Files likely touched: `frontend/src/lib/video-detection.ts`, `frontend/src/components/PatientFolderScreen.tsx`, focused E2E tests.
Scope: Large; keep the backend contract unchanged unless investigation proves it insufficient.

## Task 3 — One-screen intake with automatic report extraction

Description: Keep EEG privacy controls, video input, and patient details together on one intake screen; include all EEGs by default and show aggregate video status rather than per-file controls.

Acceptance criteria:
- [x] The single intake screen shows EEG privacy settings and the video input side by side, with aggregate modality counts and the full-frame-blur/audio policy explained accurately.
- [x] No clip-by-clip list or individual EEG toggles are shown on intake.
- [x] Keep all extracted patient/report fields behind a default-closed disclosure, without per-field controls or an intake approval step; save the complete extracted set automatically to the encrypted owner-only profile when the case is created, marked auto-extracted/unverified.

Verification:
- [x] E2E covers the one-screen layout, collapsed sensitive report values, automatic profile save and EEG inclusion, privacy settings, the detected EEG count, and no filenames/clip rows.
- [x] Desktop and mobile screenshots show no overflow and preserve visible focus.

Dependencies: Task 2.
Files likely touched: `frontend/src/components/PatientFolderScreen.tsx`, `frontend/tests/e2e/patient-folder.spec.ts`.
Scope: Medium.

## Task 4 — Unify Workspace and Patient History navigation

Description: Give each route one active navigation item, rename Cases to Patient History, remove redundant Patients labeling, and show recent privacy-safe case summaries on Workspace.

Acceptance criteria:
- [x] `/upload` marks only New patient review current; `/dashboard` marks only Workspace current; `/cases` marks only Patient History current.
- [x] Workspace shows reviewed owner-scoped patient names without report text, filenames, or internal case identifiers; auto-extracted identities are omitted from default case summaries until explicitly reviewed.
- [x] Patient History retains the owner-scoped detailed review destination.

Verification:
- [x] Playwright asserts route-specific active states and recent-case navigation.
- [x] Rendered Workspace and Patient History are checked at desktop and mobile widths.

Dependencies: Task 3.
Files likely touched: `frontend/src/components/AppShell.tsx`, `NavLink.tsx`, `DashboardScreen.tsx`, `CasesScreen.tsx`, relevant E2E specs.
Scope: Medium.

## Task 5 — Verify privacy and runtime limits

Description: Run relevant checks, rebuild the stale API service after the user authorized resetting the disposable local Postgres volume, and report which real-data/model steps remain gated by approval or input-contract limits.

Acceptance criteria:
- [x] Existing changes are preserved; only the Postgres volume was reset after explicit user authorization; after a dry run confirmed no app-row references, the 19 orphaned encrypted private-storage files were removed; model volumes remained; no source-media output occurred.
- [x] Backend/frontend checks and the pinned VSViG runtime verification pass; the active H5 and VSViG contracts were loaded without patient inference.
- [x] No real HUKM inference was run. The latest no-credentials `/api/auth/session` request returned HTTP 200, `authenticated=false`, and `owner_user_present=null`; this verifies no authenticated session on that request, not whether an account exists. No explicit “ready” authorization was given.

Verification:
- [x] Backend unittest discovery and disposable PostgreSQL integrity/concurrency checks passed. Relevant desktop/mobile E2E suites passed in API-intercepted and development-stub configurations; the synthetic real-backend suite passed. Frontend format, lint, typecheck, and production build passed.
- [x] `docker compose build backend`, additive migration to 029, live streamed-upload OpenAPI, H5 contract load, and `verify_vsvig_runtime` passed.
- [x] `git diff --check`; review changed-file scope and preserved all other volumes.

Dependencies: Tasks 1–4.
Files likely touched: project files only as required.
Scope: Large.

## Checkpoint
- [x] Upload, multi-EEG, and video detection paths are proven with synthetic fixtures.
- [x] Privacy boundaries and model limitations are visible and accurately described.
- [ ] Process the supplied HUKM media after the user registers/logs in; label adapted 640×480 video outputs research-only and unvalidated.

## Task 6 — Resume owner-scoped inference after account setup

Description: Once an owner-scoped session is verified and the user explicitly says “ready,” process the approved EEG and video inputs through the privacy-preserving research pipeline.

Acceptance criteria:
- [ ] All EEG recordings and videos are associated with the same owner-scoped case.
- [ ] Experimental letterbox provenance is retained for adapted video inputs; no result is described as clinically validated.
- [ ] Original/transient media is cleaned up according to the configured privacy policy; only approved encrypted artifacts remain.

Verification:
- [ ] Confirm job status and case review artifacts through owner-scoped endpoints.
- [ ] Report only aggregate processing outcome and explicit research-only limitations; never print patient values, paths, or filenames.

Dependencies: User registration/login.

## Review follow-ups — Required before closing Task 2/3/5

- [x] Never resubmit a video whose upload outcome is uncertain when the user rechecks status; cover it with an intercepted end-to-end regression test.
- [x] Map unknown video-job error text to a fixed safe message; do not render arbitrary service diagnostics or file paths.
- [x] Move keyboard focus to the processing heading when intake switches screens; assert it in the browser test.
- [x] Sanitize unsupported EEG-extension diagnostics so filename-derived text cannot be exposed, and test `.e` archive extraction through legacy-validator dispatch.
- [x] The user requested automatic local report extraction and saving without a separate intake confirmation step; profiles remain unverified until the owner separately reviews the complete profile on the case page.
- [x] Current video job is `privacy_transform_failed` before pose/VSViG; the stored status and retained logs do not distinguish normalization from face-redaction. Keep that subcause explicitly unknown; do not retry real media until the user signs in and says “ready.”
- [x] If local report extraction fails, EEG processing remains available and no extracted profile is saved; covered by a focused browser regression.
- [x] A retryable video rejection leaves only unsubmitted clips eligible for retry, preserves completed clips, and reports the paused/retryable state; covered by a focused browser regression.
- [x] A failed EEG session is shown as an issue even when no recording rows were created; covered by a focused browser regression.
- [x] Real-backend Playwright setup reuses its generated project namespace across config reloads; workflow assertions match the current intake and processing screen.
- [x] Provide a separate whole-profile review action after processing; default case summaries omit auto-extracted patient/report values until the owner explicitly reviews them. This records data review, not clinical validation.
- [x] Distinguish expired and not-submitted video outcomes from processing failures, while showing terminal issues accurately.
