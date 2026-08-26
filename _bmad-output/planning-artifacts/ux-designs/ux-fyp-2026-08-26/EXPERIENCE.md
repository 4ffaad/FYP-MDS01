---
name: MDS01
status: final
sources:
  - ../../../../DESIGN.md
  - ../../research/technical-privacy-preserving-patient-video-de-iden-2026-08-26/research.md
updated: '2026-08-26'
---

# MDS01 — Experience Spine

This product has two separate research surfaces in one responsive web application. **EEG Review** exposes the complete EEG processing pipeline. **Video Privacy** exposes only the patient-video privacy workflow and its protected output. The surfaces share navigation and visual tokens, but a video job never enters the EEG model pipeline.

## Foundation

Responsive web application. Desktop/laptop is the primary surface for clinical research review; tablet and mobile support upload, progress, and output inspection. The existing frontend component system remains the implementation source for controls. `DESIGN.md` is the visual identity reference; this document owns behavior, information architecture, states, accessibility, and journeys.

The product is research-only. EEG predictions must remain labeled as research/development output. Video privacy results must be described as transformed outputs with quality caveats, not as a guarantee of anonymity.

## Information Architecture

| Surface | Reached from | Purpose |
|---|---|---|
| EEG Review | App open / navigation | Upload EEG and inspect the full EEG processing pipeline and research result |
| EEG session detail | EEG session row | Review stage-by-stage status, signal summary, explanation artifact, and result metadata |
| Video Privacy | Navigation | Upload a standalone patient video and choose privacy transform profiles |
| Video job detail | Video job row or upload completion | Monitor privacy processing and inspect protected output plus quality flags |
| Settings / system status | Existing application navigation | Environment and operational information; never a place to expose patient identifiers |

Top-level navigation must show `EEG Review` and `Video Privacy` as peers. Do not place video inside the EEG upload flow, and do not require a shared patient/session identifier to begin either workflow.

## Voice and Tone

Microcopy should be calm, direct, and operational. The visual brand voice lives in `DESIGN.md`.

| Do | Don't |
|---|---|
| `Choose a privacy profile` | `Make your video anonymous` |
| `Face redaction selected` | `Face hidden perfectly` |
| `Output ready for review` | `Your safe video is complete!` |
| `Privacy quality needs review: face detection was intermittent` | `Privacy failed` when processing completed with a caveat |
| `Research-only result` | `Diagnosis` or other clinical certainty |
| `Original removed according to policy` | `We deleted everything` without explaining the policy scope |

Avoid exposing patient names, original filenames, raw paths, or identifiers in visible UI, logs, error text, downloadable filenames, or example content. Use a generated label such as `Video upload 01` or a short job ID everywhere the UI needs to refer to the selected media.

## Privacy Boundary

The frontend must preserve this separation:

```text
EEG input → EEG privacy/de-identification → preprocessing → inference → explanation → research result

Video input → selected privacy profile(s) → protected video output → quality review
```

The Video Privacy surface must not show EEG stages, H5 runtime status, inference thresholds, clinical labels, or explanation artifacts. The EEG Review surface must not imply that a video was used as model input.

The video workflow offers one independent privacy profile per v1 job. The initial profile set is:

| Profile | What it communicates | What it does not claim |
|---|---|---|
| Pose-only | Produces the configured pose-based transformed output and retains pose landmarks/visual action structure | It is not action recognition, behavior classification, or a clinical model |
| Face-redacted | Applies face redaction to detected faces while retaining the rest of the video | It does not guarantee that every identity cue outside the face is removed |

Profile composition is deferred until backend composition semantics are reviewed. The UI must not present multiple simultaneous profiles as available in v1.

The first preview is a representative frame from the transformed output. The original video is never previewed in the result surface. Full protected playback can be added later without changing the privacy boundary.

Retention and download expiry are backend-provided policy values. If the backend does not provide a configured policy, the UI states that retention is not configured and keeps download disabled.

## Component Patterns

Behavioral rules; visual specifications live in `DESIGN.md`.

