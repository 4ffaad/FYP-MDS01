# Implementation Plan: Reliable Patient Review Intake

## Overview

Repair the patient-folder workflow so a selected folder includes every supported EEG recording and every video in one owner-scoped case, the video-detection model path is actually invoked, all report fields are extracted locally and saved automatically as an unverified profile when the case is created, and Workspace/Patient History navigation presents one clear active destination. Resolve the observed upload failure at the runtime-contract boundary without weakening streamed-upload privacy. Preserve model-contract and clinical-use limits.

## Architecture Decisions

- Keep the current raw `application/octet-stream` upload contract. The stale Compose backend was rebuilt after the user explicitly authorized resetting the disposable Postgres volume. The backend storage volume was retained, then its orphaned encrypted files were removed after a zero-reference dry run; model volumes were preserved.
- Keep all selected EEG candidates in the neutral-name encrypted ZIP; the backend already creates and processes one recording row per extracted EEG and continues when a sibling recording fails.
- Use the existing owner-scoped VSViG job route for every selected video, associated with the same case. Submit sequentially because the backend allows only one active detection job at a time. Keep full-frame blur/audio exclusion and show model results as research-only.
- Automatically parse the selected report through the development-only same-origin loopback endpoint; the parser never persists the source file. Save all extracted details in the encrypted owner-only profile once the case is created and mark them `auto_extracted`/unverified. A separate case-page action can record owner review; this is not clinical validation. Do not place patient details in URLs or browser storage.
- Make the Workspace link active only on Workspace routes. Rename the case-history navigation label to Patient History, remove the redundant Patients heading, and show only reviewed owner-scoped patient names in default summaries without report text or internal case identifiers.
- The effective runtime already has the experimental 640×480 letterbox adaptation enabled. Preserve that operator setting, mark adapted video evidence unvalidated/research-only, and do not run the supplied HUKM recordings through inference until the required use/consent approval is confirmed.

## Task List

### Phase 1: Reproduce and repair upload contracts
- [x] Confirm the current source and live container upload request contracts; rebuild the backend service and verify it advertises streamed binary uploads.
- [x] Normalize structured FastAPI validation errors so UI alerts never render `[object Object]` and never echo request payloads.
- [x] Add focused regression tests for the stale-contract symptom and safe error display.

### Phase 2: Complete modality processing
- [x] Preserve all EEG candidates automatically and verify the archive contains every candidate with neutral names.
- [x] Submit every video through the existing owner-scoped VSViG route under the created case, one at a time; reflect terminal status without listing individual clips on intake.
- [x] Add focused tests for multiple EEGs, multiple videos, queue/capacity behavior, and case association.

### Checkpoint: Processing path
- [x] Backend contract and processing tests pass.
- [x] Synthetic E2E proves every selected video reaches detection, not only the separate privacy-preview utility.

### Phase 3: Intake and navigation
- [x] Make the first intake step show EEG/video totals and the single EEG privacy choice only.
- [x] Keep report details behind a default-closed disclosure without per-field controls or an intake approval step; automatically save every extracted field as unverified when the normal processing workflow creates its case.
- [x] Rename Cases navigation to Patient History, remove redundant Patients labeling, correct exclusive active navigation state, and show recent de-identified cases on Workspace.
- [x] Update E2E expectations and capture settled desktop/mobile renders.

### Checkpoint: UX and privacy
- [x] No original patient filenames, raw report text, or unreviewed identifying details appear on intake or default Workspace summaries.
- [x] Only the route currently being viewed is marked current; auto-extracted details are visibly labeled unverified and can be reviewed later from the owner-scoped case page.

### Phase 4: Verification and runtime
- [x] Run focused backend and frontend tests, full relevant suites, formatter/linter/type checks, and production build. (One pre-existing local change remains in `backend/tests/test_upload_draft_postgres_concurrency.py`; no unrelated files were reformatted.)
- [x] Verify the rebuilt Compose backend's streamed-upload OpenAPI contract, current Alembic head, H5 runtime contract, and pinned VSViG runtime using the repository runbook.
- [x] Inspect the supplied dataset read-only for supported technical metadata only; synthetic tests exercise automatic field persistence as unverified; no patient inference was run.
- [x] Run `git diff --check` and review the final diff without disturbing pre-existing worktree changes.

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Running Compose backend is older than the checked-out client/API contract | Draft and video binary uploads fail with 422 | Rebuild/recreate `backend` and verify runtime OpenAPI. The user explicitly authorized resetting only the disposable Postgres volume; private storage/model volumes were preserved. |
| Processing every clip can overwhelm the single-job video runtime | Rejections, duplicate jobs, or resource pressure | Submit sequentially and respect existing capacity/error semantics; never fan out uploads concurrently. |
| Supplied 640×480 clips differ from the native 1920×1080 VSViG contract | Adapted results are experimental and not equivalent to native validated inputs | The effective runtime already enables letterbox adaptation; preserve provenance, label results research-only, and request approval before real-data inference. The observed longest clip is below the runtime's 3600-second duration limit. |
| Patient details are sensitive and extracted without an intake approval step | Accidental exposure or false review claims | Keep the source report transient on the device, encrypt every saved field in the owner-only profile, omit unreviewed values from default summaries, and label owner review as data review rather than clinical validation. |
| Existing worktree contains many unrelated user changes | Data/code loss from broad edits | Make targeted patches only, preserve unrelated user changes, and stage only the intended workflow files. |

## Open Questions

- The latest no-credentials session check returned `authenticated=false`; account existence remains unknown, and the user has not explicitly said “ready.” Actual inference remains paused.
- The active runtime uses experimental letterbox adaptation for 640×480 clips. Any resulting scores must remain research-only and clearly labeled as adapted/unvalidated, not native-resolution validated outputs.
