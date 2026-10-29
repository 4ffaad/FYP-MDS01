# Connected Scatter — Throughput Against Cycle Time (Vega-Lite)

**Best for**: two measures that are read **together**, where the sequence of positions is the story
**Avoid when**: the two measures are independent, or the reader only needs the latest position
**Answers**: whether the team is moving toward the good corner, week after week

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 420,
  "height": 300,
  "padding": {"right": 30},
  "title": {"text": "Throughput Against Cycle Time", "subtitle": "Eight weeks, connected in order — up and to the left is better", "anchor": "start"},
  "data": {
    "values": [
      {"week": "W1", "throughput": 18, "cycle": 9.4},
      {"week": "W2", "throughput": 21, "cycle": 8.9},
      {"week": "W3", "throughput": 20, "cycle": 8.1},
      {"week": "W4", "throughput": 26, "cycle": 7.6},
      {"week": "W5", "throughput": 29, "cycle": 6.8},
      {"week": "W6", "throughput": 27, "cycle": 6.4},
      {"week": "W7", "throughput": 34, "cycle": 5.9},
      {"week": "W8", "throughput": 38, "cycle": 5.2}
    ]
  },
  "layer": [
    {
      "mark": {"type": "line", "color": "#2b66c4", "strokeWidth": 2, "opacity": 0.9},
      "encoding": {
        "x": {"field": "throughput", "type": "quantitative", "title": "merged PRs per week", "scale": {"zero": false}},
        "y": {"field": "cycle", "type": "quantitative", "title": "mean cycle time (days)", "scale": {"zero": false, "reverse": true}},
        "order": {"field": "week", "type": "ordinal"}
      }
    },
    {
      "mark": {"type": "point", "filled": true, "size": 95, "color": "#0f9b9b"},
      "encoding": {
        "x": {"field": "throughput", "type": "quantitative"},
        "y": {"field": "cycle", "type": "quantitative"}
      }
    },
    {
      "mark": {"type": "text", "dx": 9, "dy": -8, "fontSize": 10},
      "encoding": {
        "x": {"field": "throughput", "type": "quantitative"},
        "y": {"field": "cycle", "type": "quantitative"},
        "text": {"field": "week", "type": "nominal"}
      }
    }
  ]
}
```

## Data Shape

One row per time step with two quantitative measures plus an **order field**. The order is what makes this a
connected scatter rather than a scatterplot with a line drawn through the points.

| Field | Role |
|---|---|
| `throughput` | x — the measure you want to grow |
| `cycle` | y — inverted, so "better" is up |
| `week` | `order` on the line layer and the point labels |

## Key Options

| Option | Effect |
|---|---|
| `scale.reverse: true` on y | Flips the axis so the good corner is the top right, matching the subtitle |
| `scale.zero: false` on both axes | Connected scatters read as movement in a space, not as proportions — but then the axis ranges must be stated |
| `order` encoding | Draws the path in time order instead of in data order |
| Layer 3 vs 1 | Layering keeps the same field on the same scale; three separate charts would lose the shared space |
| `padding.right` | Room for the final label so it is not clipped |
| `dx`/`dy` on the labels | Diagonal nudge, the usual fix for labels sitting on their own marker |

## Pitfalls

- ❌ Treating it as a correlation chart → ✅ a connected scatter shows a *trajectory*; if you do not care about the order, use a plain scatterplot
- ❌ A path that revisits points → ✅ the line then doubles back on itself; say so in the subtitle or the reader assumes a measurement error
- ❌ Both axes truncated to a narrow band → ✅ a small window magnifies noise; either widen the domain or annotate the range
- ❌ Omitting `order` → ✅ the line follows row order, which usually is not time order once the data comes from a query

## Alternatives

| Variant | Use instead |
|---|---|
| A single measure over time | `trend-line-multi-series.md` (ECharts) |
| Two periods only | `adoption-shift-slope.md` |
| Correlation without a sequence | `metric-correlation-matrix.md` |

<!-- source: Vega-Lite docs (connected scatterplots entry in the scatter gallery section; order channel; scale.reverse) -->