| Component | Surface | Behavioral rules |
|---|---|---|
| Application navigation | Global | `EEG Review` and `Video Privacy` are peer destinations. Active state is announced to assistive technology. |
| Upload surface | EEG + Video | Accept only configured formats. Show validation before processing. Never display the raw filesystem path. Disable the start action until a valid file is selected. |
| File summary | EEG + Video | Show only a generated non-identifying label, type, size, and non-identifying technical metadata. Never show the client filename, patient name, path, or embedded identifiers. Allow removal before processing. |
| EEG pipeline stage list | EEG | Shows upload, validation, de-identification, preprocessing, inference, explanation, and result states. Selecting a completed stage reveals a concise technical summary. |
| Video profile card | Video | Keyboard- and screen-reader-selectable single-choice group. Each card exposes purpose, transform, output expectation, and limitation. Selection is reversible before processing. |
| Video privacy stage list | Video | Shows preflight, the selected transform, encoding, output validation, and cleanup. Never inserts model or clinical stages. |
| Progress/status region | EEG + Video | Uses an `aria-live="polite"` region for meaningful transitions. Polling or refresh must not steal focus. Shows configured retention/expiry when supplied. |
| Protected output card | Video | Displays only a representative frame from transformed output. Provides profile summary, quality flags, retention/expiry, acknowledgement when required, and download. The original is never a result action. |
| Research result card | EEG | Clearly labels development-stub/research-only output and links to explanation artifacts only when available. |
| Status badge | EEG + Video | Uses a text label for every state and is never the only signal of completion, failure, or privacy quality. |
| Alert | EEG + Video | States what happened, impact, and next action. A warning does not masquerade as a failure. |

## State Patterns

### Shared upload states

| State | Treatment |
|---|---|
| Empty | Explain accepted input and provide one primary file-picker action. |
| File selected | Show safe summary, validation status, remove action, and enabled start action only when valid. |
| Unsupported or invalid | Keep the file picker available, identify the problem in plain language, and preserve no unsafe transient state. |
| Uploading | Show determinate progress when available; prevent duplicate submission. |
| Upload failed | Keep the user on the same surface with retry and remove actions. Do not reveal paths or server internals. |

### Session and system surfaces

| State | Surface | Treatment |
|---|---|---|
| Cold load | EEG session list, Video job list, Settings/system status | Show structural loading placeholders that match the eventual content order. Do not expose identifiers while data is loading. |
| Empty | EEG session list, Video job list | Explain that no sessions/jobs are available and provide the relevant upload action. Keep EEG and Video entry points separate. |
| Offline or stale | Session/job lists and status | Preserve the last safe state, state when data was last refreshed, and offer retry. Do not imply that a processing job completed while status is stale. |
| Permission denied | Session/job lists and Settings/system status | Show only the safe access message and next action. Never reveal whether a hidden patient/session record exists. |
| Load failure | All list/system surfaces | Show a concise retry message without server paths, patient references, or stack traces. |

### EEG states

| State | Treatment |
|---|---|
| Queued / processing | Stage list shows the current stage and a concise explanation of what is happening. |
| Completed | Completed stages remain visible; result and explanation sections unlock only when their artifacts exist. |
| Needs review | Identify the stage and evidence needed; do not silently continue with an invalid contract. |
| Failed | Identify the failed stage, provide a safe retry path, and keep the research-only boundary visible. |
| Research result ready | Show prediction metadata and explanation artifact with an explicit `Research-only result` label. |

### Video states

| State | Treatment |
|---|---|
| No profile selected | Explain that a privacy profile is required; disable processing. |
| Preflight | Validate stream/metadata and show that the original is being handled under the configured privacy policy. |
| Transforming | Show selected profile(s), current transform stage, and progress when available. |
| Output ready | Show protected output card, representative transformed frame, profile summary, quality flags, configured retention/expiry, and download action. |
| Quality caveat | Keep output available only if the backend marks it usable; show the exact caveat and require explicit review acknowledgement before download. |
| Failed | State whether the failure happened during preflight, transformation, encoding, validation, or cleanup. Offer retry without exposing the original. |
| Original removed | Show this as a separate cleanup status, not as proof that the transformed output is identity-free. |
| Retention unavailable | State that retention is not configured and keep download disabled until a backend policy is supplied. |

## Interaction Primitives

