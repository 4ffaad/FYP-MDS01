# Calendar Grid — Deploy Rhythm Across the Train (Vega-Lite)

**Best for**: showing a weekly rhythm and its exceptions — where the regular beats and the gaps are
**Avoid when**: the time span is long (a month is the practical limit) or the values need exact reading
**Answers**: which weekdays carry deploys, and where the train went quiet

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 420,
  "height": 210,
  "title": {"text": "Deploys by Weekday", "subtitle": "Last 6 weeks of the release train", "anchor": "start"},
  "data": {
    "values": [
      {"w": 1, "d": "Mon", "deploys": 3}, {"w": 1, "d": "Tue", "deploys": 5},
      {"w": 1, "d": "Wed", "deploys": 6}, {"w": 1, "d": "Thu", "deploys": 4},
      {"w": 1, "d": "Fri", "deploys": 2}, {"w": 1, "d": "Sat", "deploys": 0},
      {"w": 1, "d": "Sun", "deploys": 0},
      {"w": 2, "d": "Mon", "deploys": 4}, {"w": 2, "d": "Tue", "deploys": 6},
      {"w": 2, "d": "Wed", "deploys": 7}, {"w": 2, "d": "Thu", "deploys": 5},
      {"w": 2, "d": "Fri", "deploys": 3}, {"w": 2, "d": "Sat", "deploys": 0},
      {"w": 2, "d": "Sun", "deploys": 0},
      {"w": 3, "d": "Mon", "deploys": 5}, {"w": 3, "d": "Tue", "deploys": 4},
      {"w": 3, "d": "Wed", "deploys": 8}, {"w": 3, "d": "Thu", "deploys": 6},
      {"w": 3, "d": "Fri", "deploys": 4}, {"w": 3, "d": "Sat", "deploys": 1},
      {"w": 3, "d": "Sun", "deploys": 0},
      {"w": 4, "d": "Mon", "deploys": 6}, {"w": 4, "d": "Tue", "deploys": 7},
      {"w": 4, "d": "Wed", "deploys": 9}, {"w": 4, "d": "Thu", "deploys": 7},
      {"w": 4, "d": "Fri", "deploys": 5}, {"w": 4, "d": "Sat", "deploys": 0},
      {"w": 4, "d": "Sun", "deploys": 0},
      {"w": 5, "d": "Mon", "deploys": 4}, {"w": 5, "d": "Tue", "deploys": 5},
      {"w": 5, "d": "Wed", "deploys": 6}, {"w": 5, "d": "Thu", "deploys": 8},
      {"w": 5, "d": "Fri", "deploys": 6}, {"w": 5, "d": "Sat", "deploys": 0},
      {"w": 5, "d": "Sun", "deploys": 0},
      {"w": 6, "d": "Mon", "deploys": 7}, {"w": 6, "d": "Tue", "deploys": 8},
      {"w": 6, "d": "Wed", "deploys": 5}, {"w": 6, "d": "Thu", "deploys": 4},
      {"w": 6, "d": "Fri", "deploys": 3}, {"w": 6, "d": "Sat", "deploys": 0},
      {"w": 6, "d": "Sun", "deploys": 1}
    ]
  },
  "mark": {"type": "rect", "cornerRadius": 2, "stroke": null},
  "encoding": {
    "x": {"field": "w", "type": "ordinal", "title": "Week in the train", "axis": {"labelAngle": 0}},
    "y": {"field": "d", "type": "ordinal", "title": null, "sort": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]},
    "color": {"field": "deploys", "type": "quantitative", "scale": {"scheme": "blues"}, "legend": {"title": "deploys"}}
  }
}
```

## Data Shape

One row per **cell**, not per week: a `w` position, a `d` position and the measure. Zero is a real value here —
the empty weekend row is part of the finding, so never drop those rows.

## Key Options

| Option | Effect |
|---|---|
| `mark.type: "rect"` + ordinal x/y | The grid form: every combination of x and y is a box, so missing combinations read as holes |
| `y.sort` as an explicit day list | Row order is fixed by hand; the renderer disables automatic sorting, so nothing else will order the week for you |
| `axis.labelAngle: 0` | Keeps short column labels horizontal |
| `scheme: "blues"` | A sequential ramp for a sequential measure — do not use a categorical scheme here |
| `cornerRadius: 2` + `stroke: null` | Softens the cells without drawing borders that would create a grid-in-grid look |
| Keep zero rows | Dropping them removes the weekend band and hides the rhythm |

## Pitfalls

- ❌ Dropping zero-value rows → ✅ the gap *is* the insight; zero and "no row" look identical in the render, so keep the row and let the colour scale show the floor
- ❌ Using a calendar grid for a long period → ✅ beyond ~30 columns the cells become unreadable; aggregate to weeks
- ❌ Treating the colour ramp as a legend for exact values → ✅ readers match shades, they do not read numbers; label any value you will be quoted on
- ❌ A categorical colour scheme → ✅ the day/week grid encodes one measure; a rainbow destroys the ordering

## Alternatives

| Variant | Use instead |
|---|---|
| Two categorical dimensions with a third measure, sorted | `service-drift-lasagna.md` |
| Weekday × hour activity rather than a calendar | `deploy-punchcard-weekday-hour.md` |
| A single continuous series over the same weeks | `trend-line-multi-series.md` (ECharts) |

<!-- source: Vega-Lite docs (rect mark, ordinal scales, quantitative colour scales) + the table-based gallery section (annual heatmap / lasagna) -->
