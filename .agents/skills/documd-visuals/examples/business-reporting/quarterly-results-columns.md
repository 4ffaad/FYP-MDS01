# Column Chart — Quarterly Results Snapshot (Infographic)

**Best for**: a lightweight vertical comparison with only a few periods or categories and a strong template-first visual treatment
**Avoid when**: the chart needs dense axis control, multiple analytical series, or statistical transforms
**Answers**: how a few periods compare, and which bar is highest or lowest

```infographic
infographic chart-column-simple
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
  title Quarterly Results
  desc Revenue by quarter for the current fiscal year
  values
    - label Q1
      value 28
    - label Q2
      value 34
    - label Q3
      value 31
    - label Q4
      value 39
```

## Data Shape

Use `values` with one numeric `value` per bar and a short `label` for each category or period.

## Key Options

| Option | Effect |
|---|---|
| `chart-column-simple` | Lightweight vertical bar/column treatment |
| `values` | Numeric series input for infographic chart templates |
| Short labels | Keeps the axis-free chart readable in one glance |

## Pitfalls

- ❌ Expecting full analytical chart semantics → ✅ infographic charts are for presentation-first views, not deep analysis
- ❌ Too many categories → ✅ once labels crowd, move to echarts or vega-lite
- ❌ Multiple unrelated series in one simple template → ✅ keep infographic chart examples structurally simple

## Alternatives

| Variant | Use instead |
|---|---|
| Analytical bar chart with axes and sorting | `comparison-bars.md` or Vega-Lite bar views |
| Part-to-whole split | `budget-allocation-donut.md` |
| Metric board instead of a chart | `leadership-metric-board.md` |

<!-- source: AntV Infographic template reference (`chart-column-simple`) + syntax docs for values -->