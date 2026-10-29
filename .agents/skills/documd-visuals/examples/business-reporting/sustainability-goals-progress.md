# Sustainability Goals Progress — Commitments With Rings (Infographic)

**Best for**: a public or internal page showing progress against sustainability commitments
**Avoid when**: commitments are measured in different units that need a table
**Answers**: each goal, its target year, and how far the organisation has moved

```infographic
infographic list-grid-circular-progress
theme
  colorPrimary #2b66c4
  palette
    - #2b66c4
    - #2f9e44
    - #f3a33c
    - #d1242f
    - #7048e8
    - #0f9b9b
    - #c16f8a
    - #7c5a3d
data
  title Climate Commitments
  desc Progress against 2030 targets
  lists
    - label Renewable electricity
      value 92
    - label Fleet electrification
      value 48
    - label Water intensity
      value 74
    - label Supplier disclosure
      value 31
```

## Data Shape

`lists` where each item carries a numeric `value` — the share of the target, 0–100. The ring prints it in
the centre (`92%`), so the label names the *goal*, not the metric, and the baseline year belongs in the
page `desc`. ⚠️ `desc` is **not** rendered by this item: a percentage written there shows up as `0%` in
the ring.

## Key Options

| Option | Effect |
|---|---|
| `infographic list-grid-circular-progress` | Rings with labels beneath — reads as a scoreboard |
| `value 92` | The ring's share, 0–100. It is the only thing the ring can draw |
| `list-grid-progress-card` | Bar form; easier when values differ in magnitude |
| `list-grid-badge-card` | Drop the ring and keep the text if progress is qualitative |

## Pitfalls

- ❌ Progress written as text (`desc 92% of target`) → ✅ `value 92`; the item renders no description, so the ring silently reads 0%
- ❌ Baseline missing → ✅ "% of target" means nothing without the baseline year; state it in the title
- ❌ Overstating progress → ✅ disclose method in the surrounding text, not the diagram
- ❌ Eight commitments → ✅ pick the ones with governance; the rest are marketing claims

## Alternatives

| Variant | Use instead |
|---|---|
| Goal progress inside one team | `onboarding-task-progress.md` |
| Adoption trend over time | `feature-adoption-trend.md` |
| Company-wide metric board | `leadership-metric-board.md` |

<!-- source: AntV Infographic syntax docs + template list (`list-grid-circular-progress`, item `circular-progress`: `label` + numeric `value`) -->
