# Faceted Scatter — Segment Patterns Without Overplotting (Vega-Lite)

**Best for**: comparing the same x/y relationship across segments while keeping each segment visually separate
**Avoid when**: all points can live comfortably in one plot, or the segments need shared trend overlays instead of separate panes
**Answers**: whether each segment follows the same pattern, and which segment behaves differently

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "data": {
    "values": [
      {"segment": "SMB", "risk": 2.1, "value": 3.8},
      {"segment": "SMB", "risk": 3.0, "value": 4.6},
      {"segment": "SMB", "risk": 4.2, "value": 5.7},
      {"segment": "Mid", "risk": 2.8, "value": 5.2},
      {"segment": "Mid", "risk": 4.4, "value": 6.3},
      {"segment": "Mid", "risk": 5.3, "value": 7.1},
      {"segment": "Enterprise", "risk": 3.6, "value": 6.2},
      {"segment": "Enterprise", "risk": 5.0, "value": 7.8},
      {"segment": "Enterprise", "risk": 6.4, "value": 8.6}
    ]
  },
  "title": {"text": "Segment Patterns", "subtitle": "Risk versus value by customer segment", "anchor": "start"},
  "facet": {"field": "segment", "type": "nominal", "columns": 3, "title": null},
  "spec": {
    "width": 180,
    "height": 180,
    "mark": {"type": "point", "filled": true, "size": 85},
    "encoding": {
      "x": {"field": "risk", "type": "quantitative", "scale": {"domain": [0, 7]}, "title": "Risk"},
      "y": {"field": "value", "type": "quantitative", "scale": {"domain": [0, 10]}, "title": "Value"},
      "color": {"field": "segment", "type": "nominal", "legend": null}
    }
  }
}
```

## Data Shape

One row per observation, plus a facet field that splits the shared scatter structure into separate panels.

## Key Options

| Option | Effect |
|---|---|
| `facet` | Splits the view into comparable small multiples |
| Shared scale domains | Keeps comparison across panels honest |
| `columns` | Controls how the trellis wraps across the page |
| Fixed `width` / `height` per facet | Keeps export layout stable |

## Pitfalls

- ❌ Auto-scaling each facet independently → ✅ similar patterns can look misleadingly different
- ❌ Overlaying segments with too much overplotting → ✅ faceting is the point when separation improves reading
- ❌ Too many facets in one export → ✅ trellis views need enough area per panel to justify themselves

## Alternatives

| Variant | Use instead |
|---|---|
| One combined relationship plot | `scatter-segment-correlation.md` |
| Small distribution panes | A faceted histogram or strip-plot spec |
| Category score grid | `matrix-service-scorecards.md` |

<!-- source: Vega-Lite docs (facet / trellis views) + examples gallery Faceting / Small Multiples -->