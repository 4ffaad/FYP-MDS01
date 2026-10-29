# Donut Share — Budget Allocation (Infographic)

**Best for**: a quick part-to-whole picture with very few categories and a strong visual style requirement
**Avoid when**: the reader needs axes, many slices, or exact ranked comparison (use echarts or vega-lite)
**Answers**: how the budget splits across a few major buckets

```infographic
infographic chart-pie-donut-plain-text
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
  title Budget Allocation
  desc FY2026 operating budget split across the main workstreams
  values
    - label Platform
      value 36
    - label Customer Ops
      value 24
    - label Security
      value 18
    - label Data
      value 12
    - label Enablement
      value 10
```

## Data Shape

Use `values` with one numeric `value` per slice. Keep the slice count small enough that the part-to-whole message still reads quickly.

## Key Options

| Option | Effect |
|---|---|
| `chart-pie-donut-plain-text` | Donut-style part-to-whole layout |
| `values` | Numeric measure list for chart templates |
| Plain text labels | Keeps the result compact and board-friendly |

## Pitfalls

- ❌ Ten tiny slices → ✅ donut views are for a few categories only
- ❌ Using infographic charts for analytical comparison → ✅ switch to `echarts` or `vega-lite` when the axes and transforms matter
- ❌ Hiding the category labels → ✅ a decorative donut without labels is not useful in static export

## Alternatives

| Variant | Use instead |
|---|---|
| Analytical pie/donut with finer control | `pie-budget-share.md` |
| KPI board with multiple headline metrics | `leadership-metric-board.md` |
| Side-by-side choice framing | `market-entry-swot.md` |

<!-- source: AntV Infographic syntax docs (`values`) + template list (`chart-pie-donut-plain-text`) -->