# Effect Scatter — Outlier Alerts on a Risk/Impact Plane (ECharts)

**Best for**: highlighting a small number of important points among a broader scatter when a static export still needs the standout items to read first
**Avoid when**: you have many points or rely on animated ripple as the main signal
**Answers**: which items are the true outliers, and where the highest-priority cases sit in the field

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 860,
  "height": 400,
  "title": { "text": "Outlier Alerts", "subtext": "Risk vs business impact", "left": "left" },
  "grid": { "left": 68, "right": 36, "top": 112, "bottom": 42 },
  "xAxis": { "type": "value", "min": 0, "max": 10 },
  "yAxis": { "type": "value", "min": 0, "max": 10 },
  "series": [
    {
      "type": "scatter",
      "symbolSize": 10,
      "itemStyle": { "color": "#2b66c4", "opacity": 0.8 },
      "data": [
        [2.2, 4.1], [3.4, 5.0], [4.0, 3.2], [5.2, 6.1], [6.1, 5.7], [3.8, 7.2],
        [5.8, 4.6], [6.9, 6.8], [4.7, 5.4], [2.8, 3.6], [7.4, 4.8], [5.0, 7.0]
      ]
    },
    {
      "type": "effectScatter",
      "symbolSize": 16,
      "showEffectOn": "emphasis",
      "rippleEffect": { "scale": 2.0, "brushType": "stroke" },
      "itemStyle": { "color": "#7048e8" },
      "label": {
        "show": true,
        "position": "top",
        "formatter": "{@[2]}"
      },
      "data": [
        [8.8, 8.7, "Gateway"],
        [7.9, 9.1, "Billing"],
        [9.2, 7.6, "Search"]
      ]
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `effectScatter` | Highlights important points more aggressively than a plain scatter |
| `showEffectOn` | Controls when the emphasis effect appears; static exports still keep the highlighted points larger and labelled |
| `rippleEffect` | Controls how far the emphasis reaches around the highlighted point |
| `label.show` | Names the exceptional points directly in the export |
| Separate `scatter` + `effectScatter` series | Keeps the background population distinct from the alert points |

## Data Shape

Background points are simple `[x, y]` pairs. Highlighted points can carry an extra third field used by the label formatter, here a short name.

## Pitfalls

- ❌ Too many effect points → ✅ once everything pulses, nothing stands out
- ❌ Depending on ripple animation for interpretation → ✅ in static exports, labels and symbol contrast still have to identify the important items
- ❌ Using effectScatter for dense clouds → ✅ use a plain scatter or a heatmap when the field is crowded
- ❌ No axis bounds → ✅ set `min`/`max` so outliers keep their positional meaning across exports

## Alternatives

| Variant | Use instead |
|---|---|
| All points matter equally | `scatter-segment-correlation.md` |
| Categorical severity comparison | `comparison-bars.md` |
| 2D density over ordered axes | `heatmap-incident-load.md` |

<!-- source: ECharts option manual (series-effectScatter / rippleEffect) + examples gallery scatter family -->