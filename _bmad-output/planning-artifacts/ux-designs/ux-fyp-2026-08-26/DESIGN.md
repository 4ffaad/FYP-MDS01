---
name: MDS01
description: Clinical research workspace for separate EEG review and patient-video privacy processing.
status: final
sources:
  - ../../../../DESIGN.md
colors:
  primary: '#0066CC'
  primary-hover: '#0052A3'
  on-primary: '#FFFFFF'
  background: '#FFFFFF'
  surface: '#F8FAFB'
  border: '#E1E4E8'
  text: '#1A1F36'
  text-muted: '#6B7280'
  accent: '#00A3FF'
  accent-ink: '#1A1F36'
  success: '#10B981'
  success-surface: '#ECFDF5'
  success-ink: '#065F46'
  warning: '#F59E0B'
  warning-surface: '#FFFBEB'
  warning-ink: '#78350F'
  danger: '#EF4444'
  danger-surface: '#FEF2F2'
  danger-ink: '#7F1D1D'
typography:
  display:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: 56px
    fontWeight: 700
    lineHeight: 1.05
  heading:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: 32px
    fontWeight: 600
    lineHeight: 1.15
  body:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: 15px
    fontWeight: 400
    lineHeight: 1.65
  mono:
    fontFamily: "SF Mono, Monaco, Cascadia Code, Roboto Mono, Consolas, monospace"
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.6
rounded:
  sm: 4px
  md: 8px
  lg: 12px
  xl: 16px
  pill: 9999px
spacing:
  base: 8px
  page-horizontal: 24px
  page-vertical: 32px
  section: 48px
  card: 24px
components:
  button-primary:
    background: '{colors.primary}'
    foreground: '{colors.on-primary}'
    radius: '{rounded.md}'
  button-secondary:
    background: '{colors.surface}'
    foreground: '{colors.primary}'
    border: '{colors.border}'
    radius: '{rounded.md}'
  card:
    background: '{colors.background}'
    border: '{colors.border}'
    radius: '{rounded.lg}'
  file-summary:
    background: '{colors.surface}'
    border: '{colors.border}'
    radius: '{rounded.md}'
  eeg-pipeline-stage-list:
    background: '{colors.background}'
    border: '{colors.border}'
    radius: '{rounded.lg}'
  video-profile-card:
    background: '{colors.background}'
    border: '{colors.border}'
    radius: '{rounded.lg}'
  video-privacy-stage-list:
    background: '{colors.background}'
    border: '{colors.border}'
    radius: '{rounded.lg}'
  progress-status-region:
    background: '{colors.surface}'
    border: '{colors.border}'
    radius: '{rounded.md}'
  protected-output-card:
    background: '{colors.background}'
    border: '{colors.border}'
    radius: '{rounded.lg}'
  research-result-card:
    background: '{colors.background}'
    border: '{colors.border}'
    radius: '{rounded.lg}'
  status-badge:
    radius: '{rounded.pill}'
    success-background: '{colors.success-surface}'
    success-foreground: '{colors.success-ink}'
    warning-background: '{colors.warning-surface}'
    warning-foreground: '{colors.warning-ink}'
    danger-background: '{colors.danger-surface}'
    danger-foreground: '{colors.danger-ink}'
  alert:
    success-background: '{colors.success-surface}'
    success-foreground: '{colors.success-ink}'
    warning-background: '{colors.warning-surface}'
    warning-foreground: '{colors.warning-ink}'
    danger-background: '{colors.danger-surface}'
    danger-foreground: '{colors.danger-ink}'
  focus-ring:
    color: '{colors.primary}'
    outline: '2px solid {colors.primary}'
    shadow: '0 0 0 3px rgba(0, 102, 204, 0.15)'
updated: '2026-08-26'
---

## Brand & Style

MDS01 is a calm clinical workspace for neurologists and clinical researchers. The interface is precise, restrained, and data-led: the UI should disappear during review so the pipeline state, signal evidence, and privacy output remain easy to understand.

The visual direction is inherited from the repository's existing `DESIGN.md`: light mode only, Inter typography, clinical blue interaction, neutral white surfaces, and small functional status colors. This UX `DESIGN.md` normalizes those decisions into the BMad token contract and adds only the EEG/video component names needed for handoff. There are no gradients, illustrations, decorative hero graphics, or celebratory effects.

The EEG Review and Video Privacy destinations are peers in the same application shell. Their visual language is shared, but their information and status semantics must remain distinct: EEG communicates research processing; Video communicates privacy transformation and output readiness.

## Colors

The palette is unchanged from the existing product direction.

| Role | Token | Use |
|---|---|---|
| Primary interactive | `{colors.primary}` | Primary actions, links, active navigation, focus states |
| Primary hover | `{colors.primary-hover}` | Hover and pressed interaction |
| Canvas | `{colors.background}` | Page background |
| Surface | `{colors.surface}` | Secondary panels, table headers, inactive containers |
| Border | `{colors.border}` | Dividers, input borders, panel separation |
| Primary text | `{colors.text}` | Headings, body copy, data labels |
| Muted text | `{colors.text-muted}` | Metadata, helper text, timestamps |
| Accent | `{colors.accent}` with `{colors.accent-ink}` | Reference lines and secondary highlights only; never small text without the ink pairing |
| Success | `{colors.success}` with `{colors.success-surface}` / `{colors.success-ink}` | Completed processing and safe output availability |
| Warning | `{colors.warning}` with `{colors.warning-surface}` / `{colors.warning-ink}` | Review needed, partial detection, quality caveats |
| Danger | `{colors.danger}` with `{colors.danger-surface}` / `{colors.danger-ink}` | Failed processing or critical warning |

