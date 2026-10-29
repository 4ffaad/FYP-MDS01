# Error Bar — Team Variance Around Mean (Vega-Lite)

**Best for**: showing a central estimate and its spread when the reader cares about uncertainty but not the full boxplot shape
**Avoid when**: you need the full distribution or every raw point matters on the page
**Answers**: what the mean is, and how wide the variability around it appears for each category

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 430,
  "height": 260,
  "title": {"text": "Team Variance Around Mean", "subtitle": "Average review time with standard-deviation bars", "anchor": "start"},
  "data": {
    "values": [
      {"team": "Core", "hours": 18}, {"team": "Core", "hours": 21}, {"team": "Core", "hours": 24},
      {"team": "Billing", "hours": 23}, {"team": "Billing", "hours": 30}, {"team": "Billing", "hours": 36},
      {"team": "Identity", "hours": 14}, {"team": "Identity", "hours": 16}, {"team": "Identity", "hours": 19}
    ]
  },
  "layer": [
    {
      "mark": {"type": "errorbar", "ticks": true},
      "encoding": {
        "x": {"field": "team", "type": "nominal", "title": null},
        "y": {"field": "hours", "type": "quantitative", "title": "Hours"}
      }
    },
    {
      "mark": {"type": "point", "filled": true, "size": 95, "color": "#2b66c4"},
      "encoding": {
        "x": {"field": "team", "type": "nominal"},
        "y": {"aggregate": "mean", "field": "hours", "type": "quantitative"}
      }
    }
  ]
}
```

## Data Shape

One row per observation. Vega-Lite derives the error bar from the grouped raw values while a second layer marks the mean explicitly.

## Key Options

| Option | Effect |
|---|---|
| `errorbar` | Encodes variability around a central estimate compactly |
| `ticks: true` | Adds visible caps so the interval is easier to read in export |
| Mean point layer | Makes the center of the interval explicit |
| Shared raw data | Keeps the interval and the mean consistent |

## Pitfalls

- ❌ Reading error bars as full distribution shape → ✅ they summarize spread, not quartiles and outliers
- ❌ Omitting the center estimate → ✅ the reader still needs the anchor value, not just the interval |
- ❌ Comparing bars built from incompatible assumptions → ✅ be clear whether the spread is stdev, stderr, or CI |

## Alternatives

| Variant | Use instead |
|---|---|
| Full distribution comparison | `release-duration-distribution.md` |
| Time-series interval | `forecast-range-band.md` |
| Exact category comparison | `comparison-bars.md` |

<!-- source: Vega-Lite docs (errorbar composite mark) + examples gallery Error Bars & Error Bands -->