# Pie — Budget Share by Workstream (ECharts)

**Best for**: a small number of categories where the message is share of total rather than exact ranked comparison
**Avoid when**: there are many slices, tiny differences matter, or the reader needs precise comparisons (use bars)
**Answers**: how the whole is divided, and which categories dominate the total

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 820,
  "height": 380,
  "title": { "text": "Budget Share by Workstream", "subtext": "Quarterly operating budget", "left": "left" },
  "legend": { "orient": "vertical", "right": 24, "top": 84 },
  "series": [
    {
      "type": "pie",
      "radius": ["0%", "62%"],
      "center": ["38%", "58%"],
      "avoidLabelOverlap": true,
      "label": { "formatter": "{b}\n{d}%", "fontSize": 11 },
      "labelLine": { "length": 16, "length2": 12 },
      "data": [
        { "value": 36, "name": "Platform" },
        { "value": 24, "name": "Customer Ops" },
        { "value": 18, "name": "Security" },
        { "value": 12, "name": "Data" },
        { "value": 10, "name": "Enablement" }
      ]
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `series.type: "pie"` | Encodes part-to-whole share as slice angle |
| `radius` / `center` | Controls pie size and reserves room for labels and legend |
| `label.formatter` | Makes the static export self-explanatory without hover |
| `avoidLabelOverlap` | Helps keep small-slice labels readable |
| `legend` | Useful when the reader needs color/category lookup at a glance |

## Data Shape

One `data` array of `{ name, value }` objects. Keep the slice count small, because pie charts become unreadable quickly as categories multiply.

## Pitfalls

- ❌ Too many slices → ✅ once the pie turns into slivers, use bars instead
- ❌ Comparing near-equal values by angle → ✅ bars are better for exact comparison
- ❌ Missing labels in static output → ✅ include percent or value directly on the chart
- ❌ Using pie for hierarchy → ✅ use `sunburst` or `treemap` when nesting matters

## Alternatives

| Variant | Use instead |
|---|---|
| Few categories, hole for center KPI | `donut-channel-mix.md` |
| Exact comparison by category | `comparison-bars.md` |
| Hierarchical share of total | `sunburst-lifecycle-share.md` |

<!-- source: ECharts option manual (series-pie) + examples gallery pie family -->