# Force Layout — Service Call Topology (Vega)

**Best for**: a small dependency map where clusters and hubs should emerge from the links themselves
**Avoid when**: the graph is large, or the picture must be identical on every build (use a circular layout)
**Answers**: which services are hubs, and which groups of services call each other

```vega
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "width": 620,
  "height": 420,
  "padding": 8,
  "title": {"text": "Service Call Topology", "subtitle": "Static force layout — links pull, nodes repel", "anchor": "start"},
  "data": [
    {
      "name": "nodes",
      "values": [
        {"id": "gateway", "group": "edge"},
        {"id": "cdn", "group": "edge"},
        {"id": "webhook", "group": "edge"},
        {"id": "auth", "group": "platform"},
        {"id": "config", "group": "platform"},
        {"id": "notify", "group": "platform"},
        {"id": "billing", "group": "core"},
        {"id": "ledger", "group": "core"},
        {"id": "search", "group": "core"},
        {"id": "media", "group": "core"}
      ]
    },
    {
      "name": "links",
      "values": [
        {"source": "gateway", "target": "auth"},
        {"source": "gateway", "target": "search"},
        {"source": "gateway", "target": "billing"},
        {"source": "gateway", "target": "media"},
        {"source": "auth", "target": "config"},
        {"source": "billing", "target": "ledger"},
        {"source": "billing", "target": "notify"},
        {"source": "ledger", "target": "notify"},
        {"source": "search", "target": "media"},
        {"source": "notify", "target": "config"},
        {"source": "webhook", "target": "billing"},
        {"source": "cdn", "target": "media"}
      ]
    },
    {
      "name": "nodePos",
      "source": "nodes",
      "transform": [
        {
          "type": "force",
          "iterations": 300,
          "static": true,
          "as": ["x", "y"],
          "forces": [
            {"force": "center", "x": {"signal": "width / 2"}, "y": {"signal": "height / 2"}},
            {"force": "nbody", "strength": -420, "theta": 0.9},
            {"force": "link", "links": "links", "distance": 115, "id": "id"}
          ]
        }
      ]
    },
    {
      "name": "linkPath",
      "source": "links",
      "transform": [
        {"type": "formula", "as": "ready", "expr": "data('nodePos') ? 1 : 0"},
        {"type": "linkpath", "shape": "line"}
      ]
    }
  ],
  "scales": [
    {"name": "color", "type": "ordinal", "domain": {"data": "nodes", "field": "group"}, "range": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"]}
  ],
  "legends": [
    {"stroke": "color", "symbolType": "circle", "title": "Layer", "orient": "right", "direction": "vertical"}
  ],
  "marks": [
    {
      "type": "path",
      "from": {"data": "linkPath"},
      "interactive": false,
      "encode": {
        "update": {
          "path": {"field": "path"},
          "stroke": {"value": "#2b66c4"},
          "strokeWidth": {"value": 1.3},
          "strokeOpacity": {"value": 0.8}
        }
      }
    },
    {
      "type": "symbol",
      "from": {"data": "nodePos"},
      "encode": {
        "update": {
          "x": {"field": "x"},
          "y": {"field": "y"},
          "size": {"value": 420},
          "fill": {"scale": "color", "field": "group"},
          "stroke": {"value": "transparent"},
          "fillOpacity": {"value": 0.9}
        }
      }
    },
    {
      "type": "text",
      "from": {"data": "nodePos"},
      "interactive": false,
      "encode": {
        "update": {
          "x": {"field": "x"},
          "y": {"field": "y"},
          "dy": {"value": 4},
          "align": {"value": "center"},
          "fontSize": {"value": 10},
          "text": {"field": "id"}
        }
      }
    }
  ]
}


```

## Data Shape

Two plain tables — nodes with an `id`, links with `source` / `target` matching those ids — plus one derived
dataset:

| Dataset | Contents |
|---|---|
| `nodes` | `id` and a grouping field used for colour |
| `links` | `source` / `target` node ids |
| `nodePos` | `nodes` run through the `force` transform, which appends `x` and `y` |

## Key Options

| Option | Effect |
|---|---|
| `"static": true` | Runs the physics to completion **before** rendering — mandatory for an exported image |
| `force: "link"` with `id` | Uses the node id as the join key, so links need no positional data |
| `nbody` with negative strength | Repulsion; more negative spreads the graph out |
| `iterations: 300` | More iterations = a more settled layout; below ~50 the graph looks half-formed |
| `linkpath` with a `lookup` | Turns edge rows into paths by pulling endpoint coordinates from the node dataset |
| `interactive: false` on the edges | Prevents the paths from swallowing pointer events (relevant when the same spec is shown live) |

## Pitfalls

- ❌ A force layout without `static: true` → ✅ the render is captured mid-simulation and produces a different picture on every run
- ❌ Position anchors in the data → ✅ a force layout computes positions; hard-coded `x`/`y` are ignored unless you use `layout: "none"` in Vega-Lite
- ❌ Reading distance as weight → ✅ in a force layout, link length is a *parameter*, not a measurement; annotate edge weight separately if it matters
- ❌ More than ~40 nodes → ✅ repulsion turns the picture into a hairball; aggregate or filter first

## Alternatives

| Variant | Use instead |
|---|---|
| Topology only, deterministic ring | `graph-platform-dependencies.md` (ECharts, circular layout) |
| Pairwise weights between groups | `chord-team-handoffs.md` (ECharts) |
| Imports over a linear order | `module-import-arcs.md` |

<!-- source: Vega docs (force transform: static / iterations / center-nbody-link forces; linkpath transform; lookup transform) + the force-directed-layout gallery example -->
