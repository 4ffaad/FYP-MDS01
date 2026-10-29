# Parallel Coordinates — Multi-Dimensional Risk Screen (ECharts)

**Best for**: comparing many records across several numeric dimensions when the pattern across dimensions matters more than one ranking
**Avoid when**: the audience is unfamiliar with the dimensions, or only one metric actually drives the decision (use bars/scatter)
**Answers**: which items are extreme, which dimensions trade off against each other, and which profiles cluster together

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 900,
  "height": 420,
  "title": { "text": "Supplier Risk Screen", "subtext": "Seven suppliers across five screening dimensions", "left": "left" },
  "parallelAxis": [
    { "dim": 0, "name": "Lead time", "min": 0, "max": 40 },
    { "dim": 1, "name": "Defect rate", "min": 0, "max": 10 },
    { "dim": 2, "name": "Single-source", "min": 0, "max": 10 },
    { "dim": 3, "name": "Margin", "min": 0, "max": 40 },
    { "dim": 4, "name": "Recovery days", "min": 0, "max": 30 }
  ],
  "parallel": {
    "left": 56,
    "right": 36,
    "top": 96,
    "bottom": 40,
    "parallelAxisDefault": {
      "nameLocation": "end",
      "nameGap": 18,
      "nameTextStyle": { "fontSize": 11 }
    }
  },
  "series": [
    {
      "type": "parallel",
      "lineStyle": { "width": 2, "opacity": 0.5 },
      "data": [
        { "name": "Supplier A", "value": [18, 2, 4, 24, 9] },
        { "name": "Supplier B", "value": [26, 3, 8, 20, 12] },
        { "name": "Supplier C", "value": [12, 1, 2, 32, 5] },
        { "name": "Supplier D", "value": [34, 6, 9, 16, 18] },
        { "name": "Supplier E", "value": [20, 4, 5, 28, 10] },
        { "name": "Supplier F", "value": [28, 7, 7, 18, 21] },
        { "name": "Supplier G", "value": [10, 2, 3, 35, 6] }
      ]
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `parallelAxis` | Declares each dimension and its numeric range |
| `parallel` | Controls the shared layout block that all axes live inside |
| `parallelAxisDefault` | Keeps axis naming and spacing consistent without repeating settings |
| `lineStyle.opacity` | Prevents the view from turning into a solid knot when lines overlap |
| Explicit `min` / `max` | Stabilizes interpretation; otherwise each dimension may auto-scale in unhelpful ways |

## Data Shape

Each record is one array of values in the exact order of the `parallelAxis` dimensions. This chart assumes all dimensions are numeric and comparable in the sense of “more/less along an axis”.

## Pitfalls

- ❌ Too many records at once → ✅ parallel coordinates saturate quickly; keep it to a small screened set in report exports
- ❌ Unclear axis ranges → ✅ always set `min` and `max`, or the chart becomes hard to compare across exports
- ❌ Using it for categorical dimensions only → ✅ this view is strongest when several numeric measures compete
- ❌ Expecting readers to infer labels on hover → ✅ static exports need a small enough record set that the overall shapes remain readable without interaction

## Alternatives

| Variant | Use instead |
|---|---|
| Two metrics only | `scatter-segment-correlation.md` |
| Exact category-by-metric comparison | `comparison-bars.md` |
| Portfolio share by hierarchy | `treemap-portfolio-breakdown.md` |

<!-- source: ECharts option manual (series-parallel / parallel / parallelAxis) + examples gallery parallel family -->