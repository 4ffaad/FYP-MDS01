# Calendar Heatmap — Release Pace by Day (ECharts)

**Best for**: daily activity over a long period where the shape of busy weeks and quiet gaps matters more than a continuous line
**Avoid when**: the period is short or the reader needs a precise trend line (use a line chart)
**Answers**: which weeks spike, whether work is regular or bursty, and where extended idle periods appear

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 920,
  "height": 300,
  "title": { "text": "Release Pace Calendar", "subtext": "Deployments per day, Q2 2026", "left": "left" },
  "visualMap": {
    "min": 0,
    "max": 8,
    "orient": "horizontal",
    "left": "center",
    "bottom": 8,
    "calculable": false
  },
  "calendar": {
    "top": 84,
    "left": 48,
    "right": 24,
    "cellSize": [20, 20],
    "range": "2026-04",
    "yearLabel": { "show": false },
    "monthLabel": { "nameMap": "en" },
    "dayLabel": { "firstDay": 1, "nameMap": "en" }
  },
  "series": [
    {
      "type": "heatmap",
      "coordinateSystem": "calendar",
      "data": [
        ["2026-04-01", 2], ["2026-04-02", 1], ["2026-04-03", 3], ["2026-04-06", 4], ["2026-04-07", 2], ["2026-04-08", 5], ["2026-04-09", 1], ["2026-04-10", 2],
        ["2026-04-13", 3], ["2026-04-14", 2], ["2026-04-15", 4], ["2026-04-16", 3], ["2026-04-17", 1], ["2026-04-20", 5], ["2026-04-21", 6], ["2026-04-22", 3],
        ["2026-04-23", 2], ["2026-04-24", 1], ["2026-04-27", 2], ["2026-04-28", 2], ["2026-04-29", 3], ["2026-04-30", 4]
      ]
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `calendar.range` | Defines the visible date window; month-sized ranges export cleanly |
| `coordinateSystem: "calendar"` | Tells the heatmap series to use the calendar grid instead of cartesian axes |
| `cellSize` | Makes daily cells large enough to read in static output |
| `dayLabel.firstDay` | Aligns the week to the locale or reporting convention |
| `visualMap` | Keeps the daily intensity scale explicit |

## Data Shape

Each point is `[dateString, value]`, with ISO-like dates such as `YYYY-MM-DD`. Missing dates simply render as empty cells, which is often exactly what you want for activity calendars.

## Pitfalls

- ❌ Cramming multiple months into a tiny frame → ✅ calendar charts need enough cell size to read weekly structure
- ❌ Using it for short time ranges → ✅ a line or bar chart is clearer when there are only a few days or weeks
- ❌ No `visualMap` legend → ✅ readers need the scale to distinguish moderate activity from extreme activity
- ❌ Treating missing dates as zeros silently → ✅ be clear whether blank means “no event” or “no data”

## Alternatives

| Variant | Use instead |
|---|---|
| Hour-by-day density | `heatmap-incident-load.md` |
| Weekly/monthly trend | `trend-line-multi-series.md` |
| Hierarchical composition | `sunburst-lifecycle-share.md` |

<!-- source: ECharts option manual (calendar coordinate system / heatmap on calendar) + examples gallery calendar family -->