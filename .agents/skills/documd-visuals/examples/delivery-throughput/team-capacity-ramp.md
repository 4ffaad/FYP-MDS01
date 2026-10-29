# Team Capacity Ramp — Hiring In Waves (Infographic)

**Best for**: showing how a team grows across hiring waves and what each wave unlocks
**Avoid when**: the reader needs FTE cost modelling (use a spreadsheet)
**Answers**: how many people arrive in each wave and what they are for

```infographic
infographic sequence-cylinders-3d-simple
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
  title Platform Team Ramp
  desc Three hiring waves across FY27
  sequences
    - label Wave 1 — Q1
      desc 4 engineers, core platform
    - label Wave 2 — Q2
      desc 8 engineers, data platform
    - label Wave 3 — Q3
      desc 12 engineers, reliability
```

## Data Shape

`sequences` where each item is a wave; the cylinder height comes from order, so keep wave sizes in `desc` as
text. Three to four waves is the readable range.

## Key Options

| Option | Effect |
|---|---|
| `infographic sequence-cylinders-3d-simple` | Stacked cylinders with a sense of growth |
| `sequence-ascending-stairs-3d-simple` | Staircase variant — better when waves follow strict order |
| `sequence-roadmap-vertical-*` | Use when waves have dates and deliverables |

## Pitfalls

- ❌ Cumulative vs per-wave confusion → ✅ say which one `desc` reports
- ❌ Waves without purpose → ✅ each wave should name what it unlocks, or it reads as headcount inflation
- ❌ Using 3-D shapes for a serious finance audience → ✅ switch to a text list for budget conversations

## Alternatives

| Variant | Use instead |
|---|---|
| Effort shape across a launch | `launch-effort-curve.md` |
| Headcount plan with dates | `hiring-plan-roadmap.md` |
| Capacity versus cost | `capacity-cost-dual-axis.md` (vega-lite) |

<!-- source: AntV Infographic syntax docs + template list (`sequence-cylinders-3d-simple`) -->
