# Heatmap — Incident Load by Day and Hour (ECharts)

**Best for**: showing intensity across two ordered dimensions such as day/hour, team/week, or product/region
**Avoid when**: the reader needs exact values for every cell or the matrix is extremely sparse (use a table or dots)
**Answers**: when concentration peaks happen, and which rows or columns stay consistently heavy or light

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 860,
  "height": 420,
  "title": {
    "text": "Incident Load by Day and Hour",
    "subtext": "Last four weeks aggregated",
    "left": "left",
    "top": 10,
    "itemGap": 14,
    "subtextStyle": { "lineHeight": 18 }
  },
  "grid": { "left": 88, "right": 36, "top": 118, "bottom": 48 },
  "xAxis": {
    "type": "category",
    "data": ["00", "04", "08", "12", "16", "20"],
    "splitArea": { "show": true }
  },
  "yAxis": {
    "type": "category",
    "data": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "splitArea": { "show": true }
  },
  "visualMap": {
    "show": false,
    "min": 0,
    "max": 24,
    "inRange": {
      "color": ["#2b66c4", "#2f9e44", "#f3a33c"]
    }
  },
  "series": [
    {
      "name": "Incidents",
      "type": "heatmap",
      "label": { "show": true, "fontSize": 10 },
      "emphasis": { "itemStyle": { "shadowBlur": 6, "shadowColor": "rgba(0, 0, 0, 0.25)" } },
      "data": [
        [0, 0, 6], [1, 0, 4], [2, 0, 9], [3, 0, 14], [4, 0, 18], [5, 0, 10],
        [0, 1, 5], [1, 1, 3], [2, 1, 8], [3, 1, 12], [4, 1, 16], [5, 1, 9],
        [0, 2, 4], [1, 2, 4], [2, 2, 7], [3, 2, 11], [4, 2, 15], [5, 2, 8],
        [0, 3, 7], [1, 3, 6], [2, 3, 10], [3, 3, 16], [4, 3, 24], [5, 3, 13],
        [0, 4, 8], [1, 4, 7], [2, 4, 12], [3, 4, 18], [4, 4, 22], [5, 4, 14],
        [0, 5, 3], [1, 5, 2], [2, 5, 4], [3, 5, 6], [4, 5, 8], [5, 5, 5],
        [0, 6, 2], [1, 6, 2], [2, 6, 3], [3, 6, 5], [4, 6, 7], [5, 6, 4]
      ]
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `series.type: "heatmap"` | Encodes value by color on a 2D categorical grid |
| `visualMap` | Maps values to color; in tight static exports it can stay hidden while still driving the palette |
| `splitArea.show` | Makes each grid cell legible in export, especially on dark themes |
| `label.show` | Useful for compact report-size matrices where every cell count still matters |
| `grid` | Heatmaps need extra left/bottom room because both axes carry full labels |

## Data Shape

Each item is `[xIndex, yIndex, value]`, where `xIndex` maps into `xAxis.data` and `yIndex` maps into `yAxis.data`. Keep both axes ordered, because heatmaps depend on adjacency.

## Pitfalls

- ❌ Unordered categories on either axis → ✅ heatmaps only work when neighboring cells have a meaningful sequence
- ❌ Color-only heatmap with no numbers or scale → ✅ in static exports, keep labels on, or show a visible `visualMap` when layout allows
- ❌ Huge sparse matrices with many zeros → ✅ use dots or a table when empty cells dominate
- ❌ Depending on hover for exact values → ✅ static exports need either labels or a small enough grid to read directly

## Alternatives

| Variant | Use instead |
|---|---|
| Time trend by one measure | `trend-line-multi-series.md` |
| Exact row/column comparison | `comparison-bars.md` |
| Day-level density over long periods | `calendar-release-pace.md` |

<!-- source: ECharts option manual (series-heatmap / visualMap / splitArea) + examples gallery heatmap family -->