# Central Concept Map — Capability Relationships (Infographic)

**Best for**: a small hub-and-spoke relationship picture where one central concept connects to a handful of related capabilities
**Avoid when**: the graph is dense, highly directional, or needs weighted edges and algorithmic layout control
**Answers**: what sits at the center, and which surrounding ideas or services relate to it

```infographic
infographic relation-circle-icon-badge
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
data
  title Capability Relationship Map
  desc Badges count the relations each node carries
  nodes
    - id core
      label Platform Core
      group central
      value 5
    - id identity
      label Identity
      group support
      value 1
    - id billing
      label Billing
      group support
      value 1
    - id search
      label Search
      group support
      value 1
    - id analytics
      label Analytics
      group support
      value 1
    - id security
      label Security
      group support
      value 1
  relations
    - from core
      to identity
    - from core
      to billing
    - from core
      to search
    - from core
      to analytics
    - from core
      to security
```

## Data Shape

Use `nodes` and `relations` when you have one center and a few simple surrounding connections. ⚠️ The
`icon-badge` item prints a number on every node: without a `value` it reads `0`, so give each node the count
the figure is about (here, how many relations it carries — 5 for the hub, 1 per satellite).

## Key Options

| Option | Effect |
|---|---|
| `relation-circle-icon-badge` | Hub-and-spoke relation treatment, with a count badge per node |
| `value 5` | The badge number; the item prints it unconditionally |
| `nodes` | Declares the entities shown in the map |
| `relations` | Declares which entities connect. **Relation labels are not drawn** by this structure — the `desc` has to carry that information |
| `group` | Lets the template distinguish the central node from its satellites |

## Pitfalls

- ❌ Large dependency webs → ✅ this family is best for a small conceptual relation map
- ❌ Treating it like a precise architecture graph → ✅ use a rectangle graph when layout control matters
- ❌ Omitting stable node IDs → ✅ relations should bind to IDs, not only labels
- ❌ Relying on `relations[].label` → ✅ the circle and network structures draw no edge labels; if the words on the arrows are the point, use a `sequence-*` template

## Alternatives

| Variant | Use instead |
|---|---|
| Directed service dependency graph | `service-dependency-network.md` |
| Explicit network or architecture topology | PlantUML or ECharts graph examples |
| Hierarchical tree | `platform-org-structure.md` |

<!-- source: AntV Infographic template reference (`relation-circle-icon-badge`) + syntax docs for nodes/relations -->