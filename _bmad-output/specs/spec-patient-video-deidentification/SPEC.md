---
id: SPEC-patient-video-deidentification
companions:
  - video-contract.md
  - evaluation-plan.md
  - architecture-diagrams.md
  - ../../../AGENTS.md
  - ../../../docs/backend.md
  - ../../../docs/privacy-research.md
sources:
  - ../../planning-artifacts/research/technical-privacy-preserving-patient-video-de-iden-2026-08-26/research.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Patient video privacy pipelines

## Why

MDS01 needs a separate video privacy feature that transforms patient video into safer research outputs without sending the video into EEG processing or a clinical/action model. The required flow is intentionally narrow: upload video, choose one or more privacy pipelines, produce policy-labeled outputs, and delete the source and transient material. This gives the project a place to compare privacy transformations while keeping model inference out of scope.

## Capabilities

- **CAP-1**
  - **intent:** A user can submit a video privacy job and select one or more privacy profiles without creating or invoking an EEG/model job.
  - **success:** A valid fixture produces an opaque job ID and `202` processing response; the job runs only the selected privacy profiles and never calls the EEG/H5 pipeline.

- **CAP-2**
  - **intent:** The system can run each selected privacy profile independently and produce a separate policy-labeled output.
  - **success:** `pose-only` produces an encrypted derived pose artifact and `face-redacted` produces an encrypted redacted-video artifact when their checks pass; one profile failure does not silently alter another profile's output.

- **CAP-3**
  - **intent:** A user can inspect the video privacy job and its outputs in a dedicated UI/API area.
  - **success:** The UI/API shows opaque IDs, profile, output type, status, safe technical metadata, quality flags, and research-only warnings without exposing source media, patient references, private paths, or the full pose artifact by default.

- **CAP-4**
  - **intent:** The system fails closed when common validation, profile processing, or output inspection is incomplete.
  - **success:** Unsupported media, decode errors, unsafe streams, missing privacy coverage, and output-integrity failures publish no unsafe output and return bounded error categories.

- **CAP-5**
  - **intent:** The project can evaluate each privacy profile for residual identity leakage and transform quality before making a stronger privacy claim.
  - **success:** A reproducible report records profile-specific identity/linkage risk, sensitive-attribute leakage, temporal or face coverage, non-video leakage, and human review findings; it does not require an action model.

## Constraints

- The subsystem is `video → privacy pipeline(s) → output`. It must not invoke EEG preprocessing, the H5 runtime, action analysis, clinical inference, or model scoring.
- A `VideoPrivacyJob` is independent of an EEG session. An optional session link may support navigation later, but it must not change processing semantics.
- The initial profile registry contains `pose-only` and opt-in `face-redacted`. Shared validation, stream removal, and metadata scrubbing are mandatory preflight, not a user-facing privacy result.
- Raw video, decrypted frames, audio, subtitles/data streams, original metadata, and transient processing files remain private and are deleted after processing according to the configured retention policy.
- Public responses expose only generated identifiers, profile/output type, safe technical metadata, processing state, quality flags, and bounded error text. They never expose patient references, original filenames, filesystem paths, source media, hashes, or full pose artifacts by default.
- Routes remain thin; repositories own database access, privacy services own processing, and long-running work is scheduled through FastAPI `BackgroundTasks`.
- Each profile is isolated behind a `VideoPrivacyPipeline` interface. Privacy detectors such as pose or face detection are transforms, not clinical/action models.
- Outputs are research-only risk reduction. No profile may be called anonymous without an approved threat model, evaluation evidence, and review.

## Non-goals

- EEG processing, H5 inference, action recognition, clinical labels, clinical explanations, or model scores.
- A learned spatio-temporal anonymizer or a formal anonymity/differential-privacy guarantee.
- Video/EEG synchronization or any requirement that a video job have an EEG session.
- Silent support for multi-person scenes. The first release must detect unsupported extra people or fail closed.
- Public raw-video access or unrestricted download of privacy outputs.

## Success signal

On a synthetic or consented fixture, a researcher can open the Video Privacy area, select `pose-only`, `face-redacted`, or both, and receive separate research-only outputs. A storage/API audit proves that the source video and transient material are gone, no EEG/model code was invoked, each output is encrypted and policy-approved, and no public response leaks identifying metadata or filesystem details.

## Assumptions

- Audio is not needed for this privacy feature and is removed unconditionally during preflight.
- The initial fixture set is synthetic or consented research data and does not justify production privacy claims.
- The first release targets one primary patient per clip; scenes with additional people are flagged or rejected until a multi-person policy is approved.

## Open Questions

- Should a video job be linkable to an existing EEG session for navigation only, or completely independent in the first release?
- Should users download face-redacted outputs, or only view them through an authorized local review endpoint?
- What containers, codecs, duration, resolution, frame rate, and upload-size limits should be approved?
- What face-coverage and missed-detection thresholds are required before a `face-redacted` output may be retained?
- Should encrypted pose artifacts be retained for research, or should the first release retain only a summary?
- Which release audience and attacker model define the privacy gate?
