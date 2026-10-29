# Pictorial Bar — Capacity as Repeated Symbols (ECharts)

**Best for**: small-count comparisons where the visual metaphor helps the reader grasp relative capacity quickly
**Avoid when**: exact values dominate or the counts are large enough that repeated icons turn into texture
**Answers**: who has more capacity, and how much larger one category feels than another

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 820,
  "height": 380,
  "title": { "text": "Support Capacity by Team", "subtext": "Analyst seats represented as repeated symbols", "left": "left" },
  "grid": { "left": 84, "right": 24, "top": 92, "bottom": 36 },
  "xAxis": {
    "type": "category",
    "data": ["Core", "Billing", "Logistics", "Identity", "Data"],
    "axisTick": { "show": false }
  },
  "yAxis": {
    "type": "value",
    "name": "seats",
    "nameLocation": "end",
    "nameGap": 12,
    "max": 20,
    "interval": 5
  },
  "series": [
    {
      "type": "pictorialBar",
      "symbol": "roundRect",
      "symbolRepeat": true,
      "symbolSize": [24, 10],
      "symbolMargin": 2,
      "symbolBoundingData": 20,
      "itemStyle": { "color": "#2b66c4" },
      "data": [18, 10, 14, 8, 12]
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `type: "pictorialBar"` | Uses repeated symbols instead of a filled bar |
| `symbolRepeat: true` | Turns the mark into stacked units rather than a single stretched icon |
| `symbolBoundingData` | Defines the scale that the repeated units map against |
| `symbolSize` / `symbolMargin` | Controls whether repeated units stay distinct in static output |
| `yAxis.max` | Keeps all categories on the same symbolic scale |

## Data Shape

Exactly like a simple bar chart: one category axis and one numeric value per category. The difference is visual encoding, not data structure.

## Pitfalls

- ❌ Using pictorial bars for large values → ✅ repeated symbols stop being legible once the count gets too high
- ❌ No fixed bounding data or axis max → ✅ the symbolism becomes inconsistent across categories or exports
- ❌ Dense decorative icons → ✅ keep symbols simple enough that repetition stays readable
- ❌ Expecting precise reading from shape alone → ✅ use this when rough magnitude plus a metaphor is the point

## Alternatives

| Variant | Use instead |
|---|---|
| Exact quantitative comparison | `comparison-bars.md` |
| One KPI only | `kpi-dashboard.md` |
| Share of total | `donut-channel-mix.md` |

<!-- source: ECharts option manual (series-pictorialBar) + examples gallery pictorialBar family -->