# Radial Bars — Support Volume Around the Clock (ECharts)

**Best for**: a cyclic category axis (hours, weekdays, shifts) where "around the clock" is part of the message
**Avoid when**: the categories have no natural cycle, or precise comparison between adjacent values is required
**Answers**: which two-hour bands carry the load, and how sharply the peak stands out

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 720,
  "height": 560,
  "title": { "text": "Support Tickets by Two-Hour Band", "subtext": "Median weekday load, last 30 days", "left": "left" },
  "polar": { "radius": ["26%", "70%"], "center": ["50%", "56%"] },
  "angleAxis": { "type": "category", "startAngle": 90, "data": ["00", "02", "04", "06", "08", "10", "12", "14", "16", "18", "20", "22"], "axisLabel": { "interval": 0 } },
  "radiusAxis": { "type": "value", "min": 0, "name": "tickets", "nameGap": 8 },
  "series": [
    {
      "name": "Tickets",
      "type": "bar",
      "coordinateSystem": "polar",
      "barWidth": "52%",
      "roundCap": true,
      "label": { "show": true, "position": "middle" },
      "data": [4, 3, 2, 3, 12, 26, 31, 29, 24, 18, 11, 7]
    }
  ]
}
```

## Data Shape

One value per cyclic slot, in cycle order. Twelve two-hour bands start at 00 and close at 22 — the axis wraps,
so the first and last bars are neighbours on the circle even though they are far apart in the array.

## Key Options

| Option | Effect |
|---|---|
| `coordinateSystem: "polar"` | Moves the bar series onto the polar system; the radius axis becomes the value axis |
| `angleAxis.type: "category"` + `startAngle: 90` | Puts the first band at twelve o'clock and walks the cycle clockwise |
| `polar.radius: ["26%", "70%"]` | Leaves the middle free for the axis name and keeps labels off the outer edge |
| `barWidth: "52%"` | Percentage widths scale with the sector, so the bars stay proportional at any canvas size |
| `roundCap: true` | Rounds the outer end of each radial bar — a polar-bar-only option that softens dense rings |
| `radiusAxis.min: 0` | Radial length must start at the centre; a non-zero minimum would falsify every comparison |

## Pitfalls

- ❌ Reading radial lengths as areas → ✅ the outer bands sweep more arc per unit, so a bar's area grows faster than its value
- ❌ More than ~20 cyclic slots → ✅ the ring becomes unreadable; bucket the bands or switch to a line chart
- ❌ Using a polar bar chart for non-cyclic categories → ✅ the only thing the circle buys you is the cycle; without it a bar chart wins
- ❌ Forgetting `angleAxis.axisLabel.interval: 0` → ✅ ECharts hides overlapping tick labels by default and will silently drop hour bands

## Alternatives

| Variant | Use instead |
|---|---|
| The same values as a ranked list | `comparison-bars.md` |
| Share of a few slices | `pie-budget-share.md` |
| Change over time rather than around the clock | `trend-line-multi-series.md` |

<!-- source: ECharts option manual (polar / radiusAxis / angleAxis / series-bar coordinateSystem, roundCap, barWidth) -->
