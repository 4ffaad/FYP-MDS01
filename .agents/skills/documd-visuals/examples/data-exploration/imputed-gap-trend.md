# Imputed Gap Trend — Missing Points Made Explicit (Vega-Lite)

**Best for**: trends with occasional missing periods where the reader must see both the line and the fact that a value was absent
**Avoid when**: there is no meaningful time sequence or the missingness itself is the whole story
**Answers**: how the trend moves overall, and where the series had to be imputed or carried across a gap

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 470,
  "height": 260,
  "title": {"text": "Imputed Gap Trend", "subtitle": "Missing week filled to preserve continuity in the view", "anchor": "start"},
  "data": {"values": [
    {"week": "2026-04-01", "value": 91},
    {"week": "2026-04-08", "value": 95},
    {"week": "2026-04-22", "value": 104},
    {"week": "2026-04-29", "value": 109}
  ]},
  "transform": [
    {"impute": "value", "key": "week", "keyvals": ["2026-04-01", "2026-04-08", "2026-04-15", "2026-04-22", "2026-04-29"], "method": "value", "value": 99},
    {"calculate": "datum.week === '2026-04-15' ? 'Imputed' : 'Observed'", "as": "status"}
  ],
  "layer": [
    {
      "mark": {"type": "line", "strokeWidth": 2.5, "color": "#2b66c4"},
      "encoding": {
        "x": {"field": "week", "type": "temporal", "title": null},
        "y": {"field": "value", "type": "quantitative", "title": "Value"}
      }
    },
    {
      "mark": {"type": "point", "filled": true, "size": 95},
      "encoding": {
        "x": {"field": "week", "type": "temporal"},
        "y": {"field": "value", "type": "quantitative"},
        "color": {"field": "status", "type": "nominal", "scale": {"domain": ["Observed", "Imputed"], "range": ["#0f9b9b", "#f3a33c"]}}
      }
    }
  ]
}
```

## Data Shape

One row per known time point. The transform inserts the missing key value and tags it so the imputed point is visible.

## Key Options

| Option | Effect |
|---|---|
| `impute` | Creates an explicit row for a missing period |
| `keyvals` | Declares the complete ordered set of periods that should exist |
| Point layer with status color | Distinguishes observed and imputed values in export |
| Shared line + points | Preserves the trend while still exposing the gap treatment |

## Pitfalls

- ❌ Hiding imputation in a seamless line → ✅ if the point is imputed, make it visible to the reader
- ❌ Using arbitrary fill values without explanation → ✅ the method and purpose of the fill must be defensible
- ❌ Imputing when the missingness should remain a break → ✅ sometimes the absence is itself the message |

## Alternatives

| Variant | Use instead |
|---|---|
| Explicit broken line at missing values | Use `mark.invalid` handling instead of impute |
| Forecast range view | `forecast-range-band.md` |
| Threshold breach annotation | `threshold-breach-annotation.md` |

<!-- source: Vega-Lite docs (impute transform / layered trend views) + examples gallery Advanced Calculations impute -->