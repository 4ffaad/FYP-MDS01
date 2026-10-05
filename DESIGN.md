# MDS01 interface

A task-focused research workspace with a calm, light neumorphic visual language.
A single patient-folder intake groups the selected report, any number of EEG
recordings, and every video clip into one opaque case. EEG and video remain
independent processing paths; the case view brings their review status and
evidence together.

## Source of truth

Tokens live in [globals.css](frontend/src/app/globals.css). Shared controls live in [components/ui](frontend/src/components/ui), with Hugeicons through [Icon.tsx](frontend/src/components/Icon.tsx). This guide describes the implemented system; it does not prescribe another theme or a marketing layout.

| Role                     | Value                 |
| ------------------------ | --------------------- |
| Canvas / panels          | `#e8ebf1` / `#e8ebf1` |
| Muted / soft surface     | `#dfe3eb` / `#eef1f6` |
| Primary / secondary text | `#182334` / `#47566b` |
| Quiet text               | `#5b6a7e`             |
| Divider / control border | `#cbd2dd` / `#b8c1cf` |
| Interactive blue / hover | `#3978bd` / `#205d9d` |
| Review / destructive     | `#f3e8d2` / `#9f3036` |

The existing `teal` utility token names map to blue. Reuse them consistently.
Use soft paired light/dark shadows on raised surfaces, inset shadows for inputs
and progress wells, one-pixel neutral borders, and generous rounded corners.
Keep text contrast high; use saturated blue for primary actions and focus. Warm
amber marks review attention; reserve red for destructive or failed states.
Avoid gradients and decorative glass effects.

## Layout and hierarchy

- The desktop sidebar is 16rem wide; mobile keeps the same links behind a top-bar menu. Page content aligns to a 1320px maximum with 24px horizontal gutters, reduced to 16px on small screens.
- Desktop navigation groups **Patient cases** and **New patient review** under Workspace, EEG upload/reviews under EEG tools, and Video upload/reviews under Video tools. Each modality screen has two local tabs for upload and past results. On mobile, the same navigation opens from the top bar. Only mark the link for the current route active; keep one consistent navigation order across routes.
- The workspace greets the signed-in user by display name when available and offers three clear starts: combined EEG + video at `/upload`, EEG only at `/upload/eeg`, and video only at `/video-detection`. Combined intake uses one folder for report extraction, EEG recordings, and related camera clips; EEG-only intake does not require a report and ignores videos. Lead with cases needing review, then show patient-case, processing, flagged-window, EEG-recording, and video-clip totals from owner-scoped case summaries. Keep modality totals in one grouped panel; do not add sample patients, fabricated activity, or trend charts without real time-series data.
- Keep the case queue scannable: status filters with counts, patient/case identity, EEG and video volume, review status, latest upload or job time, and a direct case link. Search by patient name or case reference and modality filtering sit below the status filters. An empty queue explains how a report, EEG recordings, and video clips become one case.
- `/upload` is the canonical combined patient-folder intake. One folder creates one case; selected EEGs are packaged together and video jobs run independently in the video service's single-worker queue. The browser advances through a full queue without sending another clip until the service has capacity. A single 50–100% model-input blur setting applies to the selected clips; OpenPose reads transient source frames, and the clinician review video blurs a face only when it matches the tracked person's head landmarks, with full-frame fallback otherwise. EEG signal obfuscation is the optional EEG privacy setting.
- Left-align headings, explanatory text and empty states. Use one clear primary action.
- Use a small set of raised surfaces, inset controls, and neutral dividers. Avoid nested cards and heavy outlines.
- Keep form options visible together; avoid panels nested inside panels, decorative icon tiles, redundant badges and repeated warnings.
- Use consistent soft surfaces, readable type, clear file inventories, and restrained interaction motion. Keep upload copy task-oriented; retain research/model caveats near results where they help interpret scores.
- Preserve the MDS01 wordmark. Do not substitute stock medical icons for the brand.

## Typography and controls

Use the local system sans stack already declared in CSS. No font download is needed.
Body text is 15px with a 1.6 line height; screen headings are generally 32–40px and semibold. Use monospace and tabular numerals for IDs, timestamps and measurements.

Use existing shadcn/Radix controls for dialogs, sliders, buttons and tabs. Plain links and native form controls are appropriate where they cover the interaction. Format JSX as readable blocks; do not compress an entire section onto one line.

Icons support labels. Keep them generally 16–20px, using the shared Hugeicons wrapper. Icon-only controls need an accessible name and a usable target area.

## Score and privacy language

- Development: **Development score — not a probability**.
- Uncalibrated H5: **Uncalibrated model score**, without percentage confidence.
- Calibrated H5: **Estimated window probability**, explicitly one four-second window with a two-second stride.
- Keep model name/version and research-only status findable. No whole-recording confidence badge.
- Use flagged-window counts, exact intervals and waveform context to guide review. No flagged windows does not mean a patient is seizure-free.
- Video upload runs pose readiness, VSViG, and protected review-video creation in one job. Keep scores, patch Grad-CAM, face-redaction coverage, and the protected player together on the result screen. Do not expose the separate legacy privacy utility in the main navigation.
- Video detection runs OpenPose on transient normalized frames, extracts 15
  RGB patches, then blurs each patch individually before VSViG inference. The
  owner-scoped review player shows the encrypted audio-free video with tracked
  face blur, full-frame fallback, skeleton overlay, score timeline, and a
  patch-level Grad-CAM for the strongest-scoring window. The CAM attributes
  relative score contribution to time × 15 graph nodes, then maps each node to
  its 128×128 source patch; it is not pixel-level localization or a clinical
  explanation. Label scores as research flags for review, not diagnoses.
- Never display original patient filenames or identifying container metadata.

## Interaction checks

Preserve skip navigation, visible focus, native keyboard behavior, loading/error/empty states and reduced-motion support. Test desktop and mobile, including long IDs and the waveform's horizontal canvas. Errors must remain visible and actionable. Deletion uses the existing alert dialog; it is not an opportunity for decorative warning cards.

Keep the app light-only for this pass. Add new themes, animation or component variants only when an actual workflow calls for them.
