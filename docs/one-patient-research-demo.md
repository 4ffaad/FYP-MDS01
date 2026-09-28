# One-patient local research/demo workflow

This guide covers the canonical folder intake at `/upload`; `/patient-intake` redirects there for compatibility. It is a local research workflow, not a clinically validated or production-ready patient system.

## Start the application

From the repository root, open two terminals. In the first, run the frontend;
this also creates local config and installs its locked dependencies if needed:

```sh
npm run dev
```

In the second terminal, start the backend, local H5 research runtime, database,
and pinned video assets:

```sh
docker compose up --build
```

The setup-generated Compose selection enables the local H5 profile. It requires
both ignored files under `backend/model/`: `best_seizure_model.h5` and
`model-contract.json`. They are bind-mounted read-only. The profile pins the
reviewed contract hash; the backend verifies the contract, artifact hash,
input/output shape, dtype, and output activation at startup. Missing or
mismatched assets fail closed; no substitute is selected. To explicitly run
the deterministic development stub, use
`docker compose -f docker-compose.yml up --build` instead.

The H5 scores are uncalibrated model outputs. They are not probabilities, diagnoses, or evidence of clinical validation. The signed-in local account is not checked for a clinical credential.

## Select one folder

Open **New patient review**, then select exactly one patient folder. The application recognizes:

- One or more supported EEG candidates: Nicolet `.e`, EDF/EDF+, or an MNE Nicolet `.data` file with a same-directory, same-stem `.head` sidecar. Every candidate appears as a separate selectable recording; included sources are processed in one EEG session.
- Exactly one `.doc` or `.docx` report. On macOS the host Next.js development server uses `/usr/bin/textutil` to create an in-memory draft from readable labeled fields and unlabelled report text. Every draft row is editable, removable, and selectable. There is no required Hospital ID field; include it only if it belongs in the case. Other operating systems fail closed and allow manual entry. DOB is never converted into age.
- Zero or more AVI, MP4, MOV, or WebM video candidates.

The `.data`/`.head` match is a format-sidecar rule, not an EEG/video relationship. File names never pair an EEG with a video. Unsupported files are counted but are not sent to the API. The EEG-only archive contains only selected EEG sources under neutral names; report and video bytes are submitted through their separate paths.

## Review patient details before saving

Report extraction is only a draft. Labeled details and unlabelled text are shown as separate editable rows; no field is auto-approved. Review, edit, unselect, or remove each row before confirming. If text exceeds the local review limit, check the original and add any missing details manually. No single identifier is required.

After the EEG session is created, FastAPI encrypts only the reviewed detail rows with an AES-GCM key derived from `MDS01_STORAGE_KEY`. New profiles use payload version 3; existing version-1 and version-2 profiles remain readable. The encrypted profile is owner-scoped and bound to its case ID. Generic case/session responses remain de-identified; only the dedicated authenticated profile endpoint returns the reviewed fields to the owner. The source report and unselected rows are not stored or passed to models. The case detail and combined report pages display all saved fields while keeping EEG and video outputs separate.

The confirmation is an account attestation. This local demo does not verify that the account holder is a doctor or clinician.

## Configure EEG and video together

The same screen shows both modalities and keeps their processing paths separate:

- EEG uses the selected privacy profile and the reviewed 256 Hz, 18-channel, four-second-window contract. Discontinuous `.e` segments stay separate through resampling, filtering, and windowing; window times retain elapsed source offsets. Positive recordings with gaps retain encrypted timestamped windows rather than a misleading continuous EDF clip.
- VSViG preflight uploads an encrypted temporary copy to the local backend, checks technical metadata, deletes the copy, and runs no model. VSViG uses **1920×1080** input. The local H5 profile experimentally resizes smaller videos to that geometry while preserving aspect ratio; scores are not validated as equivalent to native input. Other profiles need `VSVIG_ALLOW_LETTERBOX_ADAPTATION=true`. The preview-only path runs its own bounded video-privacy preflight and does not produce a model score.
- A VSViG-eligible clip still requires preflight and explicit per-case association confirmation. For smaller videos that pass the separate privacy utility's bounds, the operator can choose one preview-only clip: full-frame blur runs first, then the pinned Lightweight OpenPose model generates an optional body-joint overlay on the blurred frames. This path produces no VSViG score and no facial Action Units. The case report shows its privacy-safe preview and sampled-frame counts.
- Folder selection, age, and matching names never automatically pair an EEG with video. The screen always states that EEG/video clock alignment is unverified.

The EEG session and its profile can be completed when every supplied video is blocked. The preview-only path is not synchronized analysis and does not establish that the body belongs to the EEG subject. There is no synchronized multimodal timeline until an authoritative clock relationship is supplied and reviewed.

## Data lifecycle and API boundaries

1. The report is parsed locally into bounded draft fields. Only explicitly selected, reviewed fields are sent to the owner-protected profile endpoint.
2. The client packages all selected EEG sources into one neutral-named EEG-only ZIP and stages it through the existing encrypted upload-draft API; the backend creates one recording row per source.
3. FastAPI finalizes an owner-scoped asynchronous EEG session; existing validation, de-identification, processing, inference, retention, and cleanup rules remain in force.
4. Only after the session returns its opaque case reference does the client send the selected detail rows to the owner-protected profile API for encryption and storage.
5. A clip must be selected and explicitly confirmed before VSViG preflight; only those selected clips are uploaded for the check. Eligible VSViG clips and preview-only clips are separate owner-scoped jobs; preview-only jobs can be attached to the case ID and retain only an encrypted blurred/annotated output and preview until expiry.

Do not put patient data, report text, original file names/paths, private H5 weights, secrets, or generated archives in Git, logs, screenshots, or external services.

## Concrete limits before a broader demo

- VSViG uses 1920×1080 input. The local H5 profile enables experimental resizing for smaller clips; validate those scores separately from native-resolution inputs. If adaptation is disabled, smaller clips may still be eligible for privacy-plus-pose preview only; each clip must pass the privacy utility's own technical preflight. Do not infer association from file names.
- No authoritative EEG/video synchronization or clock offset is established. A same-patient association is not a timing claim.
- The local account's review checkbox does not authenticate clinician credentials.
- The H5 contract/artifact is pinned for research/demo use, but no clinical validation claim or diagnosis is supported.
- Legacy report text conversion is macOS-only. Unrecognized labels/sections require manual review; the parser never invents values. Age is only taken from an explicit Age label.
- Standard Compose startup also verifies the separately managed VSViG/OpenPose assets. If that bundle or its reviewed contract is unavailable, both VSViG detection and the OpenPose preview fail closed even though their preflight checks are available.
