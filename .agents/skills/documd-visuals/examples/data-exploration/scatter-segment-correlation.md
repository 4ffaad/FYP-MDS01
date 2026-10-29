# Scatter — Correlation Between Spend and Retention (ECharts)

**Best for**: checking correlation, clusters, and outliers between two quantitative measures
**Avoid when**: the x-axis is categorical, the points imply a sequence, or the reader needs exact ranking (use bars or lines)
**Answers**: whether two measures move together, which segments cluster, and which points behave unusually

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 820,
  "height": 400,
  "title": { "text": "Campaign Spend vs 90-Day Retention", "subtext": "One point per acquisition segment", "left": "left" },
  "grid": { "left": 72, "right": 56, "top": 88, "bottom": 48 },
  "xAxis": {
    "type": "value",
    "name": "Spend per acquired user ($)",
    "nameLocation": "middle",
    "nameGap": 30,
    "min": 10,
    "max": 70
  },
  "yAxis": {
    "type": "value",
    "name": "90-day retention (%)",
    "nameLocation": "middle",
    "nameGap": 46,
    "min": 20,
    "max": 60,
    "axisLabel": { "formatter": "{value}%" }
  },
  "series": [
    {
      "type": "scatter",
      "symbolSize": 14,
      "label": { "show": true, "position": "top", "formatter": "{@[2]}" },
      "data": [
        [18, 26, "Coupons"],
        [24, 31, "Affiliate"],
        [30, 38, "SEO"],
        [34, 41, "Referral"],
        [42, 46, "Marketplace"],
        [56, 54, "Enterprise trial"]
      ],
      "markLine": {
        "silent": true,
        "symbol": "none",
        "lineStyle": { "type": "dashed", "color": "#d1242f" },
        "label": { "color": "#d1242f" },
        "data": [
          { "xAxis": 40, "label": { "formatter": "spend guardrail", "position": "insideEndTop", "distance": 8 } },
          { "yAxis": 45, "label": { "formatter": "retention target", "position": "insideStartTop", "distance": 8 } }
        ]
      }
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `xAxis/yAxis.type: "value"` | A scatter plot only makes sense on numeric axes |
| `label.formatter: "{@[2]}"` | Reads the third field in each point tuple, which is a compact way to label points |
| `symbolSize` | Makes individual points legible in export without overwhelming the frame |
| `markLine` | Adds thresholds or guardrails without turning the chart into a full quadrant analysis |
| Fixed `min` / `max` | Stops auto-scaling from exaggerating weak relationships |

## Data Shape

An array of point tuples. Here each point is `[x, y, label]`, where `x` and `y` are quantitative measures and the third value is the segment name shown on the chart.

## Pitfalls

- ❌ Categorical x values in a scatter plot → ✅ if one axis is categorical, use bars or strip plots instead
- ❌ Auto-scaled axes making weak effects look dramatic → ✅ set sensible bounds when the narrative depends on distance
- ❌ Too many labels on too many points → ✅ label only the important or small set of points in static output
- ❌ Reading a trend line into six random points → ✅ a scatter plot suggests correlation, not causation

## Alternatives

| Variant | Use instead |
|---|---|
| Time trend of one measure | `trend-line-multi-series.md` |
| Category comparison | `comparison-bars.md` |
| Distribution summary | `boxplot` or histogram |

<!-- source: ECharts option manual (series-scatter / markLine) + examples gallery scatter family -->