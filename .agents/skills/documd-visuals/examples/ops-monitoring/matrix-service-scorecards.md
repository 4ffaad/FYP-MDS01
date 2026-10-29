# Matrix — Service Scorecards as a Metric Grid (ECharts)

**Best for**: comparing several entities against the same set of metrics in one aligned grid where position matters as much as value
**Avoid when**: the reader needs one full chart per entity, or the values are better understood as trends over time
**Answers**: which service/metric cells are strongest or weakest, and where the outliers cluster in the grid

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 900,
  "height": 420,
  "title": { "text": "Service Scorecards", "subtext": "Errors, latency, and satisfaction by team", "left": "left" },
  "matrix": {
    "left": 110,
    "top": 108,
    "right": 40,
    "bottom": 52,
    "x": {
      "data": ["Core", "Billing", "Search", "Identity", "Orders", "Warehouse"]
    },
    "y": {
      "data": ["Err", "Lat", "CSAT"]
    }
  },
  "visualMap": {
    "show": false,
    "min": 0,
    "max": 100,
    "inRange": {
      "color": ["#2b66c4", "#2f9e44", "#f3a33c"]
    }
  },
  "series": [
    {
      "type": "heatmap",
      "coordinateSystem": "matrix",
      "label": { "show": true, "fontSize": 11 },
      "data": [
        ["Core", "Err", 18], ["Billing", "Err", 26], ["Search", "Err", 14], ["Identity", "Err", 22], ["Orders", "Err", 31], ["Warehouse", "Err", 19],
        ["Core", "Lat", 54], ["Billing", "Lat", 62], ["Search", "Lat", 49], ["Identity", "Lat", 58], ["Orders", "Lat", 67], ["Warehouse", "Lat", 45],
        ["Core", "CSAT", 88], ["Billing", "CSAT", 81], ["Search", "CSAT", 91], ["Identity", "CSAT", 84], ["Orders", "CSAT", 76], ["Warehouse", "CSAT", 89]
      ]
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `matrix` | Declares the row/column grid and its labels directly |
| `coordinateSystem: "matrix"` | Lets the series snap to named matrix cells rather than a cartesian grid |
| Hidden `visualMap` | Drives the color scale while the cell labels carry the exact values |
| Heatmap cell labels | Makes each score readable in a static export |
| Shared matrix axes | Keeps every service/metric intersection aligned in one consistent plane |

## Data Shape

Each datum is `[xCategory, yCategory, value]`, where both categories must exist in the matrix `x.data` and `y.data` definitions.

## Pitfalls

- ❌ Too many rows/columns in one frame → ✅ once labels shrink too far, the matrix loses its comparison advantage
- ❌ No visible value labels or clear color mapping → ✅ in static exports, numbers or a visible legend have to carry the precision
- ❌ Mismatched category names between matrix axes and data rows → ✅ one typo sends a cell nowhere
- ❌ Expecting matrix to behave like repeated cartesian grids → ✅ it is its own coordinate system with named cells

## Alternatives

| Variant | Use instead |
|---|---|
| One overlaid multi-series chart | `comparison-bars.md` or `trend-line-multi-series.md` |
| One heatmap over two ordered axes | `heatmap-incident-load.md` |
| Hierarchical portfolio views | `treemap-portfolio-breakdown.md` |

<!-- source: ECharts option manual (matrix coordinate system, layout on matrix) + v6 matrix examples -->