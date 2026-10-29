# Radar — Capability Profile Across Shared Dimensions (ECharts)

**Best for**: comparing a few entities across the same set of scored dimensions when the overall shape matters
**Avoid when**: exact values matter more than the profile shape, or there are many entities or many dimensions (use bars)
**Answers**: where one option is stronger or weaker, and whether its profile is balanced or skewed

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 820,
  "height": 420,
  "title": { "text": "Capability Profile", "subtext": "Current platform vs target operating model", "left": "left" },
  "legend": { "data": ["Current", "Target"], "top": 8, "right": 8 },
  "radar": {
    "center": ["50%", "58%"],
    "radius": "62%",
    "splitNumber": 5,
    "axisName": { "color": "#4b5563" },
    "indicator": [
      { "name": "Resilience", "max": 10 },
      { "name": "Automation", "max": 10 },
      { "name": "Observability", "max": 10 },
      { "name": "Security", "max": 10 },
      { "name": "Scalability", "max": 10 },
      { "name": "Operability", "max": 10 }
    ]
  },
  "series": [
    {
      "type": "radar",
      "symbol": "circle",
      "symbolSize": 6,
      "lineStyle": { "width": 2 },
      "areaStyle": { "opacity": 0.16 },
      "data": [
        { "value": [6, 5, 7, 6, 5, 6], "name": "Current" },
        { "value": [8, 9, 8, 9, 8, 8], "name": "Target" }
      ]
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `radar.indicator` | Declares the shared dimensions and their maxima; without this the chart has no semantic scale |
| `splitNumber` | Controls how many rings the reader gets for rough estimation |
| `center` / `radius` | Radar charts need explicit sizing or the labels get cramped around the frame |
| `areaStyle.opacity` | Keeps the profile fill visible without obscuring the overlapping shape |
| `symbolSize` + `lineStyle.width` | Makes the vertices legible in export without overwhelming the polygon |

## Data Shape

One `indicator` array describing the shared dimensions, then one `data[{ value, name }]` entry per compared entity. Every `value` array must match the indicator order exactly.

## Pitfalls

- ❌ Mixing dimensions with different scales silently → ✅ radar charts only work when all axes are meaningfully comparable
- ❌ More than two or three entities → ✅ overlapping polygons become unreadable; switch to grouped bars
- ❌ Too many dimensions → ✅ six is already near the readability limit for a static export
- ❌ Using a radar for ranking → ✅ shape is the story here; if the reader needs exact comparison by dimension, use bars

## Alternatives

| Variant | Use instead |
|---|---|
| Exact per-dimension comparison | `comparison-bars.md` |
| One KPI only | `kpi-dashboard.md` |
| Time trend across the same metrics | `trend-line-multi-series.md` |

<!-- source: ECharts option manual (series-radar / radar coordinate system) + examples gallery radar family -->