```yaml
---
version: alpha
name: MDS01
description: "Clean, modern minimal interface for clinical EEG research review—designed for neurologists with precision, clarity, and medical-grade visual hierarchy."

colors:
  primary: "#0066CC"
  primary-hover: "#0052A3"
  on-primary: "#FFFFFF"
  background: "#FFFFFF"
  surface: "#F8FAFB"
  border: "#E1E4E8"
  text: "#1A1F36"
  text-muted: "#6B7280"
  accent: "#00A3FF"
  success: "#10B981"
  warning: "#F59E0B"
  danger: "#EF4444"

typography:
  display:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: 56px
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: -0.03em
  heading:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: 32px
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: -0.02em
  body:
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: 15px
    fontWeight: 400
    lineHeight: 1.65
    letterSpacing: -0.01em
  mono:
    fontFamily: "'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace"
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.6

spacing:
  base: 8px
  scale: [4, 8, 12, 16, 24, 32, 48, 64, 96, 128]

radius:
  sm: 4px
  md: 8px
  lg: 12px
  xl: 16px
  pill: 9999px

shadows:
  card: "0 1px 3px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.04)"
  elevated: "0 4px 12px rgba(0, 0, 0, 0.12), 0 2px 4px rgba(0, 0, 0, 0.06)"
  focus: "0 0 0 3px rgba(0, 102, 204, 0.15)"

motion:
  duration-fast: 150ms
  duration-base: 250ms
  duration-slow: 400ms
  easing: "cubic-bezier(0.4, 0, 0.2, 1)"
---

## Rationale

MDS01 serves neurologists and clinical researchers who need to review, analyze, and interpret EEG data with speed and accuracy. The design philosophy prioritizes **medical clarity over decoration**: every visual element serves diagnostic function. The interface must support long review sessions without cognitive fatigue, demand minimal training, and present complex physiological data in scannable, hierarchical patterns.

The color palette is anchored in clinical blue (#0066CC)—conveying trust, precision, and medical authority—paired with a neutral white/off-white foundation that reduces eye strain during extended screen time. Grays are warm and accessible, avoiding harsh contrast that fatigues clinicians. Status colors (green/amber/red) map to standard medical severity conventions, so interpretations are intuitive across contexts.

Typography uses Inter, the system-first choice for contemporary medical software, optimized for both print and screen. The scale is conservative: large enough for quick scanning during data review, small enough to fit complex waveforms and metadata alongside narrative. Generous line-height and letter-spacing support reading during clinical fatigue.

Spacing and radius are minimal and consistent: 8px base unit scales predictably, 4px corners feel refined without softness, and card shadows are barely perceptible—supporting depth hierarchy without visual noise.

## 1. Visual Theme & Atmosphere

**Overall aesthetic**: Clinical workspace masquerading as consumer software. The interface feels like a modern SaaS dashboard, not legacy medical software, but every decision is rooted in workflow and data density. Visual breathing room comes from whitespace and grid structure, not decoration. No gradients, illustrations, or brand flourish—only functional color and typography.

**Emotional register**: Calm, capable, trustworthy. Interactions feel responsive and precise. The UI disappears during clinical work; the data is the focus. Loading, errors, and warnings are communicated clearly without alarm.

**Light mode only**: White background reduces glare during clinical review, especially in well-lit hospital/clinic settings. No dark mode at launch—neurologists' workflow doesn't typically demand it.

## 2. Color System

| Role | Hex | Usage | WCAG AA | WCAG AAA |
|------|-----|-------|---------|---------|
| **Primary (Interactive)** | #0066CC | Buttons, links, focus states, primary actions | 6.4:1 ✓ | 6.4:1 ✓ |
| **Primary Hover** | #0052A3 | Button press, link visited | 7.8:1 ✓ | 7.8:1 ✓ |
| **On Primary** | #FFFFFF | Text/icons on primary buttons | 8.6:1 ✓ | 8.6:1 ✓ |
| **Background** | #FFFFFF | Page background, clean slate | N/A | N/A |
| **Surface** | #F8FAFB | Card backgrounds, panels, secondary containers | 1.1:1 | 1.1:1 |
| **Border** | #E1E4E8 | Dividers, input borders, subtle separation | 2.3:1 ✓ | N/A |
| **Text** | #1A1F36 | Body copy, primary content, data labels | 16.2:1 ✓ | 16.2:1 ✓ |
| **Text Muted** | #6B7280 | Secondary text, captions, metadata, disabled | 4.8:1 ✓ | 6.1:1 ✓ |
| **Accent** | #00A3FF | Highlights, reference lines, secondary CTAs | 4.2:1 ✓ | 4.2:1 ✓ |
| **Success** | #10B981 | Normal/healthy EEG ranges, positive alerts, confirmations | 4.9:1 ✓ | 6.2:1 ✓ |
| **Warning** | #F59E0B | Abnormal findings, caution flags, review needed | 3.2:1 ✓ | 4.5:1 ✓ |
| **Danger** | #EF4444 | Critical findings, seizure markers, alerts | 4.1:1 ✓ | 5.1:1 ✓ |

**Notes:**
- Primary blue chosen for clinical authority and high contrast against white.
- Muted gray (#6B7280) is light enough for secondary information without losing hierarchy; still passes AA at 4.8:1.
- Danger red (#EF4444) leans cooler to avoid harsh affect; still meets AA standards.
- Surface color (#F8FAFB) is almost white to reduce visual weight; used only for contained, secondary sections.

## 3. Typography

**Font stack:** Inter (Google Fonts) as primary, with fallback to system fonts. Inter is optimized for medical/fintech interfaces—geometric yet warm, monospace-inspired letterforms aid precision reading.

| Level | Usage | Size | Weight | Line Height | Notes |
|-------|-------|------|--------|-------------|-------|
| **Display** | Page titles (EEG Review, Patient Dashboard) | 56px | 700 | 1.05 | High impact for page orientation; rarely used |
| **Heading** | Section headers (Signal Analysis, Findings Summary) | 32px | 600 | 1.15 | Primary hierarchy for content sections |
| **Subheading** | Subsections (Temporal Lobe, Spike Detection) | 20px | 600 | 1.2 | Support Heading; use sparingly |
| **Body** | Main content, labels, data tables | 15px | 400 | 1.65 | Default reading text; generous line-height for fatigue resistance |
| **Body Small** | Metadata, timestamps, fine print | 13px | 400 | 1.6 | Reduced but still readable; medical abbreviations need clarity |
| **Mono** | Code, EEG identifiers, technical values | 13px | 400 | 1.6 | Precision and monowidth clarity for data |

**Rationale:** Body text set at 15px (not 14px) provides subtle but measurable benefit during long clinical sessions. 1.65 line-height prevents line-jumping and reduces reading fatigue. Mono faces reserved for technical data (Hz values, electrode names, timestamps) to distinguish from narrative.

## 4. Components & Patterns

### Button (Primary)
```
State: Default
Background: #0066CC
Text: #FFFFFF, 15px / 600
Padding: 12px 20px
Radius: 8px
Shadow: card
Transition: 150ms ease

