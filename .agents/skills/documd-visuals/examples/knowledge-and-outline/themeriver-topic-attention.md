# ThemeRiver — Topic Attention Over Time (ECharts)

**Best for**: showing how several categories wax and wane over time as a combined stream rather than as separate stacked bars
**Avoid when**: exact values matter more than rhythm, or the reader must compare many discrete timestamps precisely
**Answers**: which themes dominate at different periods, and how the composition shifts over time

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 900,
  "height": 360,
  "title": { "text": "Topic Attention Over Time", "subtext": "Weekly issue volume by theme", "left": "left" },
  "singleAxis": {
    "top": 96,
    "bottom": 40,
    "type": "time"
  },
  "series": [
    {
      "type": "themeRiver",
      "label": { "show": false },
      "emphasis": { "focus": "series" },
      "data": [
        ["2026-04-01", 12, "Platform"],
        ["2026-04-08", 16, "Platform"],
        ["2026-04-15", 18, "Platform"],
        ["2026-04-22", 14, "Platform"],
        ["2026-04-29", 11, "Platform"],

        ["2026-04-01", 8, "Support"],
        ["2026-04-08", 10, "Support"],
        ["2026-04-15", 15, "Support"],
        ["2026-04-22", 18, "Support"],
        ["2026-04-29", 12, "Support"],

        ["2026-04-01", 5, "Security"],
        ["2026-04-08", 7, "Security"],
        ["2026-04-15", 6, "Security"],
        ["2026-04-22", 9, "Security"],
        ["2026-04-29", 10, "Security"],

        ["2026-04-01", 4, "Data"],
        ["2026-04-08", 6, "Data"],
        ["2026-04-15", 9, "Data"],
        ["2026-04-22", 7, "Data"],
        ["2026-04-29", 8, "Data"]
      ]
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `series.type: "themeRiver"` | Encodes changing composition as flowing bands around a central baseline |
| `singleAxis.type: "time"` | Gives the stream an ordered temporal axis |
| `[date, value, name]` data rows | Supplies time, magnitude, and theme in one compact structure |
| `top` / `bottom` | Reserves room for the title and axis in a compact export |
| `emphasis.focus` | Helps preview interaction while the static export still reads from band shape |

## Data Shape

Each row is `[time, value, category]`. Repeated timestamps across categories form the stacked flowing composition for that period.

## Pitfalls

- ❌ Expecting exact per-point comparison → ✅ themeRiver is about rhythm and changing composition, not precise lookup
- ❌ Too many categories → ✅ once the stream becomes ribbon noise, use stacked areas or bars instead
- ❌ Irregular timestamps with missing categories unexamined → ✅ gaps can distort the visual rhythm if the data is patchy
- ❌ Using it for non-temporal categories → ✅ this view assumes an ordered time axis

## Alternatives

| Variant | Use instead |
|---|---|
| Exact trend lines by series | `trend-line-multi-series.md` |
| Daily density by calendar cell | `calendar-release-pace.md` |
| Part-to-whole at one point in time | `pie-budget-share.md` |

<!-- source: ECharts option manual (series-themeRiver / singleAxis) + examples gallery themeRiver family -->