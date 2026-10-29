# Relation Network — Service Dependencies (Infographic)

**Best for**: a small labeled dependency or concept network where the audience benefits from a pre-styled relational map rather than a low-level graph grammar
**Avoid when**: the network is large, weighted, or needs algorithmic layout control (use a rectangle graph)
**Answers**: which services depend on which others, and where the central connectors sit

```infographic
infographic
theme
  colorPrimary #2b66c4
  palette
    - #2b66c4
    - #2f9e44
    - #f3a33c
    - #d1242f
    - #7048e8
    - #0f9b9b
    - #c16f8a
    - #7c5a3d
design
  structure relation-dagre-flow
  item rounded-rect-node
data
  title Service Dependency Network
  desc Core runtime dependencies around the order path, each arrow naming the call
  nodes
    - id gateway
      label Gateway
    - id auth
      label Identity
    - id catalog
      label Catalog
    - id orders
      label Orders
    - id billing
      label Billing
    - id warehouse
      label Warehouse
  relations
    - from gateway
      to auth
      label auth
    - from gateway
      to catalog
      label browse
    - from gateway
      to orders
      label checkout
    - from orders
      to billing
      label charge
    - from orders
      to warehouse
      label fulfil
```

## Data Shape

Use `nodes` plus `relations`. Nodes should have stable `id` values; relations connect them with `from` and `to`, and may carry a short `label`.

## Key Options

| Option | Effect |
|---|---|
| `design` → `structure relation-dagre-flow` | Ranked flow layout; **the only relation structure that draws the relation labels** |
| `design` → `item rounded-rect-node` | Boxes with their labels inside. `simple-circle-node` draws a bare circle — its label is a tooltip, so it exports as an unnamed dot |
| `nodes` | Declares the entities in the network |
| `relations` | Declares the connections, each with a `label` naming the call |
| Inline `design` block | Needed because `relation-dagre-flow` has no built-in template name |

## Pitfalls

- ❌ `relation-network-simple-circle-node` for a labelled map → ✅ it draws circles only: no node labels and no relation labels, so the figure is nameless. Use the inline `relation-dagre-flow` design
- ❌ Treating this as a precise architecture topology → ✅ it is a high-level relation map, not a protocol diagram
- ❌ Too many nodes → ✅ relation templates saturate quickly; keep them small and conceptual
- ❌ Omitting stable IDs → ✅ relation edges should bind to node IDs, not only display labels

## Alternatives

| Variant | Use instead |
|---|---|
| Rich dependency graph with layout control | `dependencies-and-relations/dependency-graph.md` |
| Ordered process flow | `product-roadmap-sequence.md` or PlantUML flow examples |
| Layered system structure | PlantUML or HTML architecture overviews |

<!-- source: AntV Infographic syntax docs (`nodes` + `relations`, inline `design` block) — relation labels verified to render only under `relation-dagre-flow` -->