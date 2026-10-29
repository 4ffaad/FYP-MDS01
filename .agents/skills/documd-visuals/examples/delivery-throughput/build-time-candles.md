# Candlesticks — Build Duration Spread Per Week (Vega-Lite)

**Best for**: a range plus an inner range — a body between two quartiles and whiskers to the extremes
**Avoid when**: a single summary statistic per period would do, or the audience is not used to the form
**Answers**: how variable each week's build times were, and which week had the heavy tail

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 480,
  "height": 260,
  "title": {"text": "Build Duration Spread", "subtitle": "Whiskers: 5th–95th percentile · body: 25th–75th percentile", "anchor": "start"},
  "data": {
    "values": [
      {"week": "W1", "low": 6.2, "p25": 7.4, "p75": 9.1, "high": 12.4},
      {"week": "W2", "low": 6.4, "p25": 7.2, "p75": 8.6, "high": 10.1},
      {"week": "W3", "low": 7.1, "p25": 8.3, "p75": 11.2, "high": 16.8},
      {"week": "W4", "low": 6.9, "p25": 7.5, "p75": 8.4, "high": 9.6},
      {"week": "W5", "low": 6.1, "p25": 6.8, "p75": 7.6, "high": 8.9},
      {"week": "W6", "low": 5.9, "p25": 6.4, "p75": 7.1, "high": 8.2}
    ]
  },
  "layer": [
    {
      "mark": {"type": "rule", "color": "#2b66c4", "strokeWidth": 1.5},
      "encoding": {
        "x": {"field": "week", "type": "ordinal", "title": null},
        "y": {"field": "low", "type": "quantitative", "title": "build minutes", "scale": {"zero": false}},
        "y2": {"field": "high"}
      }
    },
    {
      "mark": {"type": "bar", "size": 18, "cornerRadius": 2, "color": "#0f9b9b", "opacity": 0.9},
      "encoding": {
        "x": {"field": "week", "type": "ordinal", "title": null},
        "y": {"field": "p25", "type": "quantitative"},
        "y2": {"field": "p75"}
      }
    }
  ]
}
```

## Data Shape

Four numbers per period, ordered `low ≤ p25 ≤ p75 ≤ high`. The whisker layer uses `low`/`high`, the body
layer uses `p25`/`p75` — one row, two overlapping marks.

| Layer | Fields | Meaning |
|---|---|---|
| Rule | `low` → `high` | The full observed spread |
| Bar | `p25` → `p75` | The middle half — the "body" |

## Key Options

| Option | Effect |
|---|---|
| `y` + `y2` on both layers | Two positional endpoints; `x2`/`y2` are what make a range mark |
| `mark.size: 18` on the bar | Fixes the body width so it never grows into a slab |
| `cornerRadius: 2` | A small rounding keeps the body from looking like a plain column |
| `scale.zero: false` | Candles read the range, not the magnitude — but state the axis range in the copy |
| Body colour distinct from whisker | The two layers must be tellable apart at a glance |

## Pitfalls

- ❌ Using candles for a single value per period → ✅ that is a bar chart; the form earns its keep only when a spread exists
- ❌ Whiskers that are not symmetric assumptions → ✅ say what the whiskers are (5th–95th here), because the standard Tukey reading is different
- ❌ A body wider than the whisker gap → ✅ the body must sit strictly inside the whiskers; otherwise the summary contradicts the range
- ❌ Overlapping bodies → ✅ reduce the bar width or drop to one candle per two periods

## Alternatives

| Variant | Use instead |
|---|---|
| Full distribution per period | `release-duration-distribution.md` (box plot) |
| A single line with an envelope | `forecast-range-band.md` |
| A continuous price-like series | `candlestick-quarterly-price-range.md` (ECharts) |

<!-- source: Vega-Lite docs (rule and bar marks with y2, layered plots, scale.zero) + the candlestick entry in the layered gallery section -->
