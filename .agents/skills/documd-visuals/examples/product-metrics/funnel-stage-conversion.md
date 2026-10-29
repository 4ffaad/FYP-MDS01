# Funnel — Stage Conversion and Drop-off (ECharts)

**Best for**: ordered stages where the message is conversion and attrition from one step to the next
**Avoid when**: stages loop, split into parallel paths, or you need exact transfer volumes between branches (use sankey)
**Answers**: where the largest drop happens, and how much volume remains at each stage

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 820,
  "height": 430,
  "title": { "text": "Hiring Funnel", "subtext": "Quarter-to-date candidate conversion", "left": "left" },
  "legend": { "data": ["Candidates"], "top": 8, "right": 8 },
  "series": [
    {
      "name": "Candidates",
      "type": "funnel",
      "left": "8%",
      "top": 102,
      "bottom": 28,
      "width": "72%",
      "min": 0,
      "max": 2400,
      "minSize": "10%",
      "maxSize": "100%",
      "sort": "descending",
      "gap": 3,
      "label": { "show": true, "position": "inside", "formatter": "{b}\n{c}" },
      "labelLine": { "show": false },
      "itemStyle": { "borderColor": "rgba(255,255,255,0.9)", "borderWidth": 1 },
      "data": [
        { "value": 2400, "name": "Applicants" },
        { "value": 1200, "name": "Screened" },
        { "value": 520, "name": "Interviews" },
        { "value": 220, "name": "Offers" },
        { "value": 120, "name": "Accepted" }
      ]
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `sort: "descending"` | Keeps the funnel ordered from largest stage to smallest; use ascending only for inverted storytelling |
| `minSize` / `maxSize` | Stops the tail from collapsing into an unreadable tip |
| `label.position: "inside"` | Makes every stage carry its own value, which matters in static exports |
| `gap` | Separates stages so the drop-offs read as discrete steps rather than one blended shape |
| `min` / `max` | Locks the width scale to the real stage range instead of letting ECharts infer it |

## Data Shape

One ordered `data` array of `{ name, value }` stage objects. The order is semantic: this chart only makes sense when the stages represent a real progression.

## Pitfalls

- ❌ Unordered categories in a funnel → ✅ a funnel is not a ranked bar chart; only use it for true process stages
- ❌ Tiny tail stages with outside labels only → ✅ static exports need inside labels or the smallest stages become guesswork
- ❌ Using a funnel for branching journeys → ✅ use `sankey` when one stage splits into multiple downstream paths
- ❌ Comparing several funnels in one frame → ✅ use bars if the reader must compare multiple pipelines side by side

## Alternatives

| Variant | Use instead |
|---|---|
| Branching conversions | `sankey-channel-to-fulfilment.md` |
| Exact stage-to-stage comparisons | `comparison-bars.md` |
| Time trend of one stage | `trend-line-multi-series.md` |

<!-- source: ECharts option manual (series-funnel) + examples gallery funnel family -->