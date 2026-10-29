# Range Band — Throughput With a Percentile Envelope (ECharts)

**Best for**: a trend line that needs an honest uncertainty or variation envelope around it
**Avoid when**: the band has no defined meaning, or the reader only needs the point estimate
**Answers**: what the typical volume was, and how wide the week-to-week spread ran around it

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 880,
  "height": 420,
  "title": { "text": "Merged Pull Requests With Spread", "subtext": "Median line with a 25th–75th percentile band", "left": "left" },
  "legend": { "data": ["25th–75th percentile", "Median"], "top": 8, "right": 8 },
  "grid": { "left": 72, "right": 40, "top": 96, "bottom": 44 },
  "xAxis": { "type": "category", "boundaryGap": false, "data": ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9", "W10"] },
  "yAxis": { "type": "value", "name": "PRs / week", "nameLocation": "end", "nameGap": 14 },
  "series": [
    {
      "name": "Base",
      "type": "line",
      "stack": "band",
      "symbol": "none",
      "silent": true,
      "lineStyle": { "opacity": 0 },
      "areaStyle": { "opacity": 0 },
      "data": [28, 31, 26, 33, 30, 35, 29, 32, 34, 31]
    },
    {
      "name": "25th–75th percentile",
      "type": "line",
      "stack": "band",
      "symbol": "none",
      "silent": true,
      "lineStyle": { "opacity": 0 },
      "areaStyle": { "opacity": 0.22 },
      "data": [24, 18, 30, 20, 28, 25, 26, 25, 25, 23]
    },
    {
      "name": "Median",
      "type": "line",
      "symbolSize": 7,
      "lineStyle": { "width": 3 },
      "label": { "show": true, "position": "top", "formatter": "{c}" },
      "data": [39, 40, 39, 43, 42, 44, 41, 43, 44, 42]
    }
  ]
}
```

## Data Shape

Three parallel arrays per period — lower bound, median, upper bound — plus one derived array:

| Array | W1 | W2 | W3 | … | Role |
|---|---|---|---|---|---|
| Lower (25th) | 28 | 31 | 26 | | Invisible stack base |
| Median | 39 | 40 | 39 | | Visible line, unstacked |
| Upper (75th) | 52 | 49 | 56 | | Used only to derive the span |
| Span = upper − lower | 24 | 18 | 30 | | Visible stack segment (the band) |

## Key Options

| Option | Effect |
|---|---|
| Lower series with `areaStyle.opacity: 0` | Draws nothing but still lifts the stacked band to the lower bound |
| Span series with `stack: "band"` | The fill spans exactly from lower to upper — the standard band trick |
| `lineStyle.opacity: 0` on both helper series | Leaves only the band; the helper edges should not read as data lines |
| `"silent": true` | Keeps the technical series out of hover and legend interactions |
| Median series left unstacked | A stacked median would be drawn relative to the band, not to the axis |
| `areaStyle.opacity: 0.22` | A band is context, not data — keep it faint enough that the median line stays dominant |

## Pitfalls

- ❌ Stacking the median together with the band → ✅ the median must stay on its own axis scale; only the band helpers share a stack name
- ❌ Naming the helpers in the legend → ✅ "Base" and the raw span array are artefacts; name only the band and the median
- ❌ A band without a stated meaning → ✅ say "25th–75th percentile" or "forecast range" in the subtitle; an unexplained envelope is noise
- ❌ Using `areaStyle` opacity 1 → ✅ opaque fills hide the grid and each other; bands belong at low alpha

## Alternatives

| Variant | Use instead |
|---|---|
| A single interval per category | `team-variance-interval.md` (Vega-Lite) |
| Mean and standard deviation as whiskers | `boxplot-latency-distribution.md` |
| Two lines without a band | `trend-line-multi-series.md` |

<!-- source: ECharts option manual (series-line stack + areaStyle) combined with the documented confidence-band technique used across ECharts examples -->