Status colors always accompany a text label. Color alone never communicates whether a stage completed or whether an output is safe to use. Body text and status foreground/background pairings target WCAG 2.2 AA for normal text; solid warning, danger, and success colors are used for borders or icons, not as small white text backgrounds.

## Typography

Use Inter or the system fallback stack for all interface copy. Use the mono token for technical values such as sample rates, channel names, frame counts, file hashes, job identifiers, and timestamps when precision matters.

Page titles orient the reviewer; headings divide workflow sections; body text explains what happened and what the reviewer can do next. Avoid all-caps prose and avoid using display typography for operational messages.

## Layout & Spacing

Use the 8px base scale and the existing 12-column desktop grid. The maximum content width is 1400px so EEG evidence and video output comparisons can remain visible without forcing a narrow reading column.

Desktop/laptop is the primary review surface. At widths below 1000px, two-column review layouts stack vertically. At widths below 600px, navigation becomes compact and file/profile controls stack; no essential action is hidden behind hover.

Page padding is `{spacing.page-horizontal}` horizontally and `{spacing.page-vertical}` vertically. Major sections use `{spacing.section}` separation. Cards use `{spacing.card}` internal padding unless the content is a dense table or waveform.

## Elevation & Depth

Use borders and whitespace for hierarchy. The standard card uses a one-pixel border and the existing subtle card shadow. Elevated surfaces are reserved for transient dialogs, menus, and output previews. Do not use shadows to imply clinical certainty or privacy strength.

## Shapes

Inputs and small controls use `{rounded.sm}`. Buttons and compact controls use `{rounded.md}`. Cards and larger panels use `{rounded.lg}`. Status badges may use `{rounded.pill}`. Keep corners consistent between the upload surface, processing stages, and protected-output preview.

## Components

### Application navigation

Use a white side rail on desktop and a compact top navigation on smaller screens. The active destination uses a light neutral background, primary-blue text, and a primary-blue leading marker. The navigation must expose **EEG Review** and **Video Privacy** as separate destinations.

### Upload surface

The upload surface is a bordered card with a clear file-picker action, accepted-format guidance, selected-file summary, and a primary action to begin processing. The video upload must not imply that an EEG file is required. Patient media is represented only by a generated non-identifying label and technical metadata needed for processing.

### File summary

The file summary uses the generated job label, configured type, size, and safe technical metadata. Never render the client filename, patient name, filesystem path, or embedded identifying metadata.

### EEG pipeline stage list

EEG uses a vertical or horizontal stage list with explicit labels, descriptions, status text, and timestamps where available. The list includes upload, validation, de-identification, preprocessing, inference, explanation, and result.

### Video profile card

Each video privacy profile is presented as a selectable card with its name, plain-language purpose, included transform, output expectation, and limitations. One profile is selected per v1 job. Selection state is conveyed by a visible border/focus treatment and text, not by color alone. Initial profiles are **Pose-only** and **Face-redacted**.

### Video privacy stage list

Video uses a shorter privacy-transform list containing preflight, the selected transform, encoding, output validation, and cleanup. It must never display EEG inference, explanation, or clinical result stages.

### Progress/status region

The progress/status region uses a quiet surface and explicit text status. Determinate progress is shown when available; a stable stage label remains visible when percentage progress is unavailable. Status transitions use the `{components.status-badge}` treatment and do not rely on color alone.

### Protected output card

The completed video surface shows a protected-output card with a representative frame from the transformed output, profile name, output format, processing status, privacy quality flags, backend-provided retention/expiry, and an explicit download action. The original file is never previewed or offered as the result of the privacy workflow.

### Research result card

The EEG result card separates model metadata from interpretation and visibly labels development-stub or research-only output. It never uses clinical diagnosis language.

### Status badge

Use text labels such as `Queued`, `Processing`, `Ready`, `Needs review`, `Failed`, and `Original removed`. Use `{components.status-badge}` surface/foreground pairings and preserve a readable label at every size.

### Alert

Use `{components.alert}` for messages that explain what happened, impact, and next action. Warnings must distinguish a quality caveat from a processing failure. Use the status-specific surface and ink pairings rather than solid status colors behind small white text.

## Do's and Don'ts

| Do | Don't |
|---|---|
| Make EEG and Video Privacy visible as separate destinations | Combine them into one ambiguous upload wizard |
| Show exactly which privacy transform produced an output | Call a transformed video “anonymous” without qualification |
| Pair status color with a text label and explanation | Communicate privacy or clinical state by color alone |
| Keep patient files out of mocks, examples, and repository assets | Embed real patient frames or identifying filenames in the frontend |
| Show research-only language for EEG outputs | Present a development-stub result as a clinical diagnosis |
| Use calm, precise state changes | Add celebratory animations, gradients, or decorative medical imagery |
