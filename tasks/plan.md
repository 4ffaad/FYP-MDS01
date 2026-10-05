# Implementation Plan: Reliable Patient Review Intake

## Overview

Repair the patient-folder workflow so a selected folder includes every supported EEG recording and every video in one owner-scoped case, the video-detection model path is actually invoked, all report fields are extracted locally and saved automatically to the owner-only profile when the case is created, and Workspace/Patient History navigation presents one clear active destination. Resolve the observed upload failure at the runtime-contract boundary without weakening streamed-upload privacy. Preserve model-contract and clinical-use limits.

## Architecture Decisions

- Keep the current raw `application/octet-stream` upload contract. The stale Compose backend was rebuilt after the user explicitly authorized resetting the disposable Postgres volume. The backend storage volume was retained, then its orphaned encrypted files were removed after a zero-reference dry run; model volumes were preserved.
- Keep all selected EEG candidates in the neutral-name encrypted ZIP; the backend already creates and processes one recording row per extracted EEG and continues when a sibling recording fails.
- Use the existing owner-scoped VSViG job route for every selected video, associated with the same case. Submit sequentially because the backend allows only one active detection job at a time. Keep full-frame blur/audio exclusion and show model results as research-only.
- Automatically parse the selected report through the development-only same-origin loopback endpoint; the parser never persists the source file. Save all extracted details in the encrypted owner-only profile once the case is created and display them in Patient Review without an approval step. Do not place patient details in URLs or browser storage.
- Make the Workspace link active only on Workspace routes. Rename the case-history navigation label to Patient History, remove the redundant Patients heading, and show owner-scoped patient names in default summaries without report text; use the case reference when no name was extracted.
- The effective runtime has experimental 640×480 letterbox adaptation enabled. Preserve that operator setting and mark adapted video evidence unvalidated/research-only. The user explicitly authorized a bounded local smoke run on one supplied EEG and one public demo clip; do not treat those results as clinical evidence or start a large batch without a separate request.

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
- [x] Only the route currently being viewed is marked current; extracted details appear automatically in the owner-scoped case page without a verification badge or approval action.

### Phase 4: Verification and runtime
- [x] Run focused backend and frontend tests, full relevant suites, formatter/linter/type checks, and production build. (One pre-existing local change remains in `backend/tests/test_upload_draft_postgres_concurrency.py`; no unrelated files were reformatted.)
- [x] Verify the rebuilt Compose backend's streamed-upload OpenAPI contract, current Alembic head, H5 runtime contract, and pinned VSViG runtime using the repository runbook.
- [x] Run one supplied EEG through the actual H5 service against disposable SQLite and one public demo clip through pinned VSViG; remove temporary media/results and preserve PostgreSQL. No patient names or source filenames were emitted.
- [x] Run `git diff --check` and review the final diff without disturbing pre-existing worktree changes.

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Running Compose backend is older than the checked-out client/API contract | Draft and video binary uploads fail with 422 | Rebuild/recreate `backend` and verify runtime OpenAPI. The user explicitly authorized resetting only the disposable Postgres volume; private storage/model volumes were preserved. |
| Processing every clip can overwhelm the single-job video runtime | Rejections, duplicate jobs, or resource pressure | Submit sequentially and respect existing capacity/error semantics; never fan out uploads concurrently. |
| Supplied 640×480 clips differ from the native 1920×1080 VSViG contract | Adapted results are experimental and not equivalent to native validated inputs | The effective runtime already enables letterbox adaptation; preserve provenance, label results research-only, and request approval before real-data inference. The observed longest clip is below the runtime's 3600-second duration limit. |
| Patient details are sensitive and extracted without an approval step | Accidental exposure or misleading report content | Keep the source report transient on the device, encrypt saved fields in the owner-only profile, show only the patient name in owner summaries, and show full extracted details only in the owner-only Patient Review. |
| Existing worktree contains many unrelated user changes | Data/code loss from broad edits | Make targeted patches only, preserve unrelated user changes, and stage only the intended workflow files. |

## Open Questions

- No account-based browser upload was performed during the real-media smoke run. The H5 service was invoked locally with disposable SQLite, and the VSViG runtime was invoked directly; neither created user-facing database records.
- The active runtime uses experimental letterbox adaptation for 640×480 clips. Any resulting scores must remain research-only and clearly labeled as adapted/unvalidated, not native-resolution validated outputs.

## Follow-up: Independent Intake and Video Queue Backpressure (2026-10-01)

- [x] Preserve the combined patient-folder workflow and add an EEG-only folder workflow that does not require a report or upload videos.
- [x] Provide three dashboard entry points: EEG + video, EEG only, and video only.
- [x] When the video API returns queue-full (429), wait for a job already accepted in this intake to finish, then safely retry the unaccepted clip. Preserve stop-and-review behavior when an accepted job's status is uncertain.
- [x] Keep the current clip's upload/stage visible and collapse the per-clip list by default for large batches.
- [x] Match review-video face detections to the current OpenPose head landmarks; use full-frame blur when the match is missing or ambiguous.
- [x] Document the visible pipeline stages and known deployment security limits. Avoid logging patient identifiers or every internal function call.
- [x] Verify with focused browser/backend tests, existing full suites, and the local public demo clip. Preserve the Postgres and private storage volumes.

