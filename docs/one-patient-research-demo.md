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

- One or more supported EEG candidates: Nicolet `.e`, EDF/EDF+, or an MNE Nicolet `.data` file with a same-directory, same-stem `.head` sidecar. All supported EEGs in the selected folder are included automatically and processed as separate recordings in one EEG session.
- Exactly one `.doc` or `.docx` report. On macOS the development UI automatically submits the selected report to its same-origin loopback-only `/api/patient-report` parser, which uses `/usr/bin/textutil` and returns bounded fields without storing the source file. Every extracted populated field is saved automatically to the owner-only encrypted case profile when processing creates the case; there are no per-field controls or extra intake confirmation step. The profile starts auto-extracted and unverified. An owner may later mark the full profile reviewed from the case page after comparing its values with the source report; this is data review, not clinical validation. DOB is never converted into age.
- Zero or more AVI, MP4, MOV, or WebM video candidates.

The `.data`/`.head` match is a format-sidecar rule, not an EEG/video relationship. File names never pair an EEG with a video. Unsupported files are counted but are not sent to the API. The EEG-only archive contains all supported EEG sources from the selected folder under neutral names; report and video bytes are submitted through their separate paths.

## Automatically extract patient details

Extracted fields are grouped together in a read-only disclosure that stays collapsed by default because report values may contain identifiers. Every non-empty extracted field is included automatically in the encrypted, owner-only case profile as part of the normal processing workflow; there are no per-field controls or intake approval step. The case page labels machine-extracted values unverified. If text exceeds the local extraction limit, check the original report. No single identifier is required.

After the EEG session is finalized and the owner-scoped case exists, FastAPI encrypts the complete extracted detail set with an AES-GCM key derived from `MDS01_STORAGE_KEY`. New profiles use payload version 3; existing version-1 and version-2 profiles remain readable. Automatically extracted profiles have `verification_status=auto_extracted`, with no reviewer or review timestamp. Only reviewed profiles contribute a name or bounded report summary to default case-list/detail responses; unreviewed profile fields remain available only through the authenticated, owner-scoped profile endpoint. The original DOC/DOCX source is not retained or passed to models. The case detail page displays saved fields, including identifying fields, only to the authenticated owner.

Selecting a folder authorizes this local research workflow to extract and save its report fields. That does not authenticate the account holder as a doctor or clinician and does not mark the profile reviewed. The separate case-page review action records only that the owner compared the extracted values; it does not assert clinical credentials or validate model output.

## Configure EEG and video together

The same screen shows both modalities and keeps their processing paths separate:

- EEG uses the selected privacy profile and the reviewed 256 Hz, 18-channel, four-second-window contract. Discontinuous `.e` segments stay separate through resampling, filtering, and windowing; window times retain elapsed source offsets. Positive recordings with gaps retain encrypted timestamped windows rather than a misleading continuous EDF clip.
- VSViG preflight uploads an encrypted temporary copy to the local backend, checks technical metadata, deletes the copy, and runs no model. VSViG uses **1920×1080** input. The local H5 profile experimentally resizes smaller videos to that geometry while preserving aspect ratio; scores are not validated as equivalent to native input. Other profiles need `VSVIG_ALLOW_LETTERBOX_ADAPTATION=true`. The preview-only path runs its own bounded video-privacy preflight and does not produce a model score.
- All supported videos in the explicitly selected patient folder are included for sequential VSViG job submission; each job performs server-side contract preflight before privacy transformation and inference. The separate preview-only path can still be used for a manually chosen clip: full-frame blur runs first, then the pinned Lightweight OpenPose model generates an optional body-joint overlay on blurred frames. This path produces no VSViG score and no facial Action Units. The case report shows its privacy-safe preview and sampled-frame counts.
- Folder selection, age, and matching names never automatically pair an EEG with video. The screen always states that EEG/video clock alignment is unverified.

The EEG session and its profile can be completed when every supplied video is blocked. The preview-only path is not synchronized analysis and does not establish that the body belongs to the EEG subject. There is no synchronized multimodal timeline until an authoritative clock relationship is supplied and reviewed.

## Data lifecycle and API boundaries

1. Folder selection triggers local loopback-only report extraction. The source document is processed in memory and is not stored by the parser.
2. The client packages all selected EEG sources into one neutral-named EEG-only ZIP and stages it through the existing encrypted upload-draft API; the backend creates one recording row per source.
3. FastAPI finalizes an owner-scoped asynchronous EEG session; existing validation, de-identification, processing, inference, retention, and cleanup rules remain in force.
4. After the session returns its opaque case reference, the client sends all extracted fields to the owner-protected extraction endpoint. FastAPI encrypts them and records the profile as auto-extracted/unverified; the original report is not persisted.
5. Every supported video in the selected patient folder is uploaded one at a time to the owner-scoped VSViG job endpoint, which performs preflight before processing. Preview-only clips remain a separate owner-scoped workflow and retain only an encrypted blurred/annotated output and preview until expiry.
6. The owner may later mark the complete profile reviewed through the case page after comparing it with the source report. Default case summaries expose the patient name only after that action; no report text or identifying detail is added to Workspace summaries.

Do not put patient data, report text, original file names/paths, private H5 weights, secrets, or generated archives in Git, logs, screenshots, or external services.

## Concrete limits before a broader demo

- VSViG uses 1920×1080 input. The local H5 profile enables experimental resizing for smaller clips; validate those scores separately from native-resolution inputs. If adaptation is disabled, smaller clips may still be eligible for privacy-plus-pose preview only; each clip must pass the privacy utility's own technical preflight. Do not infer association from file names.
- No authoritative EEG/video synchronization or clock offset is established. A same-patient association is not a timing claim.
- Automatically extracted profile fields are unreviewed by default; the account does not establish clinical credentials, and a profile review action is not clinical validation.
- The H5 contract/artifact is pinned for research/demo use, but no clinical validation claim or diagnosis is supported.
- Legacy report text conversion is macOS-only. Unrecognized labels/sections require manual review; the parser never invents values. Age is only taken from an explicit Age label.
- Standard Compose startup also verifies the separately managed VSViG/OpenPose assets. If that bundle or its reviewed contract is unavailable, both VSViG detection and the OpenPose preview fail closed even though their preflight checks are available.
