# Waterfall — Bridge from Plan to Actual (Vega-Lite)

**Best for**: explaining how several positive and negative factors move a baseline to an ending total
**Avoid when**: the reader only needs the final ranking or trend, not the step-by-step contribution story
**Answers**: which changes pushed the outcome up or down, and how they accumulate into the final result

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 500,
  "height": 280,
  "data": {
    "values": [
      {"step": "Plan", "amount": 180},
      {"step": "Price", "amount": 24},
      {"step": "Mix", "amount": -18},
      {"step": "Returns", "amount": -12},
      {"step": "Upsell", "amount": 16},
      {"step": "Actual", "amount": 190}
    ]
  },
  "title": {"text": "Plan-to-Actual Bridge", "subtitle": "Positive and negative contributors to the final total", "anchor": "start"},
  "transform": [
    {"window": [{"op": "sum", "field": "amount", "as": "running_total"}], "frame": [null, 0]},
    {"calculate": "datum.running_total - datum.amount", "as": "previous_total"},
    {"calculate": "datum.step === 'Plan' || datum.step === 'Actual' ? 0 : (datum.amount >= 0 ? datum.previous_total : datum.running_total)", "as": "start"},
    {"calculate": "datum.step === 'Plan' ? datum.amount : datum.step === 'Actual' ? datum.amount : (datum.amount >= 0 ? datum.running_total : datum.previous_total)", "as": "end"},
    {"calculate": "datum.step === 'Plan' || datum.step === 'Actual' ? 'total' : datum.amount >= 0 ? 'up' : 'down'", "as": "direction"}
  ],
  "layer": [
    {
      "mark": {"type": "bar", "cornerRadiusEnd": 3},
      "encoding": {
        "x": {"field": "step", "type": "ordinal", "title": null},
        "y": {"field": "start", "type": "quantitative", "title": "Revenue (k$)"},
        "y2": {"field": "end"},
        "color": {
          "field": "direction",
          "type": "nominal",
          "scale": {"domain": ["up", "down", "total"], "range": ["#2b66c4", "#d1242f", "#4b5563"]},
          "legend": null
        }
      }
    },
    {
      "mark": {"type": "text", "dy": -8, "color": "#1f2937"},
      "encoding": {
        "x": {"field": "step", "type": "ordinal"},
        "y": {"field": "end", "type": "quantitative"},
        "text": {"field": "amount", "type": "quantitative", "format": "+,.0f"}
      }
    }
  ]
}
```

## Data Shape

One ordered row per bridge step. The transform computes the running total, then derives the start and end of each bar inside the spec.

## Key Options

| Option | Effect |
|---|---|
| `window` cumulative sum | Builds the running bridge without preprocessing |
| `calculate` for `start` / `end` | Turns one signed measure into bar extents |
| `y` + `y2` | Encodes each waterfall segment as an interval |
| Derived `direction` color | Separates positive, negative, and total bars |

## Pitfalls

- ❌ Using a plain bar chart for bridge logic → ✅ the cumulative structure disappears
- ❌ Forgetting explicit ordering of steps → ✅ waterfalls only make sense when the sequence is semantic
- ❌ Mixing totals and deltas without separate treatment → ✅ starting/ending totals need different interval logic

## Alternatives

| Variant | Use instead |
|---|---|
| Category comparison only | `comparison-bars.md` |
| Trend over time | `trend-line-multi-series.md` |
| Flow through process stages | `funnel-stage-conversion.md` or `sankey-channel-to-fulfilment.md` |

<!-- source: Vega-Lite docs (window / calculate / y2 interval bars) + examples gallery Advanced Calculations waterfall -->