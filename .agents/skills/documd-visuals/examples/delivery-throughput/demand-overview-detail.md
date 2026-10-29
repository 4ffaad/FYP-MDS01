# Overview + Detail — Two-Panel Time Slice (Vega-Lite)

**Best for**: putting a broad context chart above a focused detail chart when one panel alone would either hide the big picture or the important local variation
**Avoid when**: interaction is required to brush or zoom between panels, or the dataset is trivial enough for one chart
**Answers**: what the overall pattern is, and what one important segment looks like up close

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "title": {"text": "Overview and Detail", "subtitle": "Weekly demand with a closer look at the recent range", "anchor": "start"},
  "data": {
    "values": [
      {"week": "2026-03-04", "demand": 74},
      {"week": "2026-03-11", "demand": 78},
      {"week": "2026-03-18", "demand": 83},
      {"week": "2026-03-25", "demand": 88},
      {"week": "2026-04-01", "demand": 92},
      {"week": "2026-04-08", "demand": 98},
      {"week": "2026-04-15", "demand": 105},
      {"week": "2026-04-22", "demand": 111},
      {"week": "2026-04-29", "demand": 116}
    ]
  },
  "vconcat": [
    {
      "width": 500,
      "height": 120,
      "mark": {"type": "area", "opacity": 0.25, "color": "#2b66c4"},
      "encoding": {
        "x": {"field": "week", "type": "temporal", "title": null},
        "y": {"field": "demand", "type": "quantitative", "title": "Demand"}
      }
    },
    {
      "width": 500,
      "height": 200,
      "transform": [{"filter": "toDate(datum.week) >= toDate('2026-04-01')"}],
      "mark": {"type": "line", "strokeWidth": 2.5, "color": "#0f9b9b"},
      "encoding": {
        "x": {"field": "week", "type": "temporal", "title": null},
        "y": {"field": "demand", "type": "quantitative", "title": "Demand"}
      }
    }
  ]
}
```

## Data Shape

One temporal series reused in two vertically concatenated views, with the lower panel filtered to the most relevant slice.

## Key Options

| Option | Effect |
|---|---|
| `vconcat` | Stacks overview and detail views in one composed spec |
| Filtered second panel | Narrows attention without losing the full context |
| Different marks per panel | Lets the overview read as shape and the detail read as precision |
| Shared dataset | Keeps the story internally consistent |

## Pitfalls

- ❌ Expecting interactive linked brushing → ✅ this static pattern uses fixed filter logic, not interaction
- ❌ Making both panels visually identical → ✅ the point is to change the reading scale, not duplicate the chart
- ❌ Overusing concat for small datasets → ✅ one chart is often enough unless the detail genuinely adds value

## Alternatives

| Variant | Use instead |
|---|---|
| One forecast plus uncertainty | `forecast-range-band.md` |
| Faceted comparison across segments | `segment-pattern-small-multiples.md` |
| KPI plus sparkline card | HTML/CSS or infographic card layouts |

<!-- source: Vega-Lite docs (concat composition / filter transform) + examples gallery Repeat & Concatenation -->