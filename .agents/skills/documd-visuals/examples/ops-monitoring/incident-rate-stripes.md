# Stripes — Incident Rate Anomaly Band (Vega-Lite)

**Best for**: a compact, wordless time band whose only job is to show when things were above or below normal
**Avoid when**: a precise value must be read at a specific time — stripes are a shape, not a table
**Answers**: which months ran hot, which ran cold, and whether the year is trending one way

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 540,
  "height": 84,
  "title": {"text": "Incident Rate Anomalies", "subtitle": "Month by month, deviation from the 3-year mean (red = more incidents than normal)", "anchor": "start"},
  "data": {
    "values": [
      {"m": 1, "anomaly": -1.8}, {"m": 2, "anomaly": -0.6}, {"m": 3, "anomaly": 0.4},
      {"m": 4, "anomaly": 1.9}, {"m": 5, "anomaly": 2.6}, {"m": 6, "anomaly": 0.8},
      {"m": 7, "anomaly": -1.2}, {"m": 8, "anomaly": -2.4}, {"m": 9, "anomaly": -0.3},
      {"m": 10, "anomaly": 1.1}, {"m": 11, "anomaly": 3.4}, {"m": 12, "anomaly": 4.1}
    ]
  },
  "mark": {"type": "rect", "stroke": null},
  "encoding": {
    "x": {"field": "m", "type": "ordinal", "title": null, "axis": null},
    "color": {
      "field": "anomaly",
      "type": "quantitative",
      "scale": {"scheme": "redblue", "reverse": true, "domain": [-4.5, 4.5]},
      "legend": null
    }
  }
}
```

## Data Shape

One row per time step with a single **anomaly** value (deviation from a baseline). No axis, no legend, no
labels — the whole payload is the striped band.

| Field | Role |
|---|---|
| `m` | Ordinal x; the sequence is the time axis |
| `anomaly` | Colour only, on a domain that is symmetric about zero |

## Key Options

| Option | Effect |
|---|---|
| `x.axis: null` | Removes the axis entirely; the band is meant to be read as a shape |
| `color.legend: null` | The concept is explained in the subtitle, not in a legend |
| Symmetric `domain: [-4.5, 4.5]` | Puts the neutral colour exactly at "as expected" |
| `reverse: true` | Warm stripes for abnormal-high, cool for abnormal-low |
| `height: 84` | A thin band: tall stripes start looking like a bar chart with missing axes |
| `mark.stroke: null` | Cells must touch; gaps break the band into unrelated chips |

## Pitfalls

- ❌ Stripes with an axis and a legend → ✅ it becomes a very small column chart; the form only works in its stripped-down state
- ❌ A truncated or one-sided colour domain → ✅ the neutral colour then no longer means "normal", which is the entire reading
- ❌ Too few steps (< ~12) → ✅ the band needs enough columns to form a texture; otherwise draw bars
- ❌ Using it as a chart the reader can quote numbers from → ✅ pair it with a table or label the years you will cite

## Alternatives

| Variant | Use instead |
|---|---|
| The same data with values readable | `deviation-from-average.md` |
| Month × day detail | `deploy-frequency-calendar.md` |
| A trend with an uncertainty envelope | `forecast-range-band.md` |

<!-- source: Vega-Lite docs (rect marks with a single positional channel spanning the view, quantitative colour scales) + the warming-stripes custom-design example in the Vega gallery -->
