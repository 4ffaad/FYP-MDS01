---
title: 'Build standalone Video Privacy vertical slice'
type: 'feature'
created: '2026-08-26'
status: 'done'
review_loop_iteration: 0
baseline_commit: '4c0878a173ccc5fc0b02a9bdfdfcda6df1ad0137'
context:
  - /Users/daffa/Dev/fyp/AGENTS.md
  - /Users/daffa/Dev/fyp/_bmad-output/planning-artifacts/ux-designs/ux-fyp-2026-08-26/EXPERIENCE.md
  - /Users/daffa/Dev/fyp/_bmad-output/planning-artifacts/ux-designs/ux-fyp-2026-08-26/DESIGN.md
  - /Users/daffa/Dev/fyp/_bmad-output/planning-artifacts/research/technical-privacy-preserving-patient-video-de-iden-2026-08-26/digests/implementation-r1-1.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** MDS01 has no way to upload or privacy-transform patient video. The frontend must not imply that video enters the EEG/H5 pipeline, and the backend must not retain original media or identifiers in public responses.

**Approach:** Add one standalone Video Privacy job flow with a separate database model, private encrypted storage, FastAPI background processing, and a Next.js surface. Support one selected profile per job: Face-redacted using OpenCV face detection, and Pose-only using MediaPipe pose landmarks rendered without the original appearance. Retain only the transformed output and representative preview frame.

## Boundaries & Constraints

**Always:** Keep video jobs separate from EEG sessions and inference. Store binaries below `backend/storage/sessions/{job_id}/`, never in PostgreSQL. Use generated labels, scrub output metadata, remove original/transient files after processing, and never expose paths, client filenames, patient references, or source media. Use FastAPI `BackgroundTasks`. Label all outputs as research privacy transforms, not guaranteed anonymity. Validate stream type/size before processing and make download available only for backend-validated output; require acknowledgement for usable `Needs review` output.

**Ask First:** None for the approved v1 scope. Stop if implementation would require profile composition, clinical/action inference, retaining original media, or changing the reviewed EEG contract.

**Never:** Do not call EEG/H5/model services, analyze clinical action, claim anonymity, preview original media in the result surface, commit patient media/model assets, or use a learned anonymizer without a reviewed dataset and evaluation contract.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Face-redacted happy path | Valid MP4/MOV/WebM and `face-redacted` | 202 job; process frames, blur detected faces, remove audio/metadata, retain encrypted output and transformed preview | Job becomes `failed` with stage-safe message if output validation fails |
| Pose-only happy path | Valid video and `pose-only` | 202 job; render pose landmarks on a non-identifying background, retain encrypted output and preview | Job becomes `needs_review` if pose coverage is intermittent; download requires acknowledgement |
| Invalid upload | Unsupported type, missing stream, or over configured size | No usable job/output | 400/413 with no path or original filename in response |
| Missing/unsupported profile | Empty or unknown profile | No processing starts | 422 with supported profile IDs |
| Output unavailable | Job not ready, unusable, expired, or retention policy missing | No media download | 409/410 with safe status and next action |

</frozen-after-approval>

## Code Map

- `backend/app/database/models/eeg.py` -- add isolated `VideoPrivacyJob` status/profile metadata model without changing EEG tables or contracts.
- `backend/migrations/versions/012_video_privacy_jobs.py` -- Alembic migration for video job metadata.
- `backend/app/database/repository.py` -- add opaque job lookup/list/update helpers; never return private paths through API serializers.
- `backend/app/core/config.py` -- add video size, retention, and processor configuration using environment defaults.
- `backend/app/services/video_storage_service.py` -- encrypted upload/output storage under the job boundary, generated labels, cleanup, and safe materialization for processing/download.
- `backend/app/video_privacy/processor.py` -- adapter boundary for OpenCV face-redaction and MediaPipe pose-only transforms; scrub audio/metadata and emit quality flags.
- `backend/app/services/video_privacy_service.py` -- create jobs, schedule/process jobs, validate outputs, acknowledge usable caveats, and enforce cleanup/download policy.
- `backend/app/api/video_privacy.py` and `backend/app/main.py` -- protected endpoints for create/list/detail/acknowledge/preview/download; keep routes thin.
- `frontend/src/lib/types.ts` and `frontend/src/lib/api.ts` -- video job types, profile metadata, API calls, and safe response mapping.
- `frontend/src/app/video-privacy/page.tsx`, `frontend/src/app/video-privacy/[jobId]/page.tsx`, and `frontend/src/components/VideoPrivacyScreen.tsx` -- upload/profile and job-detail surfaces following the final UX spine.
- `frontend/src/components/AppShell.tsx` -- add `Video Privacy` as a peer navigation destination without altering EEG navigation semantics.
- `backend/tests/test_video_privacy.py` and `frontend/tests/e2e/video-privacy.spec.ts` -- unit/API/privacy edge cases and stub-backed browser acceptance tests.

