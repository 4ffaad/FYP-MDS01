# Boxplot — Latency Distribution by Region (ECharts)

**Best for**: comparing distributions across categories when medians, spread, and outliers matter more than raw point counts
**Avoid when**: the audience is unfamiliar with quartiles and whiskers, or you need every individual point shown explicitly
**Answers**: which groups are slower or more variable, and where outliers appear

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 860,
  "height": 400,
  "title": { "text": "API Latency Distribution", "subtext": "P50-P95 spread by region, current week", "left": "left" },
  "grid": { "left": 70, "right": 24, "top": 88, "bottom": 44 },
  "xAxis": {
    "type": "category",
    "data": ["US-East", "EU-West", "AP-South"],
    "boundaryGap": true,
    "nameGap": 30,
    "splitArea": { "show": false }
  },
  "yAxis": {
    "type": "value",
    "name": "ms",
    "nameLocation": "end",
    "nameGap": 10,
    "min": 0,
    "max": 420,
    "splitArea": { "show": true }
  },
  "series": [
    {
      "type": "boxplot",
      "data": [
        [72, 96, 118, 144, 188],
        [84, 110, 136, 174, 226],
        [98, 132, 168, 220, 302]
      ]
    },
    {
      "type": "scatter",
      "data": [
        [0, 236],
        [1, 268],
        [2, 346]
      ],
      "symbolSize": 10
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `series.type: "boxplot"` | Encodes five-number summaries directly as box-and-whisker marks |
| Boxplot `data` order | The tuple is `[min, Q1, median, Q3, max]`, so ordering errors completely change the chart |
| Companion `scatter` series | A simple way to surface explicit outliers next to the box summaries |
| Fixed y-axis bounds | Prevents one extreme outlier from compressing the whole chart unexpectedly |
| `splitArea.show` | Helps readers estimate quartile positions without adding more labels |

## Data Shape

One category array on the x-axis, one five-number summary tuple per category for the boxplot series, and optional `[categoryIndex, value]` points for explicit outliers.

## Pitfalls

- ❌ Misordered boxplot tuples → ✅ the chart will still render, but it will mean something false
- ❌ Expecting raw counts from a boxplot → ✅ this chart summarises a distribution; it does not show sample size by itself
- ❌ Hiding outliers when they matter → ✅ add a small scatter overlay if exceptional cases are part of the story
- ❌ Using a boxplot for one tiny sample → ✅ with very few observations, show the raw points instead

## Alternatives

| Variant | Use instead |
|---|---|
| Raw points and clusters | `scatter-segment-correlation.md` |
| One aggregate trend | `trend-line-multi-series.md` |
| Category comparison of a single summary metric | `comparison-bars.md` |

<!-- source: ECharts option manual (series-boxplot) + examples gallery boxplot family -->