# MDS01 design system

MDS01 is a clinical decision-support workspace for clinicians and clinical researchers. The interface should feel precise, calm, and native to an Apple workstation: near-invisible chrome, generous white space, confident typography, and one clear interactive blue.

This system is adapted from the local Apple design reference at `apple/DESIGN.md`. It keeps the reference's white and parchment tones, SF Pro-style type stack, hairline separators, pill actions, and restrained elevation. It does not copy Apple's logo, product content, photography, or consumer shopping patterns.

## Product truth

The frontend has three jobs:

- `/upload` lets a clinician submit an EEG ZIP and choose a privacy method.
- `/dashboard` shows where submitted analyses stand.
- `/results/[jobId]` shows the development prediction, confidence, evidence window, privacy method, and non-clinical boundary.

The interface never renders patient references, original filesystem paths, unrestricted files, or original filenames. Client-side jobs use generated labels such as `Recording 01`.

## Apple-inspired visual language

### Color tokens

- **Canvas:** `#ffffff`, the primary working surface.
- **Parchment:** `#f5f5f7`, used for page bands, footers, selected control areas, and quiet supporting surfaces.
- **Pearl:** `#fafafc`, used for near-white input and utility surfaces.
- **Ink:** `#1d1d1f`, used for headings and primary content.
- **Muted ink:** `#333333` for readable supporting copy; `#7a7a7a` for captions and secondary metadata.
- **Hairline:** `#e0e0e0` for the quiet 1px boundaries used to organize real content.
- **Action Blue:** `#0066cc` for primary actions, links, focus, selected navigation, and confirmed states.
- **Focus Blue:** `#0071e3` for keyboard focus rings.
- **Sky Blue:** `#2997ff` for active analysis details when a brighter blue is needed.
- **Amber and red:** reserved for warnings, non-clinical notices, errors, and seizure-indicated development output. They are semantic status colors, not brand accents.

No decorative gradients, glows, glass surfaces, or colored shadows are used. The workflow is light-first because the user is reviewing technical clinical information on a workstation.

### Typography

Use the system stack so Apple platforms resolve to SF Pro without shipping a font file:

```css
"SF Pro Text", "SF Pro Display", -apple-system, BlinkMacSystemFont, system-ui, sans-serif
```

- Display headings use weight 600, tight tracking, and a 1.07 to 1.12 line height.
- Body text uses 400 weight, approximately 17px, and approximately 1.47 line height where space permits.
- Strong labels use weight 600. Weight 500 is not part of the system.
- Monospace is limited to opaque IDs, timestamps, model versions, and technical measurements.

### Shapes and elevation

- Full-screen workspace surfaces are rectangular.
- Utility panels use an 18px radius and a 1px hairline border.
- Primary and secondary actions use a full pill radius.
- Compact utility controls use an 8px radius.
- No shadow is used on panels, buttons, text, or navigation. Separation comes from white versus parchment and from hairlines.
- A pressed button scales to `0.97` to acknowledge the action.

## Layout

The shared shell uses a slim white navigation bar with MDS01, `New analysis`, `Dashboard`, privacy context, and environment state. It stays visually quiet so the current task carries the page.

Pages use a centered reading frame with generous vertical space:

- Upload uses a working panel and a compact process explanation.
- Dashboard uses a structured list of runs and a simple empty state.
- Results use a headline panel for prediction and confidence, followed by the evidence window and run details.

White and parchment create rhythm without decorative lines. A panel only exists when it groups a real task or a related set of data.

## Components

- `button-primary`: Action Blue, white text, full pill, 44px minimum height.
- `button-secondary`: white surface, Action Blue border and text, full pill.
- `StatusBadge`: icon, label, and semantic state color. Color is never the only status signal.
- `AttentionHeatmap`: bounded inline SVG, loaded only on the result route. It is an inspection aid, not an automatic clinical explanation.
- `AppShell`: slim navigation and persistent privacy boundary.
- `PrivacyOption`: config-driven radio selection from `PRIVACY_METHODS`.

Use `@phosphor-icons/react` for icons. Do not draw a second icon family or use emoji as UI controls.

## Motion and interaction

Motion is intentionally quiet. A single page entrance provides hierarchy, upload progress provides feedback, and buttons use a short pressed state. All motion is disabled or reduced under `prefers-reduced-motion: reduce`.

Focus is visible with a 2px Action Blue ring. Touch targets are at least 44px where practical. Form controls have visible labels, and errors identify both the problem and the recovery action.

## Performance rules

- Use system fonts and no image assets for the current product UI.
- Do not import the EEG visualization on upload or dashboard routes.
- Do not request signal data until a result route opens.
- Keep signal requests bounded and abort them when the route is abandoned.
- Keep page transitions and status polling local to the relevant client components.

## Dials

- `DESIGN_VARIANCE`: 3/10. Apple-like precision and symmetry suit a clinical workstation.
- `MOTION_INTENSITY`: 2/10. Only hierarchy and feedback motion are needed.
- `VISUAL_DENSITY`: 4/10. The UI is airy, but run metadata remains scannable.
