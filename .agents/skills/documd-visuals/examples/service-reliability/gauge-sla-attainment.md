# Gauge — SLA Attainment at a Glance (ECharts)

**Best for**: a single bounded KPI where the reader first needs the answer “are we on target?”
**Avoid when**: the reader needs many exact values or must compare several categories at once
**Answers**: how close the metric is to the goal, and whether it is comfortably on track or in warning territory

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 520,
  "height": 360,
  "title": { "text": "SLA Attainment", "subtext": "Rolling 30-day average", "left": "center", "top": 8 },
  "series": [
    {
      "type": "gauge",
      "center": ["50%", "58%"],
      "radius": "72%",
      "min": 90,
      "max": 100,
      "splitNumber": 5,
      "progress": { "show": true, "width": 16 },
      "axisLine": { "lineStyle": { "width": 16 } },
      "axisLabel": { "distance": 18, "fontSize": 10 },
      "splitLine": { "distance": -16, "length": 14 },
      "axisTick": { "distance": -16, "length": 7 },
      "pointer": { "width": 4 },
      "anchor": { "show": true, "showAbove": true, "size": 10 },
      "title": { "fontSize": 12, "offsetCenter": [0, "74%"] },
      "detail": { "fontSize": 26, "offsetCenter": [0, "44%"], "formatter": "{value}%" },
      "data": [{ "value": 98.7, "name": "target 99.0%" }]
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `min` / `max` | Defines the operational range; without them the dial can mislead badly |
| `progress.show` | Turns the gauge into a clear progress ring rather than needle-only ornament |
| `detail.formatter` | Displays the exact KPI in the chart itself |
| `center` / `radius` | Controls how much of the frame the gauge occupies |
| `splitNumber` | Sets the coarse scale marks for quick estimation |

## Data Shape

One bounded value, usually with one datum object in `data`. Gauges are strongest when the metric naturally has a target range or threshold interpretation.

## Pitfalls

- ❌ Using the default 0–100 range when the real operating band is narrow → ✅ set meaningful `min` and `max`
- ❌ Packing several gauges into one small frame → ✅ use one gauge, then move supporting metrics into bars or lines
- ❌ Decorative gauge with no exact number → ✅ always show the value directly in static exports
- ❌ Comparing categories with gauges → ✅ gauges answer status, not comparison

## Alternatives

| Variant | Use instead |
|---|---|
| Several KPIs plus supporting trends | `kpi-dashboard.md` |
| One exact trend over time | `trend-line-multi-series.md` |
| Category comparison | `comparison-bars.md` |

<!-- source: ECharts option manual (series-gauge) + examples gallery gauge family -->