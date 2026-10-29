# Isotype Grid — One Square Per On-Call Engineer (Vega-Lite)

**Best for**: making a small headcount tangible — the reader counts squares instead of reading digits
**Avoid when**: counts are in the hundreds, or exact comparison between rows is the point
**Avoids**: log scales and rounding arguments
**Answers**: which squads can sustain an on-call rotation, and which are one absence from breaking

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 460,
  "height": 210,
  "title": {"text": "On-Call Eligible Engineers", "subtitle": "One square = one engineer, eight slots per rotation", "anchor": "start"},
  "data": {"sequence": {"start": 0, "stop": 48, "as": "slot"}},
  "transform": [
    {"calculate": "floor(datum.slot / 8)", "as": "teamIdx"},
    {"calculate": "datum.slot % 8", "as": "pos"},
    {"calculate": "['Core','Search','Identity','Billing','Mobile','Platform'][datum.teamIdx]", "as": "team"},
    {"calculate": "[6,3,8,5,2,7][datum.teamIdx]", "as": "units"},
    {"filter": "datum.pos < datum.units"}
  ],
  "layer": [
    {
      "mark": {"type": "square", "size": 190, "filled": true},
      "encoding": {
        "x": {"field": "pos", "type": "ordinal", "title": null, "axis": null},
        "y": {"field": "team", "type": "ordinal", "title": null},
        "color": {"field": "team", "type": "nominal", "legend": null}
      }
    },
    {
      "mark": {"type": "text", "align": "left", "dx": 8, "fontSize": 11},
      "encoding": {
        "x": {"field": "units", "type": "ordinal"},
        "y": {"field": "team", "type": "ordinal"},
        "text": {"field": "units", "type": "quantitative"}
      }
    }
  ]
}
```

## Data Shape

There is no data file — the rows are **generated**:

| Step | Effect |
|---|---|
| `data.sequence` start 0, stop 48 (6 squads × 8 slots) | Produces one row per possible slot |
| `calculate floor(slot / 8)` | Splits the sequence into squads |
| `calculate slot % 8` | Slot index inside the row → the x position |
| `calculate [6,3,8,5,2,7][teamIdx]` | The actual headcount per squad |
| `filter pos < units` | Keeps only the filled slots |

## Key Options

| Option | Effect |
|---|---|
| `sequence` generator | Grid rows without pasting 31 near-identical objects |
| `filter` with an expression | Drops the empty slots, leaving the classic isotype silhouette |
| `mark.square` + `size` | A fixed square size keeps the "one square = one person" promise |
| Text layer at `x: units` | The count sits right after the last square, so the digit never has to be inferred |
| Shared x scale across layers | Both layers share the ordinal x domain, so rows stay aligned |

## Pitfalls

- ❌ Varying the square size per row → ✅ the unit must stay constant or the chart becomes a bar chart drawn with squares
- ❌ Units in the hundreds → ✅ counting stops working; use a bar chart
- ❌ Parts of a unit (0.5 people) → ✅ isotype counts whole things; round and say so, or pick a different unit ("one square = 10 hours")
- ❌ A row with zero units → ✅ it disappears entirely; label such squads in the copy

## Alternatives

| Variant | Use instead |
|---|---|
| Exact comparison of the same squads | `comparison-bars.md` (ECharts) |
| Squad size against a target | `target-attainment-bullet.md` |
| Squad composition rather than size | `quarterly-share-normalized-stack.md` |

<!-- source: Vega-Lite docs (sequence data generator, calculate and filter transforms, square point marks, layered text) + the unit-chart entries in the community gallery -->