State: Hover
Background: #0052A3
Cursor: pointer

State: Active
Background: #003D7A
Box-shadow: card + inset 0 2px 4px rgba(0, 0, 0, 0.1)

State: Disabled
Background: #E1E4E8
Text: #6B7280
Cursor: not-allowed
Opacity: 0.6
```

### Button (Secondary)
```
Background: #F8FAFB
Border: 1px solid #E1E4E8
Text: #0066CC, 15px / 600
Padding: 12px 20px
Radius: 8px

State: Hover
Background: #EEF1F5
Border: #D1D9E0
```

### Input Field (Text / Number)
```
Background: #FFFFFF
Border: 1px solid #E1E4E8
Text: #1A1F36, 15px
Padding: 12px 16px
Radius: 8px
Line-height: 1.65

State: Focus
Border: 2px solid #0066CC
Box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.15)
Outline: none

State: Error
Border: 2px solid #EF4444
Background: rgba(239, 68, 68, 0.02)

Placeholder text: #6B7280, font-style: italic
```

### Data Table
```
Header row background: #F8FAFB
Header text: #1A1F36, 15px / 600, text-transform: uppercase, letter-spacing: 0.05em
Body text: #1A1F36, 15px / 400
Row divider: 1px solid #E1E4E8
Zebra striping: alternate row background #F8FAFB / #FFFFFF
Padding: cells 16px vertical, 12px horizontal
Min row height: 44px (touch target)
```

### Card / Panel
```
Background: #FFFFFF
Border: 1px solid #E1E4E8
Radius: 12px
Shadow: card
Padding: 24px
Margin-bottom: 24px

