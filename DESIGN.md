# MDS01 interface

A task-focused research workspace. People upload one EEG archive and, separately,
one video; they inspect processing and review flagged windows. Video privacy is
a separate workflow. The interface must make those boundaries and the
limitations of the output clear.

## Source of truth

Tokens live in [globals.css](frontend/src/app/globals.css). Shared controls live in [components/ui](frontend/src/components/ui), with Hugeicons through [Icon.tsx](frontend/src/components/Icon.tsx). This guide describes the implemented system; it does not prescribe another theme or a marketing layout.

| Role | Value |
| --- | --- |
| Canvas / panels | `#ffffff` |
| Muted / soft surface | `#f5f5f7` / `#fafafc` |
| Primary / secondary text | `#1d1d1f` / `#333333` |
| Quiet text | `#707070` |
| Divider / control border | `#e0e0e0` / `#d2d2d7` |
| Interactive blue / hover | `#0066cc` / `#0056b3` |
| Caution / destructive | `#8a5a00` / `#b3261e` |

The existing `teal` utility token names map to blue. Reuse them consistently; do not introduce competing colors. Do not claim accessibility conformance from token names—check contrast for the actual foreground/background pair.

## Layout and hierarchy

- Shared header and page frame align to a 1320px maximum. Horizontal gutters are 24px, reduced to 16px on small screens.
- Three top-level destinations: **EEG analysis**, **Video privacy**, and **Video detection**. Upload is an EEG action, not a fourth workspace.
- Left-align headings, explanatory text and empty states. Use one clear primary action.
- Use space and dividers for structure. Reserve bordered panels for interactive data, upload targets and independently reviewable content.
- Keep form options visible together; avoid panels nested inside panels, decorative icon tiles, redundant badges and repeated warnings.
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
- Video privacy output is a research transform. Keep acknowledgement and quality caveats near its download action.
- Video detection publishes an encrypted owner-scoped privacy-safe review
  artifact (face-redacted model input; full-frame-blurred, audio-free preview with
  skeleton overlay) alongside prediction/evidence metadata; it never publishes source
  playback. The keypoint labels in model evidence identify input regions, not
  clinical explanations.
- Never display original patient filenames or identifying container metadata.

## Interaction checks

Preserve skip navigation, visible focus, native keyboard behavior, loading/error/empty states and reduced-motion support. Test desktop and mobile, including long IDs and the waveform's horizontal canvas. Errors must remain visible and actionable. Deletion uses the existing alert dialog; it is not an opportunity for decorative warning cards.

Keep the app light-only for this pass. Add new themes, animation or component variants only when an actual workflow calls for them.
