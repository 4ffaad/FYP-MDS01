# Circle Packing — Build Artifact Sizes (Vega)

**Best for**: a hierarchy where nesting should be visible as containment rather than as partitions
**Avoid when**: the values are close together — circle area exaggerates differences
**Answers**: which artifact group dominates the bundle, and how the leaves compare inside it

```vega
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "width": 520,
  "height": 400,
  "padding": 8,
  "title": {"text": "Build Artifact Sizes", "subtitle": "Circle area is proportional to megabytes shipped", "anchor": "start"},
  "data": [
    {
      "name": "tree",
      "values": [
        {"id": "all", "parent": null, "name": "Artifacts", "size": 56},
        {"id": "images", "parent": "all", "name": "Container images", "size": 28},
        {"id": "api", "parent": "images", "name": "api", "size": 12},
        {"id": "worker", "parent": "images", "name": "worker", "size": 9},
        {"id": "admin", "parent": "images", "name": "admin", "size": 7},
        {"id": "bundles", "parent": "all", "name": "JS bundles", "size": 9},
        {"id": "app", "parent": "bundles", "name": "app", "size": 5},
        {"id": "embed", "parent": "bundles", "name": "embed", "size": 4},
        {"id": "static", "parent": "all", "name": "Static assets", "size": 19},
        {"id": "fonts", "parent": "static", "name": "fonts", "size": 8},
        {"id": "icons", "parent": "static", "name": "icons", "size": 6},
        {"id": "docs", "parent": "static", "name": "docs", "size": 5}
      ],
      "transform": [
        {"type": "stratify", "key": "id", "parentKey": "parent"},
        {
          "type": "pack",
          "field": "size",
          "sort": {"field": "value"},
          "size": [{"signal": "width"}, {"signal": "height"}]
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
      "type": "symbol",
      "from": {"data": "tree"},
      "encode": {
        "update": {
          "x": {"field": "x"},
          "y": {"field": "y"},
          "size": {"signal": "4 * datum.r * datum.r"},
          "fill": {"scale": "color", "field": "depth"},
          "fillOpacity": {"value": 0.85}
        }
      }
    },
    {
      "type": "text",
      "from": {"data": "tree"},
      "interactive": false,
      "encode": {
        "update": {
          "x": {"field": "x"},
          "y": {"field": "y"},
          "text": {"field": "name"},
          "fontSize": {"value": 10},
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

The same flat parent/child table as a treemap, but the `pack` transform emits **`x`, `y` and `r`** instead of
rectangle corners. Parent sizes again equal the sum of their children.

| Output | Used by |
|---|---|
| `x`, `y` | Circle centres, shared by the symbol and text marks |
| `r` | Radius — the symbol mark converts it with `size: 4 * r * r` |
| `depth` | Drives the colour ramp so rings of nesting are visually separated |

## Key Options

| Option | Effect |
|---|---|
| `size: 4 * datum.r * datum.r` | Vega symbol sizes are areas, so the radius must be squared to keep the packing metric |
| `fillOpacity: 0.85` | Lets overlapping nest levels read as layers rather than flat discs |
| Depth colour ramp + matching label ramp | The outer (deepest) circles are darkest, so their labels need the light text colour |
| `sort` by value | Packs large circles first, which produces a tighter figure |
| `size: [width, height]` on the transform | Fits the packing to the view box |

## Pitfalls

- ❌ Passing `r` straight into `size` → ✅ symbol `size` is an area, so the packing would be visually wrong and overlapping
- ❌ Circles with similar values → ✅ the eye struggles with area; a treemap or bar chart compares better
- ❌ Empty parents → ✅ a group whose children sum to zero collapses and its label overwrites a neighbour's
- ❌ Long labels on small circles → ✅ they overflow into the neighbouring circle; label only what fits or move labels to a legend

## Alternatives

| Variant | Use instead |
|---|---|
| Rectangular proportional nesting | `cost-center-treemap.md` |
| Hierarchy in rings | `catalog-sunburst-share.md` |
| Leaf values only | `comparison-bars.md` (ECharts) |

<!-- source: Vega docs (stratify + pack transforms; symbol size as area) + the circle-packing gallery example -->
