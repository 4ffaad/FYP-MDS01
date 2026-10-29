# Variance Diverging Bars — Headcount Versus Plan (ECharts)

**Best for**: a signed variance list where direction (over plan / under plan) is the message
**Avoid when**: every value shares one sign, or the reader needs absolute totals rather than deltas
**Answers**: which teams are over plan, which are under, and how far each one missed

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 840,
  "height": 400,
  "title": { "text": "Headcount Variance vs Plan", "subtext": "Q3 close — below plan (left) / above plan (right)", "left": "left" },
  "legend": { "data": ["Below plan", "Above plan"], "top": 8, "right": 8 },
  "grid": { "left": 112, "right": 48, "top": 96, "bottom": 36 },
  "xAxis": { "type": "value", "name": "people vs plan", "nameLocation": "end", "nameGap": 14 },
  "yAxis": { "type": "category", "data": ["Data", "Platform", "Mobile", "Identity", "Search"], "axisTick": { "show": false } },
  "series": [
    {
      "name": "Below plan",
      "type": "bar",
      "stack": "variance",
      "barMaxWidth": 22,
      "label": { "show": true, "position": "left" },
      "data": [
        { "value": -6 },
        { "value": -2 },
        { "value": 0, "label": { "show": false } },
        { "value": 0, "label": { "show": false } },
        { "value": 0, "label": { "show": false } }
      ]
    },
    {
      "name": "Above plan",
      "type": "bar",
      "stack": "variance",
      "barMaxWidth": 22,
      "label": { "show": true, "position": "right" },
      "data": [
        { "value": 0, "label": { "show": false } },
        { "value": 0, "label": { "show": false } },
        { "value": 1 },
        { "value": 4 },
        { "value": 7 }
      ]
    }
  ]
}
```

## Data Shape

One signed number per category. Split the values into two series — negatives in one, positives in the other — so
each direction gets its own theme colour without writing a colour function (ECharts option must stay pure JSON).

## Key Options

| Option | Effect |
|---|---|
| `"stack": "variance"` | Both series share one slot, so bars grow left and right from zero instead of being placed side by side |
| Per-item `label.show: false` | Hides the "0" label that the opposite-series placeholder would otherwise print |
| `label.position: "left"` / `"right"` | Labels sit outside the bar end, so the sign is never hidden behind the bar |
| Two series instead of one | Gives the two directions distinct series colours and a readable legend, with no colour callback |
| `xAxis.type: "value"` | The zero baseline must be a value axis — a category axis cannot express sign |

## Pitfalls

- ❌ One series with mixed signs and a `formatter` callback → ✅ ECharts options here are pure JSON; split by sign across two series
- ❌ Zero values written as `null` → ✅ `null` is skipped but `0` keeps the stack heights stable; hide only the label
- ❌ Axis truncated around the data range → ✅ a diverging chart must keep zero inside the axis, otherwise the sign loses meaning
- ❌ Positive and negative entries of the same category drawn side by side → ✅ one `stack` name is what makes the reading "from zero outward"

## Alternatives

| Variant | Use instead |
|---|---|
| Cumulative deltas that add up to a new total | `run-rate-waterfall.md` |
| Signed values across two periods | `comparison-bars.md` (grouped) |
| Distribution of the same measure | `boxplot-latency-distribution.md` |

<!-- source: ECharts option manual (series-bar stack / label) + bar how-to; diverging-reading rule from the data-visualization guidance on zero baselines -->
