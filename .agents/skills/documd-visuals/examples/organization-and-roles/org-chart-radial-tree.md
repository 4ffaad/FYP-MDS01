# Radial Tree — Platform Org Chart (Vega)

**Best for**: a hierarchy with a natural centre, where the fan-out matters more than the reading order
**Avoid when**: labels are long, or the hierarchy is deep and lopsided (a left-to-right tree reads better)
**Answers**: which pillar owns which teams, and how evenly the org fans out

```vega
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "width": 520,
  "height": 520,
  "padding": 12,
  "title": {"text": "Platform Organisation", "subtitle": "Cluster layout on a ring — one spoke per team", "anchor": "start"},
  "data": [
    {
      "name": "tree",
      "values": [
        {"id": 1, "parent": null, "name": "Platform"},
        {"id": 2, "parent": 1, "name": "Runtime"},
        {"id": 3, "parent": 1, "name": "Data"},
        {"id": 4, "parent": 1, "name": "Client"},
        {"id": 5, "parent": 2, "name": "Core services"},
        {"id": 6, "parent": 2, "name": "Build & release"},
        {"id": 7, "parent": 3, "name": "Streaming"},
        {"id": 8, "parent": 3, "name": "Analytics"},
        {"id": 9, "parent": 4, "name": "Web"},
        {"id": 10, "parent": 4, "name": "Mobile"}
      ],
      "transform": [
        {"type": "stratify", "key": "id", "parentKey": "parent"},
        {
          "type": "tree",
          "method": "cluster",
          "size": [{"signal": "2 * PI"}, {"signal": "width / 2 - 46"}],
          "as": ["alpha", "radius", "depth", "children"]
        }
      ]
    },
    {
      "name": "links",
      "source": "tree",
      "transform": [
        {"type": "treelinks", "key": "id"},
        {
          "type": "linkpath",
          "shape": "diagonal",
          "orient": "radial",
          "sourceX": {"expr": "datum.source.alpha"},
          "sourceY": {"expr": "datum.source.radius"},
          "targetX": {"expr": "datum.target.alpha"},
          "targetY": {"expr": "datum.target.radius"}
        }
      ]
    }
  ],
  "scales": [
    {"name": "color", "type": "ordinal", "domain": {"data": "tree", "field": "depth"}, "range": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"]}
  ],
  "marks": [
    {
      "type": "path",
      "from": {"data": "links"},
      "interactive": false,
      "encode": {
        "update": {"stroke": {"value": "#2f9e44"}, "strokeWidth": {"value": 1.6}}
      }
    },
    {
      "type": "symbol",
      "from": {"data": "tree"},
      "encode": {
        "update": {
          "x": {"signal": "width / 2 + datum.radius * cos(datum.alpha - PI / 2)"},
          "y": {"signal": "height / 2 + datum.radius * sin(datum.alpha - PI / 2)"},
          "size": {"signal": "datum.depth === 0 ? 900 : datum.depth === 1 ? 480 : 190"},
          "fill": {"scale": "color", "field": "depth"}
        }
      }
    },
    {
      "type": "text",
      "from": {"data": "tree"},
      "interactive": false,
      "encode": {
        "update": {
          "x": {"signal": "width / 2 + datum.radius * cos(datum.alpha - PI / 2)"},
          "y": {"signal": "height / 2 + datum.radius * sin(datum.alpha - PI / 2)"},
          "text": {"field": "name"},
          "fontSize": {"value": 10},
          "align": {"signal": "datum.alpha < PI ? 'right' : 'left'"},
          "baseline": {"value": "middle"},
          "radius": {"value": 9},
          "angle": {"signal": "datum.alpha < PI ? (datum.alpha - PI / 2) * 180 / PI : (datum.alpha + PI / 2) * 180 / PI"}
        }
      }
    }
  ]
}


```

## Data Shape

A flat parent/child table — `id` plus `parentKey` — that the transforms turn into geometry:

| Transform | Effect |
|---|---|
| `stratify` | Builds the hierarchy from `id` / `parent`; the root is the row with a null parent |
| `tree` with `method: "cluster"` | Assigns every leaf an equal slice of the circle (use `"tidy"` to weight by subtree size) |
| `treelinks` | Emits one row per parent→child edge, carrying `source` and `target` objects |
| `linkpath` with `orient: "radial"` | Turns each edge into a curved path using the polar outputs (`alpha`, `radius`) |

## Key Options

| Option | Effect |
|---|---|
| `size: [2π, width/2]` | Maps the first tree output to the full circle and the second to the radius |
| `method: "cluster"` | Equal angular spacing per leaf — the classic org-chart look; `"tidy"` produces uneven, more compact fans |
| `cos/sin` with `- PI/2` | Rotates the tree so the first child starts at twelve o'clock |
| `angle` flipping at `alpha < PI` | Keeps labels readable on both halves instead of upside down on one side |
| `radius: 9` on the text marks | Pushes labels off the node discs |

## Pitfalls

- ❌ A deep, unbalanced tree in a ring → ✅ radial trees waste the middle; if one branch is far deeper than the others, use a horizontal tree
- ❌ Labels without the `alpha < PI` flip → ✅ half the labels render upside down and mirrored
- ❌ Too many leaves → ✅ the outer ring needs ~14px of arc per label; beyond ~30 leaves, aggregate levels
- ❌ Missing `parentKey: null` on the root → ✅ `stratify` throws when no root is identifiable

## Alternatives

| Variant | Use instead |
|---|---|
| Hierarchy with explicit left/right sides | `platform-org-structure.md` (Infographic) |
| Hierarchy plus magnitude | `cost-center-treemap.md` |
| Grouping without a hierarchy | `service-call-force-map.md` |

<!-- source: Vega docs (stratify / tree / treelinks / linkpath radial transforms) + the radial-tree-layout gallery example -->
