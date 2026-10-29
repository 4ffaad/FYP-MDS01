# Normalized Mix Bars — Where Engineering Time Goes (ECharts)

**Best for**: comparing the **composition** of several periods when the periods are not the same size
**Avoid when**: absolute volume matters (normalised bars hide the totals) or there are only two categories
**Answers**: how the share of each activity type shifts from quarter to quarter

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 820,
  "height": 400,
  "title": { "text": "Engineering Time by Activity", "subtext": "Share of each quarter, % of tracked capacity", "left": "left" },
  "legend": { "data": ["Feature work", "Support & on-call", "Tech debt", "Meetings"], "top": 8, "right": 8 },
  "grid": { "left": 64, "right": 32, "top": 96, "bottom": 36 },
  "xAxis": { "type": "category", "data": ["Q1", "Q2", "Q3", "Q4"] },
  "yAxis": { "type": "value", "max": 100, "name": "% capacity", "nameLocation": "end", "nameGap": 14, "axisLabel": { "formatter": "{value}%" } },
  "series": [
    {
      "name": "Feature work",
      "type": "bar",
      "stack": "share",
      "barMaxWidth": 64,
      "label": { "show": true, "position": "inside", "formatter": "{c}%" },
      "data": [42, 38, 33, 40]
    },
    {
      "name": "Support & on-call",
      "type": "bar",
      "stack": "share",
      "barMaxWidth": 64,
      "data": [26, 28, 30, 24]
    },
    {
      "name": "Tech debt",
      "type": "bar",
      "stack": "share",
      "barMaxWidth": 64,
      "data": [18, 20, 24, 22]
    },
    {
      "name": "Meetings",
      "type": "bar",
      "stack": "share",
      "barMaxWidth": 64,
      "data": [14, 14, 13, 14]
    }
  ]
}
```

## Data Shape

Rows are periods, series are the mixed categories, and **each column must already sum to 100**. Each series
carries an independent percentage array — there is no "stack to 100" flag, so the normalisation is data
preparation, not chart configuration.

## Key Options

| Option | Effect |
|---|---|
| `"stack": "share"` | One stack name per column; every column then fills the same height |
| `yAxis.max: 100` | Fixes the top of the scale so all columns line up exactly at the ceiling |
| `axisLabel.formatter: "{value}%"` | Declares the unit once, so per-segment "%" labels can be limited to one series |
| `label.formatter: "{c}%"` on one series only | Labeling every segment turns a mix chart into a wall of numbers; label the segment you want read |
| `barMaxWidth` | Keeps the columns from becoming wide slabs in a four-category frame |

## Pitfalls

- ❌ Columns that do not sum to 100 → ✅ pre-normalise; the chart cannot warn you about a bad denominator
- ❌ Percentages with no stated base → ✅ name the denominator ("% of tracked capacity"), otherwise the shares are unreadable
- ❌ Using this to show that total capacity grew → ✅ normalised bars deliberately hide volume; pair with a second chart if volume matters
- ❌ Labelling every segment → ✅ one labelled series plus a legend reads far faster than four labelled bands

## Alternatives

| Variant | Use instead |
|---|---|
| Absolute stacked volumes | `comparison-bars.md` |
| A single period's split with few parts | `pie-budget-share.md` |
| An unfolding mix over a long timeline | `incident-trend-stacked-area.md` |

<!-- source: ECharts option manual (series-bar stack, value-axis max/formatter) + the bar how-to note that percentage stacking is a data-side decision -->
