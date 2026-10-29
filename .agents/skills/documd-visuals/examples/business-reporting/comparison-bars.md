# Comparison Bars — Grouped, Stacked, and Sorted (ECharts)

**Best for**: comparing categories across one or two dimensions — sides, products, periods, regions
**Avoid when**: the categories are few and the message is share-of-total (use a pie/donut) or the values form a trend
**Answers**: which category wins, and (when stacked) how each total is composed

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 820,
  "height": 380,
  "title": { "text": "Sales by Product and Channel", "subtext": "Stacked by channel, sorted by total", "left": "left" },
  "tooltip": { "trigger": "axis", "axisPointer": { "type": "shadow" } },
  "legend": { "data": ["Online", "Retail", "Partner"], "top": 8, "right": 8 },
  "grid": { "left": 72, "right": 24, "top": 92, "bottom": 32 },
  "xAxis": { "type": "category", "data": ["Shirts", "Heels", "Trousers", "Socks", "Cardigans"] },
  "yAxis": { "type": "value", "name": "units", "nameLocation": "end", "nameGap": 12 },
  "series": [
    {
      "name": "Online",
      "type": "bar",
      "stack": "total",
      "barMaxWidth": 48,
      "itemStyle": { "borderRadius": [0, 0, 0, 0] },
      "data": [90, 132, 134, 101, 120]
    },
    {
      "name": "Retail",
      "type": "bar",
      "stack": "total",
      "data": [290, 182, 234, 191, 220]
    },
    {
      "name": "Partner",
      "type": "bar",
      "stack": "total",
      "data": [190, 232, 154, 201, 150]
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `"stack": "total"` | Stacks all series that share the stack name; remove it to get grouped bars |
| `barMaxWidth` / `barWidth` | Prevents bars from becoming slabs on wide charts (and keeps them visible when narrow) |
| `itemStyle.borderRadius` | Rounds bar corners; use `[0,0,0,0]` for a crisp business look |
| `axisPointer: { type: "shadow" }` | Highlights the whole category on hover (preview only — exports are static) |
| `label.formatter: "total"` | Only valid on the top-most stacked series; put it there, not on every series |
| Sorting | Sort the **data arrays together** (and the `xAxis.data`) — ECharts has no declarative sort |

## Data Shape

One `xAxis.data` array of categories, one `series` per series with parallel `data` arrays. For a sorted view,
sort all arrays by the total before writing the JSON.

## Pitfalls

- ❌ Stacking series with different units → ✅ only stack comparable measures; mixed units belong in grouped bars
- ❌ Stacked bars summing to 100% silently → ✅ label the axis as "%" if values are normalised
- ❌ Relying on `tooltip` for the totals → ✅ stacked comparisons need visible totals (label) because exports are static
- ❌ Unequal category spacing (`barCategoryGap` per series) → ✅ in one cartesian system these gaps are shared; set them on the last bar series only

## Alternatives

| Variant | Use instead |
|---|---|
| Share of total for few categories | Pie/donut (or a stacked single bar) |
| Positive and negative contributions | Waterfall (`custom` series or a vega-lite transform) |
| Many categories | Horizontal bars (`yAxis.type: "category"`) or a table |

<!-- source: ECharts option manual (series-bar stack / barMaxWidth / label) + the bar how-to (barGap sharing note) -->
