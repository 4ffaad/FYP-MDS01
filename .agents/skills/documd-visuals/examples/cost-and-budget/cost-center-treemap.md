# Treemap — Cloud Cost Centres by Size (Vega)

**Best for**: a hierarchy whose areas must be proportional to a measure, packed without gaps
**Avoid when**: exact comparisons matter (area is hard to read) or the hierarchy is only two levels
**Answers**: which teams and sub-services consume the cloud budget, and how the leaf sizes compare

```vega
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "width": 540,
  "height": 340,
  "padding": 6,
  "title": {"text": "Cloud Spend by Cost Centre", "subtitle": "Area is proportional to monthly spend (kUSD)", "anchor": "start"},
  "data": [
    {
      "name": "tree",
      "values": [
        {"id": "cloud", "parent": null, "name": "Cloud", "size": 100},
        {"id": "compute", "parent": "cloud", "name": "Compute", "size": 42},
        {"id": "gpu", "parent": "compute", "name": "GPU training", "size": 18},
        {"id": "batch", "parent": "compute", "name": "Batch jobs", "size": 14},
        {"id": "notebooks", "parent": "compute", "name": "Notebooks", "size": 10},
        {"id": "storage", "parent": "cloud", "name": "Storage", "size": 31},
        {"id": "object", "parent": "storage", "name": "Object store", "size": 19},
        {"id": "backups", "parent": "storage", "name": "Backups", "size": 12},
        {"id": "traffic", "parent": "cloud", "name": "Traffic", "size": 27},
        {"id": "egress", "parent": "traffic", "name": "Egress", "size": 16},
        {"id": "ingress", "parent": "traffic", "name": "Ingress", "size": 11}
      ],
      "transform": [
        {"type": "stratify", "key": "id", "parentKey": "parent"},
        {
          "type": "treemap",
          "field": "size",
          "sort": {"field": "value", "order": "descending"},
          "method": "squarify",
          "ratio": 1.2,
          "size": [{"signal": "width"}, {"signal": "height"}],
          "round": true
        }
      ]
    }
  ],
  "scales": [
    {"name": "color", "type": "ordinal", "domain": {"data": "tree", "field": "depth"}, "range": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"]},
    {"name": "label", "type": "ordinal", "domain": {"data": "tree", "field": "depth"}, "range": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"]}
  ],
  "marks": [
    {
      "type": "rect",
      "from": {"data": "tree"},
      "encode": {
        "update": {
          "x": {"field": "x0"},
          "y": {"field": "y0"},
          "x2": {"field": "x1"},
          "y2": {"field": "y1"},
          "fill": {"scale": "color", "field": "depth"},
          "stroke": {"value": "#ffffff"},
          "strokeWidth": {"value": 1.5}
        }
      }
    },
    {
      "type": "text",
      "from": {"data": "tree"},
      "interactive": false,
      "encode": {
        "update": {
          "x": {"signal": "(datum.x0 + datum.x1) / 2"},
          "y": {"signal": "(datum.y0 + datum.y1) / 2"},
          "text": {"field": "name"},
          "fontSize": {"value": 11},
          "fontWeight": {"signal": "datum.depth === 1 ? 'bold' : 'normal'"},
          "align": {"value": "center"},
          "baseline": {"value": "middle"},
          "fill": {"scale": "label", "field": "depth"}
        }
      }
    }
  ]
}


```

## Data Shape

A flat parent/child table where **every node carries a `size`**, and a parent's size equals the sum of its
children. The layout is then computed entirely by the `treemap` transform.

| Field | Meaning |
|---|---|
| `size` | The measure; parent sizes must equal the child sums or the nesting will not tile |
| `parent` | Null only for the root, otherwise the parent's `id` |
| `x0/y0/x1/y1` | Output by the transform — the rectangle corners used by the marks |

## Key Options

| Option | Effect |
|---|---|
| `method: "squarify"` | Produces near-square tiles, which are easier to compare than long slabs |
| `method: "binary"` / `"slice"` / `"dice"` | Other tilings; `slice`/`dice` give long strips and are usually harder to read |
| `ratio: 1.2` | Aspect-ratio target for `squarify`; larger values allow thinner rectangles |
| `round: true` | Snaps coordinates to whole pixels — prevents seams between tiles |
| `sort` by value descending | Puts the largest tiles first in reading order |
| Depth-indexed colour ramps (rect **and** text) | A label colour scale keeps text legible on both the light and dark end of the fill ramp |

## Pitfalls

- ❌ Parent sizes that do not equal the sum of their children → ✅ the transform positions by the given sizes, so the hierarchy and the packing disagree
- ❌ Three or four levels → ✅ the deepest level becomes unreadable slivers; keep to two levels and aggregate below
- ❌ Comparing small tiles by area → ✅ human area judgement is poor; label the values you want compared
- ❌ White labels on the light end of the ramp → ✅ pair a fill scale with a matching text-colour scale, as here

## Alternatives

| Variant | Use instead |
|---|---|
| Hierarchy as proportions in rings | `catalog-sunburst-share.md` |
| Hierarchy as nested circles | `asset-size-packing.md` |
| One level of the same values | `comparison-bars.md` (ECharts) |

<!-- source: Vega docs (stratify + treemap transforms, rect marks with x0/y0/x1/y1 outputs) + the treemap gallery example -->
