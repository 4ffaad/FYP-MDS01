# Bump Chart — Squad Ranking Across Quarters (ECharts)

**Best for**: tracking who moved up or down in a ranking, where the *change of position* is the story
**Avoid when**: the underlying values matter (ranks hide the gaps) or there are more than ~8 ranked lines
**Answers**: which squad climbed, which slipped, and where the lines crossed

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 840,
  "height": 440,
  "title": { "text": "Squad Ranking by Delivery Confidence", "subtext": "Rank 1 is best — position, not score", "left": "left" },
  "grid": { "left": 72, "right": 132, "top": 96, "bottom": 40 },
  "xAxis": { "type": "category", "boundaryGap": false, "data": ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"], "axisTick": { "show": false } },
  "yAxis": { "type": "category", "inverse": true, "data": ["1st", "2nd", "3rd", "4th", "5th"], "axisTick": { "show": false }, "splitLine": { "show": true } },
  "series": [
    { "name": "Core", "type": "line", "symbolSize": 13, "lineStyle": { "width": 3 }, "endLabel": { "show": true, "formatter": "{a}" }, "data": [2, 1, 1, 0, 0, 0] },
    { "name": "Search", "type": "line", "symbolSize": 13, "lineStyle": { "width": 3 }, "endLabel": { "show": true, "formatter": "{a}" }, "data": [0, 0, 2, 1, 2, 1] },
    { "name": "Identity", "type": "line", "symbolSize": 13, "lineStyle": { "width": 3 }, "endLabel": { "show": true, "formatter": "{a}" }, "data": [1, 2, 0, 2, 1, 3] },
    { "name": "Billing", "type": "line", "symbolSize": 13, "lineStyle": { "width": 3 }, "endLabel": { "show": true, "formatter": "{a}" }, "data": [3, 3, 3, 4, 3, 2] },
    { "name": "Mobile", "type": "line", "symbolSize": 13, "lineStyle": { "width": 3 }, "endLabel": { "show": true, "formatter": "{a}" }, "data": [4, 4, 4, 3, 4, 4] }
  ]
}
```

## Data Shape

The y-axis is a **category axis of rank labels**, so every series value is a category **index**, not a score:
rank 1 → `0`, rank 3 → `2`. With `inverse: true` the first category sits at the top, which is what makes rank 1 read as "best".

| Quarter | Core | Search | Identity | Billing | Mobile |
|---|---|---|---|---|---|
| Rank (1–5) | 3,2,2,1,1,1 | 1,1,3,2,3,2 | 2,3,1,3,2,4 | 4,4,4,5,4,3 | 5,5,5,4,5,5 |
| Data (index) | 2,1,1,0,0,0 | 0,0,2,1,2,1 | 1,2,0,2,1,3 | 3,3,3,4,3,2 | 4,4,4,3,4,4 |

## Key Options

| Option | Effect |
|---|---|
| `yAxis.type: "category"` + `inverse: true` | Rank 1 at the top, rank N at the bottom — the opposite of a default value axis |
| `xAxis.boundaryGap: false` | Animates the reading as a continuous race rather than a series of isolated points |
| `endLabel.show: true` | Labels the line at its last point, so the legend can stay off and the labels never collide |
| `grid.right: 132` | Room for the end labels — without it ECharts clips them off the canvas |
| `symbolSize: 13` | Position changes are the message; a visible marker at every quarter makes the crossings readable |

## Pitfalls

- ❌ Feeding real scores into a rank axis → ✅ the category axis maps numbers to positions; pre-compute ranks and convert them to indices
- ❌ Ranks with gaps (1, 2, 5) → ✅ the axis will compress them into neighbours; state ties explicitly or the crossings mislead
- ❌ More than ~8 lines → ✅ bump charts degrade fast; split into two charts or keep only the movers
- ❌ Using a bump chart to show growth → ✅ rank hides magnitude; when the sizes matter, show the values instead

## Alternatives

| Variant | Use instead |
|---|---|
| The underlying scores | `trend-line-multi-series.md` |
| Signed change between two periods | `headcount-variance-diverging-bars.md` |
| Movement of one metric's distribution | `incident-trend-stacked-area.md` |

<!-- source: ECharts option manual (category-axis index mapping, yAxis.inverse, line endLabel) + the bump-chart gallery entry -->
