# Implementation Plan: Reliable Patient Review Intake

## Overview

Repair the patient-folder workflow so a selected folder includes every supported EEG recording and every video in one owner-scoped case, the video-detection model path is actually invoked, patient details are reviewed on a later intake step, and Workspace/Patient History navigation presents one clear active destination. Resolve the observed upload failure at the runtime-contract boundary without weakening streamed-upload privacy. Preserve model-contract and clinical-use limits.

## Architecture Decisions

- Keep the current raw `application/octet-stream` upload contract. The live Compose backend currently advertises an older `multipart/form-data` contract, so rebuild/recreate the backend from the checked-out source rather than regressing the client to multipart uploads.
- Keep all selected EEG candidates in the neutral-name encrypted ZIP; the backend already creates and processes one recording row per extracted EEG and continues when a sibling recording fails.
- Use the existing owner-scoped VSViG job route for every selected video, associated with the same case. Submit sequentially because the backend allows only one active detection job at a time. Keep full-frame blur/audio exclusion and show model results as research-only.
- Move report-detail review to a second in-memory intake step. Continue to persist only explicitly approved details; do not place patient details in URLs or browser storage.
- Make the Workspace link active only on Workspace routes. Rename the case-history navigation label to Patient History, remove the redundant Patients heading, and show a privacy-safe recent-case list in Workspace without names or report text.
- Keep experimental 640×480 letterbox adaptation disabled by default. Do not run the supplied HUKM recordings through inference until the required use/consent approval is confirmed; use synthetic fixtures for regression tests.

## Task List

### Phase 1: Reproduce and repair upload contracts
- [ ] Confirm the current source and live container upload request contracts; rebuild only the backend service and verify it advertises streamed binary uploads.
- [ ] Normalize structured FastAPI validation errors so UI alerts never render `[object Object]` and never echo request payloads.
- [ ] Add focused regression tests for the stale-contract symptom and safe error display.

### Phase 2: Complete modality processing
- [ ] Preserve all EEG candidates automatically and verify the archive contains every candidate with neutral names.
- [ ] Submit every video through the existing owner-scoped VSViG route under the created case, one at a time; reflect terminal status without listing individual clips on intake.
- [ ] Add focused tests for multiple EEGs, multiple videos, queue/capacity behavior, and case association.

### Checkpoint: Processing path
- [ ] Backend contract and processing tests pass.
- [ ] Synthetic E2E proves every selected video reaches detection, not only the separate privacy-preview utility.

### Phase 3: Intake and navigation
- [ ] Make the first intake step show EEG/video totals and the single EEG privacy choice only.
- [ ] Move report-detail opt-in to the next intake step while preserving explicit review and cancellation behavior.
- [ ] Rename Cases navigation to Patient History, remove redundant Patients labeling, correct exclusive active navigation state, and show recent de-identified cases on Workspace.
- [ ] Update E2E expectations and capture settled desktop/mobile renders.

### Checkpoint: UX and privacy
- [ ] No original patient filenames, raw report text, or identifying metadata appear on intake or Workspace summaries.
- [ ] Only the route currently being viewed is marked current; detail opt-in remains explicit.

### Phase 4: Verification and runtime
- [ ] Run focused backend and frontend tests, full relevant suites, formatter/linter/type checks, and production build.
- [ ] Verify the rebuilt Compose backend's streamed-upload OpenAPI contract and pinned VSViG runtime using the repository runbook.
- [ ] Inspect the supplied dataset read-only for supported technical metadata only; do not run patient inference until approval and any experimental preprocessing choice are confirmed.
- [ ] Run `git diff --check` and review the final diff without disturbing pre-existing worktree changes.

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Running Compose backend is older than the checked-out client/API contract | Draft and video binary uploads fail with 422 | Rebuild/recreate only `backend`; preserve PostgreSQL volume and verify runtime OpenAPI after restart. |
| Processing every clip can overwhelm the single-job video runtime | Rejections, duplicate jobs, or resource pressure | Submit sequentially and respect existing capacity/error semantics; never fan out uploads concurrently. |
| Supplied 640×480 clips differ from the native 1920×1080 VSViG contract; one exceeds the 900-second limit | Model jobs may be rejected or adaptation may be unvalidated | Keep adaptation and limits unchanged by default; request explicit authorization before any real-data inference or operator configuration change. |
| Patient details are sensitive and report extraction is opt-in | Accidental persistence or display | Keep details only in component memory until the second-step review; save only checked details; keep source report transient. |
| Existing worktree contains many unrelated user changes | Data/code loss from broad edits | Make targeted patches only; do not reset, format unrelated files, commit, or push. |

## Open Questions

- Before processing the supplied HUKM clips, confirm that local research inference is covered by the applicable retrospective-use/consent approval.
- If approved, separately decide whether to enable the explicitly experimental letterbox adaptation; this does not make outputs equivalent to native-resolution validated inputs.