## Tasks & Acceptance

**Execution:**
- [x] Add model, migration, repository, encrypted video storage, and configuration -- create a separate persistence/storage boundary.
- [x] Implement processor adapters and background service -- produce the two approved transformed outputs, quality flags, metadata-scrubbed files, and cleanup behavior.
- [x] Add video privacy API endpoints and safe serializers -- expose only opaque job state, generated labels, output metadata, preview, and download policy.
- [x] Add frontend upload/profile/job-detail routes and navigation -- present privacy-only stages, protected preview, quality acknowledgement, and no EEG/model language.
- [x] Add backend and Playwright tests -- cover validation, privacy boundaries, cleanup, status transitions, and both profiles using synthetic fixtures/mocks.
- [x] Update setup/readme documentation -- document video runtime dependencies, local test commands, and patient-data handling.

**Acceptance Criteria:**
- Given a valid supported video and one approved profile, when the user submits it, then a separate opaque video job is created and the UI shows preflight and privacy-only processing states.
- Given a completed job, when the user opens it, then the UI shows only the transformed representative frame, selected profile, quality flags, retention/expiry, and research-only wording.
- Given a `Needs review` output marked usable, when the user acknowledges the caveat, then the protected output download is enabled; otherwise it remains disabled.
- Given any API response or error, when it is inspected, then it contains no patient reference, original filename/path, source media, or EEG/H5/model fields.
- Given processing completes or fails, when private storage is inspected, then original/transient plaintext files are removed and only encrypted allowed artifacts remain.
- Given the existing EEG test suite runs, when the video feature is enabled, then EEG routes, model contracts, and existing browser tests continue to pass unchanged.

## Spec Change Log

## Design Notes

The processor is intentionally behind an adapter: privacy/storage/API code must not depend on MediaPipe internals. Pose-only writes landmarks to a non-identifying canvas; face-redacted writes a redacted video. Both outputs are audio-free and metadata-scrubbed. A missing optional processor dependency fails closed as a safe job failure, never as an unredacted passthrough.

## Verification

**Commands:**
- `PYTHONPATH=. .venv/bin/python -m unittest discover -s backend/tests -v` -- expected: existing and video tests pass.
- `cd frontend && npm run lint && npm run build && npm run test:e2e` -- expected: lint, production build, and stub browser tests pass.
- `cd frontend && npm run test:e2e:real` -- expected: existing real EEG canary workflow remains green when Docker/video dependencies are available.

**Manual checks:**
- Upload a consented/synthetic short video through `/video-privacy`; confirm no original preview/download, only generated labels, privacy-only stages, transformed preview, quality policy, and cleanup state.

## Suggested Review Order

**Processing boundary**

- Start with the service that owns job creation, fail-closed processing, cleanup, and retention policy.
  [`video_privacy_service.py:126`](../../backend/app/services/video_privacy_service.py#L126)

- Inspect the adapter that preflights streams, transforms frames, and validates encoded output.
  [`processor.py:33`](../../backend/app/video_privacy/processor.py#L33)

- Check encrypted input, retained artifacts, response-scoped materialization, and cleanup boundaries.
  [`video_storage_service.py:13`](../../backend/app/services/video_storage_service.py#L13)

**API and persistence**

- Trace the protected multipart entry point and safe media-response endpoints.
  [`video_privacy.py:29`](../../backend/app/api/video_privacy.py#L29)

- Review the isolated job schema and non-identifying quality metadata.
  [`video.py:30`](../../backend/app/database/models/video.py#L30)

- Confirm the production migration matches the isolated persistence boundary.
  [`012_video_privacy_jobs.py:13`](../../backend/migrations/versions/012_video_privacy_jobs.py#L13)

**Browser contract**

- Review upload/profile selection, privacy-only stages, transformed preview, and acknowledgement gating.
  [`VideoPrivacyScreen.tsx:57`](../../frontend/src/components/VideoPrivacyScreen.tsx#L57)

- Verify backend/stub mapping does not expose client filenames or EEG/model fields.
  [`api.ts:501`](../../frontend/src/lib/api.ts#L501)

**Verification and handoff**

- Start with privacy, cleanup, expiry, and fail-closed unit/API coverage.
  [`test_video_privacy.py:52`](../../backend/tests/test_video_privacy.py#L52)

- Confirm desktop/mobile browser behavior and the generated-label contract.
  [`video-privacy.spec.ts:7`](../../frontend/tests/e2e/video-privacy.spec.ts#L7)
