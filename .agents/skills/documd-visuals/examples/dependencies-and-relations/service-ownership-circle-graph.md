# Circular Graph — Who Owns Which Shared Service (ECharts)

**Best for**: a small, dense relation map where a deterministic ring layout beats a jittery force layout
**Avoid when**: the graph is large, directional or has meaningful clusters (use a force layout or a matrix)
**Answers**: which teams touch a shared service, and which services are single-owner islands

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 800,
  "height": 600,
  "title": { "text": "Service Ownership Around the Platform Ring", "subtext": "Arrows point from owner to consumer", "left": "left" },
  "series": [
    {
      "name": "Ownership",
      "type": "graph",
      "layout": "circular",
      "circular": { "rotateLabel": true },
      "symbolSize": 34,
      "label": { "show": true, "position": "right", "fontSize": 11 },
      "lineStyle": { "curveness": 0.2, "opacity": 0.7, "width": 1.6 },
      "edgeSymbol": ["none", "arrow"],
      "edgeSymbolSize": 8,
      "data": [
        { "name": "Gateway" },
        { "name": "Auth" },
        { "name": "Billing" },
        { "name": "Search" },
        { "name": "Notify" },
        { "name": "Ledger" },
        { "name": "Media" },
        { "name": "Config" }
      ],
      "links": [
        { "source": "Gateway", "target": "Auth" },
        { "source": "Gateway", "target": "Search" },
        { "source": "Gateway", "target": "Billing" },
        { "source": "Billing", "target": "Ledger" },
        { "source": "Billing", "target": "Notify" },
        { "source": "Search", "target": "Media" },
        { "source": "Notify", "target": "Config" },
        { "source": "Auth", "target": "Config" },
        { "source": "Media", "target": "Config" },
        { "source": "Ledger", "target": "Notify" }
      ]
    }
  ]
}
```

## Data Shape

`data` lists the nodes; `links` lists `source` → `target` pairs by node **name**. No coordinates are needed —
the circular layout places the nodes evenly on a ring, in array order.

## Key Options

| Option | Effect |
|---|---|
| `layout: "circular"` | Deterministic ring: every render produces the same picture, unlike a force layout |
| `circular.rotateLabel: true` | Rotates labels tangentially so a dense ring stays readable |
| `edgeSymbol: ["none", "arrow"]` | Adds direction without a separate `directed` flag |
| `lineStyle.curveness: 0.2` | Bowed edges separate reciprocal pairs instead of drawing one line on top of the other |
| `symbolSize: 34` | Node size is fixed — the ring is a topology view, not a magnitude view |
| `lineStyle.opacity` | Keeps crossing edges faint so the node ring stays legible |

## Pitfalls

- ❌ Using a ring layout for cluster discovery → ✅ a ring imposes an order; use `layout: "force"` when grouping is the question
- ❌ Encoding a metric in `symbolSize` while the layout is circular → ✅ the ring suggests equal standing; move magnitudes to a separate chart
- ❌ Missing `links` entries for isolated nodes → ✅ every node must appear in `data` even with no edges, and isolated nodes should be labelled as such in the copy
- ❌ Relying on `layout: "force"` for a static export → ✅ force layouts need animation to settle; the ring is the export-safe choice

## Alternatives

| Variant | Use instead |
|---|---|
| Clusters and hubs, no imposed order | `graph-platform-dependencies.md` (force) |
| Pairwise weights rather than topology | `chord-team-handoffs.md` |
| Two-dimensional scores per pair | `matrix-service-scorecards.md` |

<!-- source: ECharts option manual (series-graph layout / circular.rotateLabel / edgeSymbol) + the circular-layout gallery entry -->
