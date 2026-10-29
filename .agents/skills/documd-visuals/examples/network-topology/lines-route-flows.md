# Lines — Flow Between Fixed Business Stages (ECharts)

**Best for**: directional links between known points when the path itself matters more than node size
**Avoid when**: you need conserved volume across many branches (use sankey) or a free-form relationship graph (use graph)
**Answers**: which routes exist, which ones are strongest, and where traffic converges or fans out

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 860,
  "height": 420,
  "title": { "text": "Route Flows Between Fulfilment Stages", "subtext": "Fixed positions for static export", "left": "left" },
  "grid": { "left": 32, "right": 32, "top": 96, "bottom": 24 },
  "xAxis": { "show": false, "min": 0, "max": 100, "type": "value" },
  "yAxis": { "show": false, "min": 0, "max": 100, "type": "value" },
  "series": [
    {
      "type": "scatter",
      "symbolSize": 42,
      "label": { "show": true, "position": "inside", "fontSize": 11, "formatter": "{@[2]}" },
      "itemStyle": { "color": "#2b66c4" },
      "data": [
        [12, 52, "Queue"],
        [36, 26, "Review"],
        [36, 76, "Auto route"],
        [64, 52, "Dispatch"],
        [88, 52, "Carrier"]
      ],
      "encode": { "x": 0, "y": 1 },
      "labelLayout": { "hideOverlap": true }
    },
    {
      "type": "lines",
      "coordinateSystem": "cartesian2d",
      "polyline": false,
      "lineStyle": {
        "width": 4,
        "curveness": 0.22,
        "opacity": 0.65,
        "color": "#7048e8"
      },
      "data": [
        { "coords": [[12, 52], [36, 26]], "value": 28 },
        { "coords": [[12, 52], [36, 76]], "value": 72 },
        { "coords": [[36, 26], [64, 52]], "value": 28 },
        { "coords": [[36, 76], [64, 52]], "value": 72 },
        { "coords": [[64, 52], [88, 52]], "value": 100 }
      ]
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `series.type: "lines"` | Draws directional routes between explicit coordinate pairs |
| `coordinateSystem: "cartesian2d"` | Lets the flow lines share the same fixed plane as node markers |
| `curveness` | Separates adjacent routes so they do not collapse into one straight segment |
| `lineStyle.width` / `opacity` | Keeps the routes visually present without drowning the node labels |
| `scatter` + `lines` overlay | Uses simple fixed-position node markers plus routed edges on the same cartesian plane |

## Data Shape

Each line item uses `coords: [[x1, y1], [x2, y2]]` on a numeric plane. Here a small fixed-position scatter layer is overlaid so the stage names remain readable in export.

## Pitfalls

- ❌ No explicit coordinate system → ✅ lines need a plane to live on unless used with geo
- ❌ Many overlapping routes → ✅ static exports need either stronger curvature or fewer routes
- ❌ Using lines where node relationships matter more than paths → ✅ a graph or sankey is often clearer
- ❌ Depending on animated effects → ✅ trail effects are canvas-oriented and not a safe default for this SVG export path

## Alternatives

| Variant | Use instead |
|---|---|
| Conserved flow with quantities by stage | `sankey-channel-to-fulfilment.md` |
| General dependency map | `graph-platform-dependencies.md` |
| Process diagram with semantic steps | plantuml flow examples |

<!-- source: ECharts option manual (series-lines) + examples gallery lines family -->