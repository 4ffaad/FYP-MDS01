# Run Rate Waterfall — Where the Savings Came From (ECharts)

**Best for**: a budget or cost walk from one total to another, showing which items pushed the number down or up
**Avoid when**: the items are independent measures (plain bars) or the order of the steps is arbitrary
**Answers**: how the opening run rate turned into the closing run rate, item by item

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 880,
  "height": 420,
  "title": { "text": "Run Rate Walk: Q2 → Q3", "subtext": "Cost reductions and one increase, in kUSD per month", "left": "left" },
  "legend": { "data": ["Opening / closing", "Savings", "Increase"], "top": 8, "right": 8 },
  "grid": { "left": 72, "right": 32, "top": 96, "bottom": 56 },
  "xAxis": { "type": "category", "data": ["Run rate Q2", "Vendor renegotiation", "Cloud commitment", "Headcount freeze", "Automation", "Run rate Q3"], "axisLabel": { "interval": 0, "rotate": 18 } },
  "yAxis": { "type": "value", "name": "kUSD / month", "nameLocation": "end", "nameGap": 14 },
  "series": [
    {
      "name": "Opening / closing",
      "type": "bar",
      "stack": "walk",
      "barMaxWidth": 54,
      "label": { "show": true, "position": "top" },
      "data": [420, 0, 0, 0, 0, 290]
    },
    {
      "name": "Base",
      "type": "bar",
      "stack": "walk",
      "barMaxWidth": 54,
      "silent": true,
      "itemStyle": { "opacity": 0 },
      "data": [0, 360, 325, 245, 245, 0]
    },
    {
      "name": "Savings",
      "type": "bar",
      "stack": "walk",
      "barMaxWidth": 54,
      "label": { "show": true, "position": "top", "formatter": "-{c}" },
      "data": [0, 60, 35, 80, 0, 0]
    },
    {
      "name": "Increase",
      "type": "bar",
      "stack": "walk",
      "barMaxWidth": 54,
      "label": { "show": true, "position": "top", "formatter": "+{c}" },
      "data": [0, 0, 0, 0, 45, 0]
    }
  ]
}
```

## Data Shape

Every step is written as **base + height**, not as a signed delta:

| Step | Base (invisible) | Height (visible) |
|---|---|---|
| Opening total | 0 | 420 |
| −60 (420 → 360) | 360 | 60 |
| −35 (360 → 325) | 325 | 35 |
| −80 (325 → 245) | 245 | 80 |
| +45 (245 → 290) | 245 | 45 |
| Closing total | 0 | 290 |

Compute the running total once, then emit two parallel arrays. The base series carries the running total, the
delta series carries the step height.

## Key Options

| Option | Effect |
|---|---|
| `itemStyle.opacity: 0` on the base series | Makes the invisible pedestal — the trick that turns stacked bars into a waterfall |
| `"silent": true` on the base series | Keeps the invisible series from reacting to hover, so previews do not highlight a phantom bar |
| `legend.data` without "Base" | Hides the technical series from the legend while keeping it in the chart |
| `formatter: "-{c}"` / `"+{c}"` | A string template (not a callback) that labels the signed step while the stored value stays positive |
| `barMaxWidth` on every step | Without it the opening/closing bars and the steps render at different widths when categories change |

## Pitfalls

- ❌ Writing signed deltas and letting ECharts stack them → ✅ stacking always grows upward; the base must carry the running total
- ❌ Making the base series `null` → ✅ `null` does not keep the pedestal stable; use literal `0` values
- ❌ Colouring every step the same → ✅ openings closings, decreases and increases are three different readings — keep them as three series
- ❌ Reordering the steps into "biggest saving first" → ✅ a waterfall is a sequence; its order is part of the arithmetic

## Alternatives

| Variant | Use instead |
|---|---|
| Independent budget items with no running total | `comparison-bars.md` |
| Signed variance without accumulation | `headcount-variance-diverging-bars.md` |
| Share of a fixed total | `pie-budget-share.md` |

<!-- source: ECharts option manual (series-bar stack / itemStyle / label template) + bar how-to (waterfall variant) -->
