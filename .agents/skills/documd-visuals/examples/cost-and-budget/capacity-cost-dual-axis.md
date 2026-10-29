# Dual Axis — Capacity and Cost Together (Vega-Lite)

**Best for**: placing two measures with different units on one shared time axis when the reader needs relationship context but understands the units are separate
**Avoid when**: the chart is used to imply causality or exaggerate a correlation, or when a single measure chart would be clearer
**Answers**: how the two measures moved over the same periods, and whether the peaks line up temporally

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 500,
  "height": 260,
  "title": {"text": "Capacity and Cost", "subtitle": "Shared timeline, independent scales", "anchor": "start"},
  "data": {"values": [
    {"month": "2026-01-01", "capacity": 68, "cost": 4.2},
    {"month": "2026-02-01", "capacity": 72, "cost": 4.5},
    {"month": "2026-03-01", "capacity": 81, "cost": 5.0},
    {"month": "2026-04-01", "capacity": 76, "cost": 4.8}
  ]},
  "encoding": {"x": {"field": "month", "type": "temporal", "title": null}},
  "layer": [
    {"mark": "bar", "encoding": {"y": {"field": "capacity", "type": "quantitative", "title": "Capacity (%)"}, "color": {"value": "#2b66c4"}}},
    {"mark": {"type": "line", "strokeWidth": 2.5, "color": "#f3a33c"}, "encoding": {"y": {"field": "cost", "type": "quantitative", "axis": {"orient": "right", "title": "Cost ($M)"}}}}
  ],
  "resolve": {"scale": {"y": "independent"}}
}
```

## Data Shape

One row per period with two measures that share time but not units.

## Key Options

| Option | Effect |
|---|---|
| Layered bar + line | Makes the two unit types visually distinct |
| Independent y scales | Avoids forcing incompatible measures onto one numeric axis |
| Right-side secondary axis | Keeps the second measure explicitly separated |
| Shared temporal x axis | Preserves alignment across periods |

## Pitfalls

- ❌ Using dual axes to imply a stronger relationship than the data justifies → ✅ always make the separate units explicit
- ❌ Similar colors or identical marks for both measures → ✅ visual separation is necessary for comprehension
- ❌ Forgetting `resolve.scale.y = "independent"` → ✅ the second measure will be misleadingly flattened or stretched

## Alternatives

| Variant | Use instead |
|---|---|
| One measure plus threshold | `threshold-breach-annotation.md` |
| One metric only | `trend-line-multi-series.md` or a single-series line chart |
| KPI and chart split | `metric-snapshot-board.md` |

<!-- source: Vega-Lite docs (layer / resolve independent scales) + examples gallery dual-axis layered plots -->