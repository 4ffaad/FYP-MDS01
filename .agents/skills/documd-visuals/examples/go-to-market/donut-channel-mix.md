# Donut — Share of Total by Channel (ECharts)

**Best for**: a small number of categories where the main question is relative share of the whole
**Avoid when**: there are many slices, tiny differences matter, or the reader must compare multiple groups precisely (use bars)
**Answers**: how the total is divided, and which categories dominate the mix

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 820,
  "height": 380,
  "title": { "text": "Acquisition Mix", "subtext": "Orders by channel, current month", "left": "left" },
  "legend": { "orient": "vertical", "right": 20, "top": 96 },
  "series": [
    {
      "name": "Orders",
      "type": "pie",
      "radius": ["42%", "68%"],
      "center": ["36%", "58%"],
      "avoidLabelOverlap": true,
      "itemStyle": { "borderColor": "rgba(255,255,255,0.9)", "borderWidth": 1 },
      "label": { "show": true, "formatter": "{b}\n{d}%" },
      "labelLine": { "length": 16, "length2": 10 },
      "data": [
        { "value": 420, "name": "Web" },
        { "value": 260, "name": "Marketplace" },
        { "value": 180, "name": "Partner API" },
        { "value": 90, "name": "Inside sales" }
      ]
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `radius: [inner, outer]` | Makes the pie a donut, which improves label room and leaves a calmer centre |
| `center` | Moves the chart away from the legend so labels do not collide with it |
| `label.formatter` | Shows both name and percentage directly on the exported chart |
| `avoidLabelOverlap` | Helps keep outside labels readable when slice sizes differ |
| `itemStyle.borderWidth` | Separates adjacent slices so the segments stay distinct in static output |

## Data Shape

One `data` array of `{ name, value }` objects. Keep the category count small, because each extra slice reduces the chart's readability.

## Pitfalls

- ❌ Using a pie for ten categories → ✅ too many slices destroy comparison; switch to bars
- ❌ Tiny percentage differences presented as decisive → ✅ pie charts are approximate readers, not precision tools
- ❌ Several pies in one frame → ✅ compare categories with bars instead of forcing slice-to-slice comparisons
- ❌ Missing direct labels → ✅ static exports need the percentages on the chart, not only in hover state

## Alternatives

| Variant | Use instead |
|---|---|
| Exact category comparison | `comparison-bars.md` |
| Composition over time | Stacked bars or an area chart |
| Hierarchical share of total | `treemap` or `sunburst` |

<!-- source: ECharts option manual (series-pie) + examples gallery pie family -->