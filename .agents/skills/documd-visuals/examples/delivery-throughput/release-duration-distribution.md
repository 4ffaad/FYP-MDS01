# Boxplot — Release Duration Distribution (Vega-Lite)

**Best for**: comparing distribution shape across categories when median, spread, and outliers matter more than simple averages
**Avoid when**: the audience only needs one aggregate number per category or the sample size is tiny
**Answers**: how variable each group is, where the median sits, and whether one group has more extreme values

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 440,
  "height": 260,
  "title": {"text": "Release Duration Distribution", "subtitle": "Cycle time in hours by team", "anchor": "start"},
  "data": {
    "values": [
      {"team": "Core", "hours": 18}, {"team": "Core", "hours": 22}, {"team": "Core", "hours": 24}, {"team": "Core", "hours": 29}, {"team": "Core", "hours": 31},
      {"team": "Billing", "hours": 20}, {"team": "Billing", "hours": 27}, {"team": "Billing", "hours": 34}, {"team": "Billing", "hours": 38}, {"team": "Billing", "hours": 41},
      {"team": "Identity", "hours": 12}, {"team": "Identity", "hours": 15}, {"team": "Identity", "hours": 16}, {"team": "Identity", "hours": 19}, {"team": "Identity", "hours": 23}
    ]
  },
  "mark": {"type": "boxplot", "extent": 1.5, "size": 28},
  "encoding": {
    "x": {"field": "team", "type": "nominal", "title": null},
    "y": {"field": "hours", "type": "quantitative", "title": "Hours"},
    "color": {"field": "team", "type": "nominal", "legend": null}
  }
}
```

## Data Shape

One row per observation. Vega-Lite computes the boxplot statistics directly from raw values grouped by category.

## Key Options

| Option | Effect |
|---|---|
| `mark: {"type": "boxplot"}` | Expands raw numeric rows into median, quartiles, whiskers, and outliers |
| `extent: 1.5` | Uses Tukey-style whisker distance for outlier detection |
| Category on `x` | Computes one distribution summary per group |
| Raw values input | Keeps the spec transparent and easy to change |

## Pitfalls

- ❌ Feeding pre-aggregated averages into a boxplot → ✅ it needs raw or precomputed distribution statistics, not means
- ❌ Using boxplots for very tiny samples → ✅ with too few points the distribution summary becomes misleading
- ❌ Comparing categories with different units → ✅ every group must share the same measure semantics

## Alternatives

| Variant | Use instead |
|---|---|
| One mean plus uncertainty | `forecast-range-band.md` or an `errorbar` spec |
| Exact values by category | `comparison-bars.md` |
| Single-number KPI | `metric-snapshot-board.md` or `gauge-sla-attainment.md` |

<!-- source: Vega-Lite docs (boxplot composite mark) + examples gallery Box Plots -->