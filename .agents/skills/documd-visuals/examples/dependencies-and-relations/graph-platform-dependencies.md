# Graph — Platform Dependency Map (ECharts)

**Best for**: small relationship networks where the reader needs to see central nodes and direct dependencies without a strict hierarchy
**Avoid when**: the flow direction or layer order matters more than adjacency (use a rectangle graph or sankey)
**Answers**: which services sit at the centre, which nodes are peripheral, and where the densest coupling appears

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 860,
  "height": 420,
  "title": { "text": "Platform Dependency Map", "subtext": "Fixed layout for static export", "left": "left" },
  "series": [
    {
      "type": "graph",
      "layout": "none",
      "left": 20,
      "top": 72,
      "right": 20,
      "bottom": 20,
      "symbolSize": 44,
      "label": { "show": true, "fontSize": 11 },
      "lineStyle": { "color": "#2b66c4", "opacity": 0.55, "width": 2 },
      "edgeSymbol": ["none", "arrow"],
      "data": [
        { "name": "Gateway", "x": 430, "y": 90, "itemStyle": { "color": "#7048e8" } },
        { "name": "Identity", "x": 220, "y": 170 },
        { "name": "Catalog", "x": 430, "y": 190 },
        { "name": "Billing", "x": 640, "y": 170 },
        { "name": "Search", "x": 300, "y": 300 },
        { "name": "Orders", "x": 560, "y": 300 },
        { "name": "Warehouse", "x": 430, "y": 360 }
      ],
      "links": [
        { "source": "Gateway", "target": "Identity" },
        { "source": "Gateway", "target": "Catalog" },
        { "source": "Gateway", "target": "Billing" },
        { "source": "Catalog", "target": "Search" },
        { "source": "Catalog", "target": "Orders" },
        { "source": "Orders", "target": "Warehouse" },
        { "source": "Billing", "target": "Orders" },
        { "source": "Identity", "target": "Orders" }
      ]
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `layout: "none"` | Uses explicit coordinates, which is much safer than force layout for static export |
| `data[{ x, y }]` | Pins each node to a chosen position |
| `edgeSymbol` | Makes dependency direction visible without needing hover |
| `symbolSize` + `label.show` | Keeps nodes readable at report scale |
| `lineStyle.opacity` | Softens edges so the nodes remain the primary reading target |

## Data Shape

Two arrays: `data[{ name, x, y }]` for nodes and `links[{ source, target }]` for edges. A fixed layout is best when the export must be deterministic.

## Pitfalls

- ❌ Force layout with animation disabled → ✅ static exports can freeze before the graph tells a clean story; use fixed coordinates
- ❌ Too many nodes in one frame → ✅ beyond a small network, labels and edges turn into a hairball
- ❌ Using graph when layers matter → ✅ for explicit architectural layers, use a PlantUML deployment/component view
- ❌ Undirected edges when dependency direction matters → ✅ add arrows if the relation is not symmetric

## Alternatives

| Variant | Use instead |
|---|---|
| Flow volume between stages | `sankey-channel-to-fulfilment.md` |
| Emergent relationship clusters | `relationship-network-neato.md` |
| Layered architecture | plantuml component/deployment examples |

<!-- source: ECharts option manual (series-graph) + examples gallery graph family -->