# Population Pyramid — Workforce by Age Band and Track (Vega-Lite)

**Best for**: two mirrored distributions over shared ordered bands, where the asymmetry is the story
**Avoid when**: the two halves are not the same kind of quantity, or the ordering is not meaningful
**Answers**: where each track's workforce sits by age, and which bands are top-heavy

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 420,
  "height": 260,
  "title": {"text": "Workforce by Age Band", "subtitle": "Engineering (left) and go-to-market (right), headcount", "anchor": "start"},
  "data": {
    "values": [
      {"band": "18–24", "eng": 42, "gtm": 12},
      {"band": "25–29", "eng": 118, "gtm": 34},
      {"band": "30–34", "eng": 156, "gtm": 58},
      {"band": "35–39", "eng": 131, "gtm": 71},
      {"band": "40–44", "eng": 88, "gtm": 63},
      {"band": "45–49", "eng": 54, "gtm": 47},
      {"band": "50+", "eng": 31, "gtm": 39}
    ]
  },
  "transform": [
    {"calculate": "-datum.eng", "as": "engNeg"}
  ],
  "layer": [
    {
      "mark": {"type": "bar", "color": "#2b66c4", "cornerRadius": 2, "height": 16},
      "encoding": {
        "y": {"field": "band", "type": "ordinal", "title": null},
        "x": {"field": "engNeg", "type": "quantitative", "title": "headcount", "axis": {"labelExpr": "abs(datum.value)"}}
      }
    },
    {
      "mark": {"type": "bar", "color": "#d1242f", "cornerRadius": 2, "height": 16},
      "encoding": {
        "y": {"field": "band", "type": "ordinal", "title": null},
        "x": {"field": "gtm", "type": "quantitative", "title": "headcount"}
      }
    }
  ]
}
```

## Data Shape

One row per ordered band with **one column per side**. Enter the bands in reading order — the renderer
disables automatic sorting, so the y-axis follows the order of rows in `values`.

| Field | Role |
|---|---|
| `band` | Shared ordinal axis; list from youngest to oldest so the base of the pyramid sits at the bottom |
| `eng` | Left side, negated by a `calculate` transform so bars grow left |
| `gtm` | Right side, used as-is |

## Key Options

| Option | Effect |
|---|---|
| `calculate: "-datum.eng"` | Mirroring is a data trick: negative bars on a shared scale |
| `axis.labelExpr: "abs(datum.value)"` | Shows the absolute counts on the axis instead of the negative values |
| Two layers, shared scales | Layer defaults share the x scale, so both sides measure the same headcount axis |
| `height: 16` on the bars | Leaves a gap between bands — a pyramid with touching bands reads as a solid shape |
| Explicit colours per layer | Two sides, two hues; a colour legend would only restate the subtitle |

## Pitfalls

- ❌ Two separate charts side by side → ✅ the pyramid's whole point is one shared axis, so the two sides are comparable at a glance
- ❌ Negating the value in the data file → ✅ keep source values positive and mirror them in a transform, otherwise every downstream sum is wrong
- ❌ Forgetting `labelExpr` → ✅ the axis will print negative numbers for one side
- ❌ Unequal band widths → ✅ age bands must cover the same span or the silhouette lies about the distribution

## Alternatives

| Variant | Use instead |
|---|---|
| Two values per category that changed between periods | `before-after-latency-gap.md` |
| Composition of each band | `quarterly-share-normalized-stack.md` |
| Distribution of one measure | `service-latency-density.md` |

<!-- source: Vega-Lite docs (calculate transform, axis.labelExpr, layered bar marks, shared scales) + the population-pyramid gallery entry -->
