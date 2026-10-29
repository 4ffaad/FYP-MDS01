# Dumbbell — Latency Before and After a Fix (Vega-Lite)

**Best for**: two measurements per category, where the *gap* between them is the argument
**Avoid when**: the two values are not comparable, or exact readings per endpoint are the point
**Answers**: how much each endpoint improved, and which one still lags

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 430,
  "height": 250,
  "padding": {"right": 78},
  "title": {"text": "p95 Latency Before and After the Cache Fix", "subtitle": "Milliseconds, worst endpoint on top", "anchor": "start"},
  "data": {
    "values": [
      {"endpoint": "Checkout", "before": 412, "after": 268},
      {"endpoint": "Cart", "before": 366, "after": 210},
      {"endpoint": "Search", "before": 298, "after": 224},
      {"endpoint": "Catalog", "before": 244, "after": 132},
      {"endpoint": "Profile", "before": 188, "after": 96}
    ]
  },
  "transform": [
    {"calculate": "'−' + (datum.before - datum.after) + ' ms'", "as": "deltaLabel"}
  ],
  "layer": [
    {
      "mark": {"type": "rule", "strokeWidth": 2.5, "color": "#2b66c4"},
      "encoding": {
        "y": {"field": "endpoint", "type": "ordinal", "title": null},
        "x": {"field": "before", "type": "quantitative", "title": "p95 (ms)", "scale": {"zero": true}},
        "x2": {"field": "after"}
      }
    },
    {
      "mark": {"type": "point", "filled": true, "size": 95, "color": "#d1242f"},
      "encoding": {
        "y": {"field": "endpoint", "type": "ordinal"},
        "x": {"field": "before", "type": "quantitative"}
      }
    },
    {
      "mark": {"type": "point", "filled": true, "size": 95, "color": "#0f9b9b"},
      "encoding": {
        "y": {"field": "endpoint", "type": "ordinal"},
        "x": {"field": "after", "type": "quantitative"}
      }
    },
    {
      "mark": {"type": "text", "align": "left", "dx": 10, "fontSize": 11},
      "encoding": {
        "y": {"field": "endpoint", "type": "ordinal"},
        "x": {"field": "before", "type": "quantitative"},
        "text": {"field": "deltaLabel", "type": "nominal"}
      }
    }
  ]
}
```

## Data Shape

Two numeric columns per category. The category order carries meaning — worst first — and is taken from the
row order in `values`, because automatic sorting is disabled.

## Key Options

| Option | Effect |
|---|---|
| `x` + `x2` on a `rule` | Draws the connector: the visual "bar" of the dumbbell |
| Separate `point` layers | One hue per period, so "before" and "after" are distinguishable without a legend |
| `padding.right` | Reserves room for the delta labels; without it they are clipped |
| `calculate` producing a label string | Formats the gap at build time, so the label never drifts from the data |
| `size: 95` on both point layers | Matched marker area — unequal sizes would imply a third encoding |
| `scale.zero: true` | Latency is a rate-like measure; starting the axis at zero stops the gap from being exaggerated |

## Pitfalls

- ❌ A dumbbell without a stated direction → ✅ say "before / after" or "this quarter / last quarter" in the subtitle and keep one hue per period
- ❌ Different markers for the two ends → ✅ the reader decodes colour, not shape; mixed shapes imply unrelated quantities
- ❌ Sorting the categories by name → ✅ order by the gap or by the worse endpoint so the chart has a direction
- ❌ Dropping the connector → ✅ two dots without a rule is a scatterplot; the gap is the message

## Alternatives

| Variant | Use instead |
|---|---|
| Ranks rather than values | `rank-movement-over-time.md` |
| A change that accumulates to a total | `plan-to-actual-bridge.md` |
| Two distributions rather than two points | `service-latency-density.md` |

<!-- source: Vega-Lite docs (rule mark with x2, layered point marks, text mark, padding) + the ranged-dot / dumbbell entries in the layered gallery section -->