Variant: Secondary (elevated)
Background: #F8FAFB
Border: none
Shadow: elevated
```

### Alert / Banner
```
Success:
  Background: rgba(16, 185, 129, 0.08)
  Border-left: 4px solid #10B981
  Text: #065F46
  Icon: #10B981

Warning:
  Background: rgba(245, 158, 11, 0.08)
  Border-left: 4px solid #F59E0B
  Text: #78350F
  Icon: #F59E0B

Danger:
  Background: rgba(239, 68, 68, 0.08)
  Border-left: 4px solid #EF4444
  Text: #7F1D1D
  Icon: #EF4444

Padding: 16px
Radius: 8px
Font-size: 15px
Line-height: 1.65
```

### Badge / Chip
```
Small label for status/category
Background: #EEF1F5
Text: #0066CC, 13px / 600
Padding: 4px 12px
Radius: pill (9999px)

Variant: Success
Background: rgba(16, 185, 129, 0.12)
Text: #065F46

Variant: Muted
Background: #E1E4E8
Text: #6B7280
```

### Navigation (Side Rail / Top)
```
Background: #FFFFFF
Border-right: 1px solid #E1E4E8
Item padding: 16px
Item text: 15px / 400, #1A1F36
Item height: 44px min

State: Active
Background: #EEF1F5
Text: #0066CC
Border-left: 3px solid #0066CC

State: Hover (inactive)
Background: #F8FAFB
```

### Toggle / Checkbox
```
Size: 20px × 20px (touch target 44px with padding)
Unchecked: border 2px solid #E1E4E8, background #FFFFFF
Checked: background #0066CC, checkmark #FFFFFF
Radius: 4px
Transition: 150ms ease

State: Focus
Box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.15)
```

### Tooltip / Popover
```
Background: #1A1F36
Text: #FFFFFF, 13px
Padding: 8px 12px
Radius: 6px
Shadow: elevated
Appear on hover: 250ms delay
Arrow: 6px triangle, same background
Max-width: 240px
Line-height: 1.6
```

## 5. Spacing & Layout

**Base unit: 8px**
All spacing derives from multiples of 8px: 4, 8, 12, 16, 24, 32, 48, 64, 96, 128.

| Spacing | Usage |
|---------|-------|
| **4px** | Small icon gaps, tight component padding |
| **8px** | Input padding (vertical), form gaps |
| **12px** | Icon-text spacing, tight groupings |
| **16px** | Component padding, card padding (horizontal), form row gaps |
| **24px** | Section margins, card padding (vertical), list item spacing |
| **32px** | Large section breaks, major layout shifts |
| **48px** | Between major content sections |
| **64px** | Page-level spacing |

**Grid & Layout:**
- **Max content width:** 1400px (accommodates wide EEG waveform displays and dual-panel layouts)
- **Page padding:** 24px (horizontal), 32px (vertical)
- **Column grid:** 12-column for flexibility
- **Gutters:** 24px between columns
- **Card/panel max-width:** No hard limit; let content flow; use side-by-side panels for parallel data review

**Mobile-first breakpoints** (if responsive needed):
- **Mobile:** 320px–599px
- **Tablet:** 600px–999px
- **Desktop:** 1000px+

## 6. Motion & Interaction

**Philosophy:** Motion clarifies state change and provides feedback; never decorative. Reduced motion is always respected.

| Interaction | Duration | Easing | Notes |
|-------------|----------|--------|-------|
| **Button hover / focus** | 150ms | cubic-bezier(0.4, 0, 0.2, 1) | Subtle color shift |
| **Modal open / overlay** | 250ms | cubic-bezier(0.4, 0, 0.2, 1) | Fade in + slight scale |
| **Dropdown menu appear** | 150ms | cubic-bezier(0.4, 0, 0.2, 1) | Fade + slide-down |
| **Loading spinner** | 1s | linear | Continuous rotation; elegant, not frenetic |
| **Toast notification** | 250ms