## Follow-up: Dashboard Query and Storage Hardening (2026-10-01)

- [x] Replace per-session recording and flagged-window reads in the case summary with the existing bulk repository helpers; a regression test confirms five SELECTs for four EEG cases.
- [x] Add path-bound AES-GCM envelopes for new files and atomic legacy rewrapping on successful materialization. Regression tests cover cross-session replay rejection, draft promotion, and legacy reads.
- [x] Rewrap all five legacy envelopes found in the local private storage volume on 2026-10-01; zero legacy or unreadable files remained afterward, and no database rows were changed.
- [x] Run the full backend suite, frontend format/lint/type/build checks, and the focused intake/browser suites.
- [x] Verify Compose backend health and keep the existing PostgreSQL data volume.
- [ ] Process the full supplied media collection as a batch. The inventory is about 1,016 files including two large archives; the bounded smoke run is not evidence that every file passes.

## Follow-up: Synchronized VEEG Review Completion (2026-10-02)

### Overview

Complete the existing metadata-based EEG/video review so a reviewer can account for every uploaded clip, see linked clips against the EEG source clock, and understand why other clips remain unpaired. Validate the workflow with synthetic browser fixtures first, then a bounded run on the selected supplied case. Keep EEG and video model outputs separate and research-only.

### Current implementation

- The backend already encrypts Nicolet sync anchors and resolved offsets, and links clips only when the full uploaded folder produces one unique metadata match.
- The EEG result page currently loads only clips linked to the selected recording. It does not show same-case clips that are unmatched, ambiguous, pending, or linked to another recording.
- EEG scores, source markers, and video coverage are shown in separate timeline components. Source-marker selection can seek the video, but there is no shared source-clock playhead for all rows.
- The waveform viewer is already opt-in and disabled by default because retained EEG remains biometrically sensitive. This follow-up does not change that privacy setting.

### Architecture decisions

- Reuse the owner-filtered video-jobs API, encrypted sync projection, and existing time-mapping helper; no schema migration is planned.
- Preserve the supplied contract: only unique filename-token, frame-count, frame-rate, and clock-anchor matches become links. Do not add manual pairing or guessed offsets. Show unresolved clips with a safe status instead.
- Use EEG source-clock time for score, marker, and video rows. Keep acquisition gaps visible and avoid seeking into footage outside verified coverage.
- Use no patient filenames in API responses, UI labels, screenshots, test fixtures, or logs.
- Before frontend edits, follow `frontend/AGENTS.md` and read the relevant installed Next.js guidance under `frontend/node_modules/next/dist/docs/`.

### Task List

#### Phase 1: Make every clip outcome visible

- [x] Task 7: Add a case-scoped sync inventory to EEG review. Show clips linked to the selected EEG, clips linked to another EEG, and unresolved clips with safe statuses. Keep the existing synchronized player for unique matches; never expose original names or permit a forced pairing.
- [x] Task 8: Add one EEG source-clock overview connecting model-score windows, imported EEG markers, and verified video coverage. Selecting a marker or score time should seek only when a linked clip covers that time; keep gaps and out-of-coverage times explicit.

#### Checkpoint: Review behavior

- [x] Synthetic tests cover linked, unmatched, ambiguous, pending, unavailable, and linked-to-another-recording jobs without cross-case leakage.
- [x] Browser tests verify score/marker-to-video seeking, acquisition-gap behavior, and clear unresolved-clip states at desktop and mobile sizes.

#### Phase 2: Verify the selected case

- [ ] Task 9: Run the bounded end-to-end review on the previously audited two-EEG, 26-video case after the owner account is available. Confirm every accepted clip has a visible outcome; compare with the audit baseline of 17 metadata links and 9 unresolved clips when the same folders are selected.
- [ ] Verify readable clips can show their privacy-processed review even when pose or model admission fails, and that the UI says no score was produced. Do not treat 640×480 adapted output as equivalent to the native 1920×1080 contract.
- [ ] Record aggregate results and any remaining blockers in the video runbook without patient names, source filenames, or raw report text. Do not reset the database or process the full collection for this bounded check.

#### Checkpoint: Demo ready

- [ ] The selected case shows all accepted EEG/video files, the unique metadata links, unresolved outcomes, source-marker timing, and protected video review in one review flow.
- [ ] EEG/VSViG performance or clinical validity is not inferred from this workflow check; no clinical-use threshold or Grad-CAM display is added without separate validated evidence.

### Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| A clip has no unique metadata match | It cannot be safely synchronized | Keep it unpaired, show a safe unresolved state, and inspect the source metadata; do not guess an offset. |
| EEG views use different time origins | Marker or score seeks land on the wrong video frame | Use the EEG source clock for every timeline row and test gaps, negative starting offsets, and known anchors. |
| Low-resolution video fails VSViG admission | No model score is available | Preserve the privacy-only review when possible and clearly separate review availability from score availability. |
| Signal waveform remains disabled by default | The demo lacks raw EEG traces | Keep the existing opt-in privacy gate; decide on signal exposure separately from this synchronization milestone. |
