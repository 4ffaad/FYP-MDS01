# Arc Diagram — Module Import Coupling (Vega)

**Best for**: showing which items depend on which, when the node order itself carries meaning
**Avoid when**: the graph is dense — arcs quickly stack into a solid band
**Answers**: whether coupling is local (neighbours) or long-range (across the whole order)

```vega
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "width": 600,
  "height": 220,
  "padding": 8,
  "title": {"text": "Module Import Coupling", "subtitle": "Modules on a line, each import drawn as an arc · node size = degree", "anchor": "start"},
  "data": [
    {
      "name": "edges",
      "values": [
        {"source": 2, "target": 0, "weight": 3},
        {"source": 2, "target": 1, "weight": 5},
        {"source": 3, "target": 2, "weight": 2},
        {"source": 3, "target": 4, "weight": 4},
        {"source": 8, "target": 3, "weight": 6},
        {"source": 8, "target": 2, "weight": 5},
        {"source": 8, "target": 5, "weight": 3},
        {"source": 7, "target": 6, "weight": 4},
        {"source": 7, "target": 4, "weight": 3},
        {"source": 9, "target": 8, "weight": 2},
        {"source": 5, "target": 4, "weight": 2},
        {"source": 4, "target": 0, "weight": 2}
      ]
    },
    {
      "name": "sourceDegree",
      "source": "edges",
      "transform": [{"type": "aggregate", "groupby": ["source"]}]
    },
    {
      "name": "targetDegree",
      "source": "edges",
      "transform": [{"type": "aggregate", "groupby": ["target"]}]
    },
    {
      "name": "nodes",
      "values": [
        {"index": 0, "name": "config", "group": "base"},
        {"index": 1, "name": "logger", "group": "base"},
        {"index": 2, "name": "http", "group": "transport"},
        {"index": 3, "name": "auth", "group": "transport"},
        {"index": 4, "name": "db", "group": "data"},
        {"index": 5, "name": "cache", "group": "data"},
        {"index": 6, "name": "queue", "group": "data"},
        {"index": 7, "name": "worker", "group": "app"},
        {"index": 8, "name": "api", "group": "app"},
        {"index": 9, "name": "cli", "group": "app"}
      ],
      "transform": [
        {"type": "window", "ops": ["rank"], "as": ["order"]},
        {"type": "lookup", "from": "sourceDegree", "key": "source", "fields": ["name"], "as": ["sourceDegree"], "default": {"count": 0}},
        {"type": "lookup", "from": "targetDegree", "key": "target", "fields": ["name"], "as": ["targetDegree"], "default": {"count": 0}},
        {"type": "formula", "as": "degree", "expr": "datum.sourceDegree.count + datum.targetDegree.count"}
      ]
    },
    {
      "name": "layout",
      "source": "nodes",
      "transform": [
        {"type": "formula", "as": "x", "expr": "scale('position', datum.order) + bandwidth('position') / 2"},
        {"type": "formula", "as": "size", "expr": "120 + 60 * datum.degree"}
      ]
    },
    {
      "name": "arcs",
      "source": "edges",
      "transform": [
        {"type": "lookup", "from": "layout", "key": "index", "fields": ["source", "target"], "as": ["sourceNode", "targetNode"]},
        {
          "type": "linkpath",
          "shape": "arc",
          "orient": "horizontal",
          "sourceX": {"expr": "min(datum.sourceNode.x, datum.targetNode.x)"},
          "targetX": {"expr": "max(datum.sourceNode.x, datum.targetNode.x)"},
          "sourceY": {"expr": "height - 34"},
          "targetY": {"expr": "height - 34"}
        }
      ]
    }
  ],
  "scales": [
    {"name": "position", "type": "band", "domain": {"data": "nodes", "field": "order", "sort": true}, "range": "width"},
    {"name": "color", "type": "ordinal", "domain": {"data": "nodes", "field": "group"}, "range": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"]}
  ],
  "legends": [
    {"fill": "color", "title": "Layer", "orient": "right", "symbolType": "circle"}
  ],
  "marks": [
    {
      "type": "path",
      "from": {"data": "arcs"},
      "encode": {
        "update": {
          "path": {"field": "path"},
          "stroke": {"scale": "color", "field": "sourceNode.group"},
          "strokeOpacity": {"value": 0.45},
          "strokeWidth": {"field": "weight", "mult": 0.8}
        }
      }
    },
    {
      "type": "symbol",
      "from": {"data": "layout"},
      "encode": {
        "update": {
          "x": {"field": "x"},
          "y": {"signal": "height - 34"},
          "size": {"field": "size"},
          "fill": {"scale": "color", "field": "group"},
          "fillOpacity": {"value": 0.9}
        }
      }
    },
    {
      "type": "text",
      "from": {"data": "nodes"},
      "interactive": false,
      "encode": {
        "update": {
          "x": {"scale": "position", "field": "order"},
          "y": {"signal": "height - 34"},
          "dy": {"value": 14},
          "text": {"field": "name"},
          "fontSize": {"value": 10},
          "align": {"value": "right"},
          "baseline": {"value": "middle"},
          "angle": {"value": -55}
        }
      }
    }
  ]
}


```

## Data Shape

Four tables, all derived from two inputs:

| Dataset | Role |
|---|---|
| `nodes` | One row per module, with `index` used as the edge endpoint key |
| `edges` | `source` / `target` **indices**, plus a `weight` |
| `sourceDegree` / `targetDegree` | `aggregate` counts per endpoint, used to size the nodes |
| `layout` | An invisible symbol mark that materialises the band-scale x position for every node |

## Key Options

| Option | Effect |
|---|---|
| `band` scale with `sort: true` | Orders the nodes along the line; use an explicit `sort` when the order is meaningful rather than alphabetical |
| Degree via `aggregate` + `lookup` | Node size encodes connectivity, computed from the edges rather than hand-entered |
| `linkpath` with `shape: "arc"` | Curves each edge above the node line |
| `min`/`max` on the endpoints | An arc diagram ignores direction, so the arc always spans left→right |
| `strokeWidth: weight * 0.8` | Edge weight as thickness — a faint second encoding that survives export |
| The invisible `layout` mark | Vega has no separate "layout" concept; an `opacity: 0` symbol mark is the idiom for publishing derived positions |

## Pitfalls

- ❌ A dense graph → ✅ arcs stack into an opaque band; filter to the heaviest edges
- ❌ Letting the arcs run off the canvas → ✅ they are drawn upward from the node line, so the view needs vertical room; the node row is placed near the bottom here
- ❌ Directional reading → ✅ arcs do not encode direction; use arrows or a force layout when direction matters
- ❌ A meaningful node order chosen alphabetically → ✅ the order *is* the interpretation (layer here), so it must be deliberate

## Alternatives

| Variant | Use instead |
|---|---|
| Clusters and hubs from a physics layout | `service-call-force-map.md` |
| Directed dependency flow | `service-ownership-circle-graph.md` (ECharts) |
| Order not required | `platform-dependency-graph.md` (Infographic) |

<!-- source: Vega docs (lookup, linkpath arc shape, aggregate, window rank transforms; band scales) + the arc-diagram gallery example -->
