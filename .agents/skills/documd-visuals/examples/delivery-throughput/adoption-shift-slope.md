# Slope Graph — Tooling Adoption, Then and Now (Vega-Lite)

**Best for**: exactly two time points, where the reader should see who crossed whom
**Avoid when**: there are more than two periods (use a line chart) or many series
**Answers**: which tools gained ground, which lost it, and where the lines cross

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 340,
  "height": 280,
  "data": {
    "values": [
      {"tool": "TypeScript", "q1": 62, "q2": 78},
      {"tool": "Go", "q1": 41, "q2": 44},
      {"tool": "Python", "q1": 35, "q2": 52},
      {"tool": "Rust", "q1": 12, "q2": 29},
      {"tool": "Ruby", "q1": 22, "q2": 9}
    ]
  },
  "transform": [
    {"fold": ["q1", "q2"], "as": ["period", "share"]}
  ],
  "layer": [
    {
      "mark": {"type": "line", "strokeWidth": 2.5, "opacity": 0.85},
      "encoding": {
        "x": {"field": "period", "type": "ordinal", "title": null, "sort": ["q1", "q2"], "axis": {"labelAngle": 0}},
        "y": {"field": "share", "type": "quantitative", "title": "% of new services", "scale": {"zero": true}},
        "detail": {"field": "tool"}
      }
    },
    {
      "transform": [{"filter": "datum.period === 'q1'"}],
      "mark": {"type": "text", "align": "right", "dx": -8, "fontSize": 11},
      "encoding": {
        "x": {"field": "period", "type": "ordinal", "sort": ["q1", "q2"]},
        "y": {"field": "share", "type": "quantitative"},
        "text": {"field": "tool"}
      }
    },
    {
      "transform": [{"filter": "datum.period === 'q2'"}],
      "mark": {"type": "text", "align": "left", "dx": 8, "fontSize": 11},
      "encoding": {
        "x": {"field": "period", "type": "ordinal", "sort": ["q1", "q2"]},
        "y": {"field": "share", "type": "quantitative"},
        "text": {"field": "tool"}
      }
    }
  ]
}
```

## Data Shape

One row per series with **one column per time point**. The `fold` transform turns the wide row into
`period` / `share` pairs, which is what lets both endpoints use the same encodings.

| Field | Role |
|---|---|
| `tool` | `detail` on the line layer — one line per tool, no colour legend needed |
| `period` | Ordinal x with only two values, so the axis reads as "before / after" |
| `share` | Quantitative y, shared by all three layers |

## Key Options

| Option | Effect |
|---|---|
| `transform.fold` | Wide-to-long without a `calculate` per period |
| `detail` instead of `color` | Keeps every line the same hue; the end labels do the naming |
| `x.sort: ["q1","q2"]` | Guarantees left-to-right order — automatic sorting is disabled by the renderer |
| Two filtered text layers | End labels on both sides; a single unfiltered text layer would only label one end |
| `dx: ±8` with `align` | Pushes labels away from the endpoints so they never sit on the line |
| `scale.zero: true` | Shares are ratios; a truncated axis turns small changes into dramatic slopes |

## Pitfalls

- ❌ More than two periods → ✅ a slope graph is a before/after form; three or more points need a line chart
- ❌ Labelling only one end → ✅ the crossings are the insight; readers need both names to follow them
- ❌ Scale-free endpoints (different denominators) → ✅ both periods must measure the same population, otherwise the slope is meaningless
- ❌ Too many series → ✅ past ~8 lines the labels overlap and the crossings become a thicket

## Alternatives

| Variant | Use instead |
|---|---|
| Many periods over time | `trend-line-multi-series.md` (ECharts) |
| Rank changes over many periods | `rank-movement-over-time.md` |
| A continuous path through a two-variable space | `growth-vs-efficiency-path.md` |

<!-- source: Vega-Lite docs (fold transform, detail channel, layered text marks, ordinal sort) + the slope-graph gallery entries -->
