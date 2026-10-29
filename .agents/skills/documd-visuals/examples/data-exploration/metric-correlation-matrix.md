# Correlation Heatmap — Metric Relationships (Vega-Lite)

**Best for**: showing pairwise relationship strength across several metrics when the reader needs a matrix view, not many separate scatter plots
**Avoid when**: the audience needs raw points or a small set of exact values rather than an overall relationship surface
**Answers**: which metrics move together, which oppose each other, and where the strongest patterns sit

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 360,
  "height": 320,
  "title": {"text": "Correlation Matrix", "subtitle": "Pairwise relationship strength across operating metrics", "anchor": "start"},
  "data": {
    "values": [
      {"x": "Latency", "y": "Latency", "corr": 1.00},
      {"x": "Latency", "y": "Errors", "corr": 0.78},
      {"x": "Latency", "y": "Satisfaction", "corr": -0.64},
      {"x": "Latency", "y": "Queue", "corr": 0.71},
      {"x": "Errors", "y": "Latency", "corr": 0.78},
      {"x": "Errors", "y": "Errors", "corr": 1.00},
      {"x": "Errors", "y": "Satisfaction", "corr": -0.58},
      {"x": "Errors", "y": "Queue", "corr": 0.62},
      {"x": "Satisfaction", "y": "Latency", "corr": -0.64},
      {"x": "Satisfaction", "y": "Errors", "corr": -0.58},
      {"x": "Satisfaction", "y": "Satisfaction", "corr": 1.00},
      {"x": "Satisfaction", "y": "Queue", "corr": -0.47},
      {"x": "Queue", "y": "Latency", "corr": 0.71},
      {"x": "Queue", "y": "Errors", "corr": 0.62},
      {"x": "Queue", "y": "Satisfaction", "corr": -0.47},
      {"x": "Queue", "y": "Queue", "corr": 1.00}
    ]
  },
  "mark": "rect",
  "encoding": {
    "x": {"field": "x", "type": "nominal", "title": null},
    "y": {"field": "y", "type": "nominal", "title": null},
    "color": {"field": "corr", "type": "quantitative", "scale": {"domain": [-1, 1], "scheme": "redblue"}},
    "tooltip": [
      {"field": "x", "type": "nominal", "title": "Metric A"},
      {"field": "y", "type": "nominal", "title": "Metric B"},
      {"field": "corr", "type": "quantitative", "format": ".2f", "title": "Correlation"}
    ]
  }
}
```

## Data Shape

One row per metric pair with a numeric relationship score. Symmetric matrices usually include both directions plus the diagonal.

## Key Options

| Option | Effect |
|---|---|
| `mark: "rect"` | Turns pairwise relationships into a dense matrix |
| Diverging color scale | Makes positive and negative relationships visually distinct |
| Nominal x/y encodings | Keeps the matrix aligned to metric names |
| Tooltip fields | Preserves exact lookup in preview without cluttering the export |

## Pitfalls

- ❌ Reading color-only cells without a scale → ✅ always use a bounded diverging color domain
- ❌ Using a heatmap when the matrix is tiny and exact numbers matter more → ✅ a plain table may be clearer
- ❌ Asymmetric data in a conceptually symmetric matrix → ✅ be explicit if direction changes the value

## Alternatives

| Variant | Use instead |
|---|---|
| Raw point relationships | `segment-pattern-small-multiples.md` |
| Operational intensity over two ordered axes | `heatmap-incident-load.md` |
| Small score grid with explicit values | `matrix-service-scorecards.md` |

<!-- source: Vega-Lite docs (rect mark / heatmap) + examples gallery matrix correlation heatmap -->