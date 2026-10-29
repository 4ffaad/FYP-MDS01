# Attainment Track — Goal Bars With a Background (ECharts)

**Best for**: a goal-versus-actual list where each row should read as "how much of the target is filled"
**Avoid when**: there is no shared target scale, or the rows have wildly different targets that need showing
**Answers**: which squads are close to their goal, and how much track is still empty

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 840,
  "height": 420,
  "title": { "text": "Monthly Goal Attainment", "subtext": "Bar = delivered, track = the stretch goal (axis max = 100%)", "left": "left" },
  "grid": { "left": 112, "right": 56, "top": 100, "bottom": 40 },
  "xAxis": { "type": "value", "min": 0, "max": 100, "name": "% of stretch goal", "nameLocation": "end", "nameGap": 16, "axisLabel": { "formatter": "{value}%" } },
  "yAxis": { "type": "category", "data": ["Squad A", "Squad B", "Squad C", "Squad D"], "axisTick": { "show": false } },
  "series": [
    {
      "name": "Delivered",
      "type": "bar",
      "barMaxWidth": 26,
      "showBackground": true,
      "backgroundStyle": { "opacity": 0.16, "borderRadius": 4 },
      "itemStyle": { "borderRadius": 4 },
      "label": { "show": true, "position": "right", "formatter": "{c}%" },
      "data": [93, 71, 58, 84]
    }
  ]
}
```

## Data Shape

One percentage per category, 0–100, **relative to each row's own goal**. The background track is not extra
data: it is the axis itself, so `xAxis.max` must equal the goal (100) for the empty track to mean "remaining".

## Key Options

| Option | Effect |
|---|---|
| `showBackground: true` | Draws the full-depth track behind every bar — a bar-series option, no extra series needed |
| `backgroundStyle.opacity` | Keeps the track visible but clearly secondary in both light and dark themes |
| `xAxis.max: 100` | The track length *is* the goal; changing the max silently changes what "full" means |
| `label.position: "right"` | The value sits outside the bar end, so it never overlaps the track |
| `barMaxWidth` | Prevents the rows from becoming thick slabs when there are only four categories |

## Pitfalls

- ❌ Treating the track as a target marker when the axis is auto-scaled → ✅ the background always fills to the axis maximum; pin `max` to the goal or the visual claim is false
- ❌ Rows with different goals sharing one axis max → ✅ if the goals differ, convert each row to "% of its own goal" and say so in the subtitle
- ❌ Overlapping a second bar series for "target" → ✅ a background plus a second bar produces a muddy double-encode; pick one
- ❌ Values above the axis max → ✅ ECharts clips them; leave headroom when over-achievement is expected

## Alternatives

| Variant | Use instead |
|---|---|
| Explicit target line per category | `target-attainment-bullet.md` (Vega-Lite) |
| Named threshold bands | `delivery-score-threshold-bands.md` |
| A single KPI dial | `gauge-sla-attainment.md` |

<!-- source: ECharts option manual (series-bar showBackground / backgroundStyle, value-axis min-max) -->