- Click, tap, and keyboard activation perform the same primary actions.
- File selection is explicit; drag-and-drop is an optional enhancement, never the only route.
- `Enter` or `Space` activates a focused profile or button. `Escape` closes dialogs and returns focus to the invoking control.
- Processing status may refresh automatically, but refresh never moves the user's focus or scroll position.
- Long-running processing shows a stable stage status rather than a busy animation alone.
- Download actions are disabled until output validation says the transformed file is available.
- The v1 video preview is a representative frame from transformed output. If protected playback is added later, it must not autoplay video or audio and must provide visible play and mute controls.
- Respect `prefers-reduced-motion`; replace progress animation with text updates where needed.
- Do not use carousels, hidden hover-only actions, infinite scroll, or modal stacks deeper than one level.

## Accessibility Floor

Behavioral requirements; contrast and focus visuals are defined in `DESIGN.md`.

- Meet WCAG 2.2 AA for the responsive web surface.
- Every upload control, profile card, stage, status badge, preview control, and download action has an accessible name and state.
- Profile cards use a real radio or checkbox group semantics appropriate to whether composition is supported. The selected profile is announced, not conveyed by border color only.
- The current processing stage is available in text and exposed through a polite live region; avoid rapid announcements for every percentage change.
- Keyboard focus follows reading order: navigation → page heading → upload/profile controls → status → output.
- Focus indicators use `{components.focus-ring}` and remain visible against `{colors.background}` and `{colors.surface}`.
- Minimum target size is 44px for primary interactive controls.
- If protected video playback is added, it has captions or an equivalent text description when audio or spoken content is part of the research material; audio is muted by default.
- Large text, browser zoom, and reflow must not hide the primary action or privacy caveat.
- Error messages are associated with the relevant input and do not rely on color or iconography alone.

## Responsive & Platform

| Viewport | Behavior |
|---|---|
| `≥ 1000px` | Side rail visible. EEG may use two-column evidence/detail layout. Video may show upload/profile controls beside the output/status column. |
| `600–999px` | Navigation compresses. Pipeline and output panels stack when needed. Profile cards remain fully selectable without hover. |
| `< 600px` | Single-column flow. File summary, profile cards, stage list, quality flags, and download action stack in reading order. |

The first implementation is responsive web, not a native mobile app. Mobile supports the full privacy workflow but is optimized for upload, status, and output review rather than dense EEG waveform analysis.

## Key Flows

### Flow 1 — Review an EEG session (Dr. Aisha, research workstation)

1. Dr. Aisha opens **EEG Review**.
2. She selects an EEG archive and sees safe file validation feedback.
3. She starts processing and the stage list moves through validation, de-identification, preprocessing, inference, and explanation.
4. She opens the completed stage summaries while the result is being prepared.
5. **Climax:** the session detail shows the complete pipeline as completed, a clearly labeled research-only result, and its explanation artifact without exposing the original file or patient reference.

Failure: the reviewed contract or model artifact is invalid. The UI stops at the failing stage, explains that processing was blocked for safety, and offers a safe retry path.

### Flow 2 — Create a protected video output (Maya, clinical research assistant)

1. Maya opens **Video Privacy** from the application navigation.
2. She selects one patient video without selecting or attaching an EEG file.
3. The upload surface validates the video and presents the available privacy profiles.
4. She selects **Face-redacted** and reads its purpose and limitation before starting.
5. The job detail shows preflight, face redaction, output validation, and cleanup; it does not show EEG or model stages.
6. **Climax:** the protected-output card presents the transformed video, the exact selected profile, quality flags, and a download action while stating that the result is privacy-transformed rather than guaranteed anonymous.

Failure: face detection is intermittent. The output remains visibly marked `Needs review`, the quality caveat is attached to the output, and Maya can retry or choose a different configured profile.

### Flow 3 — Use pose-only privacy (Maya, follow-up review)

1. Maya starts another job from **Video Privacy**.
2. She selects **Pose-only** and reviews the explanation that the output preserves pose landmarks rather than the patient's visible appearance.
3. She starts processing and waits on the privacy stage list.
4. She opens the output preview and checks the quality flags.
5. **Climax:** she downloads only the pose-only transformed output, with the profile and processing metadata retained in the job record.

Failure: pose transformation or output validation fails. The job identifies the failing privacy stage, keeps the download unavailable, and offers a safe retry without exposing the original.

## Finalized v1 Constraints

- One privacy profile is selected per Video Privacy job. Profile composition is deferred.
- The first video preview is a representative transformed frame. Full protected playback is deferred.
- A `Needs review` output is downloadable only after explicit acknowledgement and only when the backend marks it usable.
- Retention and download expiry come from backend policy metadata; missing policy disables download.
