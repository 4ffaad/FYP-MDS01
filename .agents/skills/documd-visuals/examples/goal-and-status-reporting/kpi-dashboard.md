# KPI Dashboard — Gauges and Panels in One Chart (ECharts)

**Best for**: a single-glance status board — one headline metric plus supporting indicators
**Avoid when**: the reader needs to compare categories over time (use bars/lines) or read exact values for many items
**Answers**: are we on target, and how do the supporting metrics look

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 860,
  "height": 420,
  "title": { "text": "Service Health — Current Quarter", "subtext": "SLO target: 99.9% availability", "left": "left" },
  "grid": [
    { "left": 56, "top": 294, "width": 270, "bottom": 44 },
    { "left": 500, "top": 294, "right": 28, "bottom": 44 }
  ],
  "xAxis": [
    {
      "gridIndex": 0,
      "type": "category",
      "data": ["W1", "W2", "W3"],
      "axisLabel": { "show": false },
      "axisTick": { "show": false }
    },
    {
      "gridIndex": 1,
      "type": "category",
      "data": ["Mon", "Tue", "Wed", "Thu", "Fri"],
      "axisLabel": { "margin": 14 },
      "axisTick": { "alignWithLabel": true }
    }
  ],
  "yAxis": [
    { "gridIndex": 0, "type": "value", "name": "req/s", "nameGap": 28 },
    {
      "gridIndex": 1,
      "type": "value",
      "name": "errors",
      "nameGap": 22,
      "axisLabel": { "margin": 12 },
      "splitLine": { "lineStyle": { "color": "rgba(0, 0, 0, 0.2)" } }
    }
  ],
  "series": [
    {
      "name": "Availability",
      "type": "gauge",
      "center": ["31%", "38%"],
      "radius": "37%",
      "min": 98,
      "max": 100,
      "splitNumber": 4,
      "progress": { "show": true, "width": 18 },
      "axisLine": { "lineStyle": { "width": 18 } },
      "axisLabel": { "show": false },
      "splitLine": { "length": 18 },
      "pointer": { "width": 4 },
      "title": { "fontSize": 6, "offsetCenter": [0, "78%"] },
      "detail": { "valueAnimation": false, "formatter": "{value}%", "fontSize": 11, "offsetCenter": [0, "52%"] },
      "data": [{ "value": 99.94, "name": "uptime" }]
    },
    {
      "name": "P95 latency",
      "type": "gauge",
      "center": ["69%", "38%"],
      "radius": "37%",
      "min": 0,
      "max": 800,
      "splitNumber": 4,
      "progress": { "show": true, "width": 18 },
      "axisLine": { "lineStyle": { "width": 18 } },
      "axisLabel": { "show": false },
      "splitLine": { "length": 18 },
      "pointer": { "width": 4 },
      "title": { "fontSize": 6, "offsetCenter": [0, "78%"] },
      "detail": { "valueAnimation": false, "formatter": "{value}ms", "fontSize": 11, "offsetCenter": [0, "52%"] },
      "data": [{ "value": 218, "name": "budget 400ms" }]
    },
    {
      "name": "Requests",
      "type": "bar",
      "xAxisIndex": 0,
      "yAxisIndex": 0,
      "itemStyle": { "borderRadius": [4, 4, 0, 0] },
      "data": [4200, 4380, 4520]
    },
    {
      "name": "Errors",
      "type": "line",
      "xAxisIndex": 1,
      "yAxisIndex": 1,
      "symbolSize": 6,
      "data": [12, 9, 15, 7, 6]
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `grid: [ … ]` (array) | Declares multiple cartesian panels; each axis/series opts in with `xAxisIndex` / `yAxisIndex` |
| `series[].center` / `radius` on gauges | Positions each gauge independently (percent of the canvas) |
| `progress.show` + `axisLine.lineStyle.width` | Modern gauge style: a thick progress ring instead of a needle-only dial |
| `detail.offsetCenter` | Places the value under the dial; `valueAnimation: false` keeps exports deterministic |
| `min` / `max` on a gauge | **Always set them** — the default 0–100 makes a 99.9% figure meaningless |
| `"name"` per gauge datum | The small caption under the number (what the metric is) |

## Data Shape

No shared dataset: each panel has its own `grid`/axis and its own `series`. Keep each panel to one idea
(a KPI, a trend, a distribution) — a dashboard is a layout decision as much as a chart decision.

## Pitfalls

- ❌ Gauges without `min`/`max` → ✅ the needle position becomes arbitrary; set the real operating range
- ❌ Five gauges and no numbers → ✅ keep at most two gauges; put the rest in bars/lines so exact values are readable
- ❌ Animation-dependent gauges → ✅ exports are static; avoid `animation` and value animations
- ❌ Overlapping panels → ✅ panels are positioned by `grid.left/right/top/bottom` and gauge `center`; check the layout once with the rendered output

## Alternatives

| Variant | Use instead |
|---|---|
| One metric only | A single gauge with a target line, or an infographic metric card |
| Many KPIs, no trends | An infographic metric board (template-based) or an HTML card grid |
| Trend comparison | `trend-line-multi-series.md` |

<!-- source: ECharts option manual (series-gauge, grid array, multi-panel axes) + handbook canvas-vs-svg -->
