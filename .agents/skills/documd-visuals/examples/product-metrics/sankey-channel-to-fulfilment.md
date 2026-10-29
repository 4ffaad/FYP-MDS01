# Sankey — Flow from Channel to Fulfilment Outcome (ECharts)

**Best for**: quantities that move from a few sources into a few outcomes and need to show how volume splits across destinations
**Avoid when**: the question is only stage drop-off with one linear path (use a funnel) or the structure is a strict hierarchy (use a tree)
**Answers**: where flow volume ends up, which routes dominate, and how sources distribute across outcomes

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 860,
  "height": 400,
  "title": { "text": "Order Flow by Channel", "subtext": "Weekly volume routed into fulfilment outcomes", "left": "left" },
  "series": [
    {
      "type": "sankey",
      "nodeAlign": "justify",
      "left": 36,
      "top": 104,
      "right": 56,
      "bottom": 28,
      "nodeWidth": 22,
      "nodeGap": 10,
      "emphasis": { "focus": "adjacency" },
      "label": { "color": "inherit", "fontSize": 11 },
      "itemStyle": { "borderWidth": 1, "borderColor": "rgba(255,255,255,0.5)" },
      "lineStyle": { "color": "source", "curveness": 0.5, "opacity": 0.45 },
      "data": [
        { "name": "Web", "depth": 0 },
        { "name": "Marketplace", "depth": 0 },
        { "name": "Partner API", "depth": 0 },
        { "name": "Ship same day", "depth": 1 },
        { "name": "Ship next day", "depth": 1 },
        { "name": "Back-order", "depth": 1 }
      ],
      "links": [
        { "source": "Web", "target": "Ship same day", "value": 360 },
        { "source": "Web", "target": "Ship next day", "value": 100 },
        { "source": "Web", "target": "Back-order", "value": 40 },
        { "source": "Marketplace", "target": "Ship same day", "value": 130 },
        { "source": "Marketplace", "target": "Ship next day", "value": 90 },
        { "source": "Marketplace", "target": "Back-order", "value": 40 },
        { "source": "Partner API", "target": "Ship same day", "value": 90 },
        { "source": "Partner API", "target": "Ship next day", "value": 110 },
        { "source": "Partner API", "target": "Back-order", "value": 40 }
      ]
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `nodeWidth` / `nodeGap` | Controls whether the nodes read like clear stages or collapse into a dense block |
| `lineStyle.color: "source"` | Colors each flow by its upstream source, which helps branch tracing |
| `lineStyle.curveness` | Opens the ribbons enough to separate adjacent routes visually |
| `emphasis.focus: "adjacency"` | Useful in preview for path tracing, but the static export still reads because the ribbons are distinct |
| `left` / `right` / `top` / `bottom` | Sankey needs layout room more than most charts; cramped bounds make labels collide |

## Data Shape

Two arrays: `data[{ name }]` for nodes and `links[{ source, target, value }]` for flows. Here each source sends volume into several outcomes, so the split pattern is the story.

## Pitfalls

- ❌ Treating a sankey like a hierarchy → ✅ this chart is about volume transfer, not parent/child structure
- ❌ Too many tiny links in one frame → ✅ aggregate minor paths before exporting or the chart turns into ribbon noise
- ❌ Inconsistent totals between incoming and outgoing flow at a stage → ✅ check the arithmetic before you publish; readers assume conservation unless noted
- ❌ Writing path labels into the ribbons → ✅ static sankey charts read better with clean node labels and well-separated flows

## Alternatives

| Variant | Use instead |
|---|---|
| Linear stage attrition | `funnel-stage-conversion.md` |
| Network relationships without conserved volume | `relationship-network-neato.md` |
| Layered process architecture | plantuml architecture / flow examples |

<!-- source: ECharts option manual (series-sankey) + examples gallery sankey family -->