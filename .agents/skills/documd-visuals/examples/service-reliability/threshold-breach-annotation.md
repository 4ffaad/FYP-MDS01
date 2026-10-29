# Threshold Annotation — Trend with Highlighted Breach (Vega-Lite)

**Best for**: a single trend where the reader needs a threshold line and one clearly highlighted breach or event
**Avoid when**: several series compete for attention or the annotation becomes a full narrative on its own
**Answers**: where the metric crosses the boundary, and how the highlighted event relates to the baseline trend

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 470,
  "height": 260,
  "title": {"text": "Latency vs Threshold", "subtitle": "One breach highlighted on the trend", "anchor": "start"},
  "data": {
    "values": [
      {"week": "2026-04-01", "latency": 142},
      {"week": "2026-04-08", "latency": 151},
      {"week": "2026-04-15", "latency": 164},
      {"week": "2026-04-22", "latency": 212},
      {"week": "2026-04-29", "latency": 171}
    ]
  },
  "layer": [
    {
      "mark": {"type": "line", "strokeWidth": 2.5, "color": "#2b66c4"},
      "encoding": {
        "x": {"field": "week", "type": "temporal", "title": null},
        "y": {"field": "latency", "type": "quantitative", "title": "Latency (ms)"}
      }
    },
    {
      "data": {"values": [{"threshold": 180}]},
      "mark": {"type": "rule", "strokeDash": [6, 4], "strokeWidth": 2, "color": "#f3a33c"},
      "encoding": {"y": {"field": "threshold", "type": "quantitative"}}
    },
    {
      "transform": [{"filter": "datum.latency > 180"}],
      "mark": {"type": "point", "filled": true, "size": 120, "color": "#d1242f"},
      "encoding": {
        "x": {"field": "week", "type": "temporal"},
        "y": {"field": "latency", "type": "quantitative"}
      }
    }
  ]
}
```

## Data Shape

One trend series plus a simple derived layer for the threshold and the breached points.

## Key Options

| Option | Effect |
|---|---|
| Layered `line` + `rule` + filtered `point` | Combines trend, benchmark, and exception in one view |
| Filter transform | Restricts the highlight layer to only the values that matter |
| Dashed threshold line | Differentiates the rule from the trend visually |
| Strong exception point | Makes the breach scan instantly in export |

## Pitfalls

- ❌ Annotating every point → ✅ the highlight layer is strongest when reserved for exceptions
- ❌ Using the same color for baseline and threshold → ✅ the rule needs its own visual role
- ❌ No explicit threshold value → ✅ the reader needs to know what the line means |

## Alternatives

| Variant | Use instead |
|---|---|
| Forecast with full uncertainty band | `forecast-range-band.md` |
| Dual-axis benchmark chart | ECharts line/markLine or layered Vega-Lite view |
| One KPI status only | `gauge-sla-attainment.md` |

<!-- source: Vega-Lite docs (layer / rule / filter transform) + examples gallery Labeling & Annotation -->