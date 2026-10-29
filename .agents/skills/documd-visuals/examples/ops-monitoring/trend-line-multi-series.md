# Trend Line with Multiple Series and a Second Axis (ECharts)

**Best for**: two measures with different units over time (revenue vs conversion rate), plus a target line
**Avoid when**: the two series do not share a time axis, or the reader only needs one number (use a KPI card)
**Answers**: how measures move over time and whether they hit the target

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 820,
  "height": 360,
  "title": { "text": "Revenue and Conversion Rate", "subtext": "Monthly, excluding internal traffic", "left": "left" },
  "tooltip": { "trigger": "axis" },
  "legend": { "data": ["Revenue (k€)", "Conversion rate (%)"], "top": 8, "right": 8 },
  "grid": { "left": 64, "right": 64, "top": 92, "bottom": 40 },
  "xAxis": {
    "type": "category",
    "boundaryGap": false,
    "data": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"]
  },
  "yAxis": [
    {
      "type": "value",
      "name": "k€",
      "nameLocation": "end",
      "nameGap": 10,
      "axisLabel": { "formatter": "{value}" }
    },
    {
      "type": "value",
      "name": "%",
      "nameLocation": "end",
      "nameGap": 10,
      "min": 0,
      "max": 6,
      "axisLabel": { "formatter": "{value}%" }
    }
  ],
  "series": [
    {
      "name": "Revenue (k€)",
      "type": "line",
      "smooth": true,
      "symbolSize": 6,
      "data": [120, 138, 131, 156, 172, 168, 191, 205],
      "markLine": {
        "silent": true,
        "symbol": "none",
        "lineStyle": { "type": "dashed", "color": "#d1242f" },
        "label": { "position": "insideStartTop", "distance": 6, "color": "#d1242f" },
        "data": [{ "yAxis": 180, "label": { "formatter": "target 180k€" } }]
      }
    },
    {
      "name": "Conversion rate (%)",
      "type": "line",
      "yAxisIndex": 1,
      "smooth": false,
      "symbolSize": 6,
      "lineStyle": { "type": "dotted" },
      "data": [3.1, 3.4, 3.2, 3.9, 4.4, 4.1, 4.8, 5.2]
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `yAxis: [ … ]` (array) | Declares two axes; the second series binds to it with `yAxisIndex: 1` |
| `"name": "k€"` / `"name": "%"` | Axis unit labels — without them dual-axis charts are ambiguous |
| `markLine.data[{ yAxis: 180 }]` | Target or threshold line inside the series (no extra series needed) |
| `boundaryGap: false` | Removes the gap before the first category — correct for time series |
| `smooth: true` | Softens the line; keep `false` when exact values matter (e.g. conversion rate) |
| `grid: { left, right, top, bottom }` | Reserve room for axis names and the legend; otherwise labels get clipped |
| `lineStyle.type` | `solid` / `dashed` / `dotted` — a second encoding channel besides colour |

## Data Shape

`xAxis.data` = labels, one `series` per measure, each with a matching-length `data` array. Inline arrays are the
right choice for report-size data.

## Pitfalls

- ❌ Two series, one axis, different units → ✅ the smaller series vanishes; add the second axis and label both units
- ❌ Dual axes used to exaggerate a correlation → ✅ state the units and keep `max` fixed; dual axes are the most
  misused chart feature there is
- ❌ Animation left on → ✅ exports are static; the renderer disables animation by default — do not set `"animation": true`
- ❌ `tooltip`/`dataZoom` treated as features of the document → ✅ they only exist in the live preview; exports are static

## Alternatives

| Variant | Use instead |
|---|---|
| Single measure with target | Plain line + `markLine`, drop the second axis |
| Need data transforms or composed views | The same data in `vega-lite` (better transform support) |
| Distribution rather than trend | `echarts` boxplot or histogram |

<!-- source: ECharts option manual (markLine / dual yAxis / grid) + handbook canvas-vs-svg notes -->
