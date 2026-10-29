# Stacked Area — Incident Mix Over Time (ECharts)

**Best for**: showing a total that moves over time while keeping the composition visible underneath
**Avoid when**: the categories are not part of a common total, or the reader needs to compare middle series precisely
**Answers**: whether the incident load is rising, and which severity class is driving the change

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 860,
  "height": 400,
  "title": { "text": "Incident Load by Severity", "subtext": "Weekly counts, stacked so the total and the mix are both visible", "left": "left" },
  "legend": { "data": ["Sev1", "Sev2", "Sev3"], "top": 8, "right": 8 },
  "grid": { "left": 64, "right": 40, "top": 96, "bottom": 40 },
  "xAxis": { "type": "category", "boundaryGap": false, "data": ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9", "W10"] },
  "yAxis": { "type": "value", "name": "incidents / week", "nameLocation": "end", "nameGap": 14 },
  "series": [
    {
      "name": "Sev1",
      "type": "line",
      "stack": "incidents",
      "smooth": 0.25,
      "symbol": "none",
      "lineStyle": { "width": 1 },
      "areaStyle": { "opacity": 0.55 },
      "data": [2, 1, 3, 2, 4, 2, 1, 2, 3, 1]
    },
    {
      "name": "Sev2",
      "type": "line",
      "stack": "incidents",
      "smooth": 0.25,
      "symbol": "none",
      "lineStyle": { "width": 1 },
      "areaStyle": { "opacity": 0.4 },
      "data": [5, 6, 4, 7, 6, 5, 8, 6, 5, 4]
    },
    {
      "name": "Sev3",
      "type": "line",
      "stack": "incidents",
      "smooth": 0.25,
      "symbol": "none",
      "lineStyle": { "width": 1 },
      "areaStyle": { "opacity": 0.28 },
      "data": [9, 11, 8, 12, 10, 13, 11, 9, 10, 12]
    }
  ]
}
```

## Data Shape

One row per period, one series per component, values in the same unit. Stacking is declared by the matching
`stack` name — the series order in the array is the stacking order from bottom to top.

## Key Options

| Option | Effect |
|---|---|
| `type: "line"` + `areaStyle` | An area chart is a line chart with a filled baseline; `stack` turns the fills into bands |
| `stack: "incidents"` | Makes each band sit on the previous one instead of covering it |
| `areaStyle.opacity` | Layered fill alpha; without it the bands are flat and the top band hides the lower edges |
| `xAxis.boundaryGap: false` | Removes the half-category padding so the first and last periods touch the axis ends — required for a continuous time reading |
| `smooth: 0.25` | A slight monotone-ish curve; large values overshoot, so keep it small or omit it |
| `symbol: "none"` | Ten periods times three series is 30 markers — the area already carries the data |

## Pitfalls

- ❌ Smoothing a stacked area heavily → ✅ interpolated curves can dip below zero and invent volume; keep `smooth` low
- ❌ Reading the middle band's height as its absolute value → ✅ only the bottom band sits on a flat baseline; every other band is read as a thickness
- ❌ Mixing units across bands → ✅ a stack is only meaningful when all bands share one unit
- ❌ Stacking series that overlap in meaning (e.g. "open" and "closed") → ✅ stacked areas show parts of a whole, not two measures

## Alternatives

| Variant | Use instead |
|---|---|
| The same mix without a running total | `trend-line-multi-series.md` |
| Composition of a fixed total rather than over time | `engineering-time-100pct-bars.md` |
| Topics flowing in and out of the conversation | `themeriver-topic-attention.md` |

<!-- source: ECharts option manual (series-line stack / areaStyle / smooth / boundaryGap) + the stacked-area and gradient-area gallery entries -->
