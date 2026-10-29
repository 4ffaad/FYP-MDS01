# Threshold Bands — Release Readiness Score (ECharts)

**Best for**: putting every value in front of a shared, named decision rule instead of a bare number
**Avoid when**: the thresholds are arbitrary, or the exact value per category is the only thing that matters
**Answers**: which services clear the release gate, which need watching, and which must not ship

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 860,
  "height": 440,
  "title": { "text": "Release Readiness by Service", "subtext": "Gate at 90 — bands mark ready / watch / at risk", "left": "left" },
  "grid": { "left": 96, "right": 48, "top": 104, "bottom": 40 },
  "xAxis": { "type": "category", "data": ["api", "search", "billing", "identity", "mobile", "platform"], "axisTick": { "show": false } },
  "yAxis": { "type": "value", "min": 0, "max": 100, "name": "readiness score", "nameLocation": "end", "nameGap": 16 },
  "series": [
    {
      "name": "Readiness",
      "type": "bar",
      "barMaxWidth": 46,
      "label": { "show": true, "position": "top" },
      "data": [92, 78, 64, 88, 71, 95],
      "markArea": {
        "silent": true,
        "itemStyle": { "opacity": 0.1 },
        "label": { "position": "insideTop", "fontSize": 11 },
        "data": [
          [ { "yAxis": 90, "name": "Release ready" }, { "yAxis": 100 } ],
          [ { "yAxis": 70 }, { "yAxis": 90, "name": "Watch" } ],
          [ { "yAxis": 0, "name": "At risk" }, { "yAxis": 70 } ]
        ]
      },
      "markLine": {
        "silent": true,
        "symbol": "none",
        "lineStyle": { "type": "dashed" },
        "data": [ { "yAxis": 90, "label": { "formatter": "gate · 90" } } ]
      },
      "markPoint": {
        "symbolSize": 44,
        "data": [ { "type": "min", "name": "Lowest" }, { "type": "max", "name": "Best" } ]
      }
    }
  ]
}
```

## Data Shape

One value per category against a **fixed, shared scale** (`min: 0`, `max: 100`). The thresholds live in
`markArea`/`markLine` as `yAxis` coordinates, so they are drawn behind the bars instead of being baked into
the data.

| Layer | Purpose |
|---|---|
| `markArea` | Shades the decision bands across the full category width and names them |
| `markLine` | A single hard gate line at 90 with an inline label |
| `markPoint` | Calls out the best and worst category so the reader does not have to scan |

## Key Options

| Option | Effect |
|---|---|
| `markArea.data` as `[{yAxis}, {yAxis}]` pairs | Each pair defines one horizontal band spanning every category |
| `markArea.label.position: "insideTop"` | Puts the band name at the top of each shaded stripe, out of the bars' way |
| `itemStyle.opacity: 0.1` | Bands are annotations; anything stronger competes with the bars |
| `"silent": true` on all three marks | Annotation layers should not react to hover — the bars own the interaction |
| `yAxis.min` / `yAxis.max` pinned | Readiness scores only compare meaningfully on a fixed 0–100 scale |

## Pitfalls

- ❌ Coding the colour into each bar instead of using bands → ✅ an explicit band says *why* a value is bad; a coloured bar only says *that* it is
- ❌ Drawn thresholds that disagree with the copy → ✅ the gate number appears in the subtitle, the mark line and the band label — keep all three in sync
- ❌ `markPoint` on every category → ✅ best/worst only; a callout on each bar is noise
- ❌ Bands that overlap → ✅ a value can belong to exactly one band, otherwise the reader cannot classify it

## Alternatives

| Variant | Use instead |
|---|---|
| A single KPI against its target | `gauge-sla-attainment.md` |
| Attainment track rather than thresholds | `goal-attainment-background-bars.md` |
| A trend crossing a threshold over time | `threshold-breach-annotation.md` (Vega-Lite) |

<!-- source: ECharts option manual (series-bar markArea / markLine / markPoint, yAxis min-max) + the markArea gallery usage -->
