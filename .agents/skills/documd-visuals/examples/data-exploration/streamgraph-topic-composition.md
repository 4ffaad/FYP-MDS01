# Streamgraph — Topic Composition Over Time (Vega-Lite)

**Best for**: showing changing composition over time when the flow and relative shape matter more than precise stacked baselines
**Avoid when**: the reader needs exact per-series values or the category count is high enough to create ribbon noise
**Answers**: which topics dominate at different times, and how their share ebbs and flows collectively

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 500,
  "height": 260,
  "title": {"text": "Topic Composition Over Time", "subtitle": "Stacked around a centered baseline to emphasize change", "anchor": "start"},
  "data": {"values": [
    {"month": "2026-01-01", "topic": "Platform", "value": 28},
    {"month": "2026-01-01", "topic": "Security", "value": 12},
    {"month": "2026-01-01", "topic": "Data", "value": 9},
    {"month": "2026-02-01", "topic": "Platform", "value": 31},
    {"month": "2026-02-01", "topic": "Security", "value": 14},
    {"month": "2026-02-01", "topic": "Data", "value": 11},
    {"month": "2026-03-01", "topic": "Platform", "value": 24},
    {"month": "2026-03-01", "topic": "Security", "value": 18},
    {"month": "2026-03-01", "topic": "Data", "value": 13},
    {"month": "2026-04-01", "topic": "Platform", "value": 20},
    {"month": "2026-04-01", "topic": "Security", "value": 22},
    {"month": "2026-04-01", "topic": "Data", "value": 15}
  ]},
  "mark": "area",
  "encoding": {
    "x": {"field": "month", "type": "temporal", "title": null},
    "y": {"field": "value", "type": "quantitative", "stack": "center", "title": "Volume"},
    "color": {"field": "topic", "type": "nominal"}
  }
}
```

## Data Shape

One row per time/category pair with a numeric value. Centered stacking turns a plain stacked area into a streamgraph.

## Key Options

| Option | Effect |
|---|---|
| `mark: "area"` | Creates continuous composition bands over time |
| `stack: "center"` | Produces the streamgraph baseline rather than a zero-based stack |
| Temporal x encoding | Keeps the composition aligned to an ordered sequence |
| Category color | Separates the thematic bands visually |

## Pitfalls

- ❌ Using streamgraphs for exact value lookup → ✅ the point is flow and changing composition, not precise reading
- ❌ Too many categories → ✅ the centered layers become hard to track quickly
- ❌ Using a centered baseline when absolute totals must be compared directly → ✅ keep a regular stacked area in that case

## Alternatives

| Variant | Use instead |
|---|---|
| Exact multi-series trend lines | `trend-line-multi-series.md` |
| ThemeRiver presentation chart | `themeriver-topic-attention.md` |
| Percent-only composition | `quarterly-share-normalized-stack.md` |

<!-- source: Vega-Lite docs (area / stack center) + examples gallery Area & Streamgraphs -->