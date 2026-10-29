# Error Band — Forecast Range Around a Central Trend (Vega-Lite)

**Best for**: showing a central forecast with uncertainty or variability around it instead of pretending the line is exact
**Avoid when**: you only have one deterministic series or the audience needs raw individual observations instead of intervals
**Answers**: what the expected trend is, and how wide the plausible range becomes over time

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 460,
  "height": 260,
  "data": {
    "values": [
      {"week": "2026-04-01", "mean": 92, "low": 84, "high": 101},
      {"week": "2026-04-08", "mean": 98, "low": 89, "high": 108},
      {"week": "2026-04-15", "mean": 105, "low": 95, "high": 117},
      {"week": "2026-04-22", "mean": 111, "low": 99, "high": 124},
      {"week": "2026-04-29", "mean": 116, "low": 103, "high": 130}
    ]
  },
  "layer": [
    {
      "mark": {"type": "errorband", "opacity": 0.22},
      "encoding": {
        "x": {"field": "week", "type": "temporal", "title": null},
        "y": {"field": "low", "type": "quantitative", "title": "Demand"},
        "y2": {"field": "high"}
      }
    },
    {
      "mark": {"type": "line", "strokeWidth": 2.5},
      "encoding": {
        "x": {"field": "week", "type": "temporal"},
    "title": {"text": "Forecast Range", "subtitle": "Expected demand with explicit low/high bounds", "anchor": "start"},
        "y": {"field": "mean", "type": "quantitative"}
      }
    }
  ]
}
```
      "mark": {"type": "line", "strokeWidth": 2.5, "color": "#7ca6ff"},
## Data Shape

One row per period with a central estimate plus explicit low/high bounds. The band and the line reuse the same dataset in separate layers.

## Key Options

| Option | Effect |
|---|---|
| Layered `errorband` + `line` | Separates the range from the central forecast |
| `y` + `y2` on the band layer | Uses explicit interval bounds rather than inferred aggregate uncertainty |
| Temporal x encoding | Keeps the interval aligned to ordered time periods |
| Low-opacity band | Preserves the line as the primary reading target |

## Pitfalls

- ❌ Showing one clean line for uncertain forecasts → ✅ the band is the point of the chart
- ❌ Using a fully opaque band → ✅ it will bury the mean line and labels
- ❌ Mixing unrelated confidence assumptions → ✅ define clearly what the interval means before encoding it

## Alternatives

| Variant | Use instead |
|---|---|
| One deterministic trend | `trend-line-multi-series.md` |
| Distribution by category | `boxplot-latency-distribution.md` |
| Mean with discrete error bars only | A Vega-Lite `errorbar` view |

<!-- source: Vega-Lite docs (errorband composite mark / layered views) + examples gallery Error Bars & Error Bands -->