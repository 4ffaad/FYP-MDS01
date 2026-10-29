# Revenue Staircase Plan — Quarterly Targets Stepping Up (Infographic)

**Best for**: showing a quarterly plan where each quarter steps up from the last
**Avoid when**: the reader needs variance against plan (use a chart)
**Answers**: the target for each quarter and the assumption behind the step

```infographic
infographic sequence-ascending-stairs-3d-simple
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
  title FY27 Revenue Plan
  desc Each quarter steps up on a named assumption
  sequences
    - label Q1 — $3.1M
      desc Baseline renewal book
    - label Q2 — $3.6M
      desc Add usage-based add-ons
    - label Q3 — $4.2M
      desc Partner channel opens
    - label Q4 — $5.0M
      desc Enterprise motion matures
```

## Data Shape

`sequences` in ascending order, four steps. Put the number inside the label so the step height and the value
read together, and keep the assumption in `desc`.

## Key Options

| Option | Effect |
|---|---|
| `infographic sequence-ascending-stairs-3d-simple` | Staircase with depth; reads as growth |
| `sequence-ascending-stairs-3d-underline-text` | Underlined labels; cleaner on light themes |
| `chart-column-simple` | Use when exact quarter-over-quarter comparison is the point |

## Pitfalls

- ❌ Steps without assumptions → ✅ each rise needs a reason or the plan looks like a straight line
- ❌ Numbers in `desc` only → ✅ the staircase should carry the value in the label
- ❌ Five or more quarters → ✅ crowded; group by half-year instead

## Alternatives

| Variant | Use instead |
|---|---|
| Quarterly results achieved | `quarterly-results-columns.md` |
| Conversion through the sales stages | `conversion-funnel-journey.md` |
| Revenue concentration by customer | `revenue-concentration-topk-others.md` (vega-lite) |

<!-- source: AntV Infographic syntax docs + template list (`sequence-ascending-stairs-3d-simple`) -->
