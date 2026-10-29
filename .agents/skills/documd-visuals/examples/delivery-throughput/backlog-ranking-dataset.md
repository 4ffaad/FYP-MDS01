# Dataset-Driven Ranking — Support Backlog by Age (ECharts)

**Best for**: a ranking whose source rows are already tabular, so the option stays free of parallel `data` arrays
**Avoid when**: the option is a one-off snapshot, or the data has to be reshaped before it can be drawn
**Answers**: which queues carry the oldest backlog, read straight off a named-dimension dataset

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 840,
  "height": 440,
  "title": { "text": "Support Backlog Ranked by Mean Age", "subtext": "Rows come from dataset.source and are bound through encode", "left": "left" },
  "grid": { "left": 96, "right": 96, "top": 100, "bottom": 40 },
  "dataset": {
    "source": [
      { "queue": "Trust & safety", "mean_age_days": 13.4, "open": 19 },
      { "queue": "Enterprise", "mean_age_days": 11.8, "open": 42 },
      { "queue": "Platform", "mean_age_days": 9.7, "open": 28 },
      { "queue": "Billing", "mean_age_days": 8.6, "open": 37 },
      { "queue": "Integrations", "mean_age_days": 6.1, "open": 64 },
      { "queue": "Self-serve", "mean_age_days": 4.2, "open": 118 }
    ]
  },
  "xAxis": { "type": "value", "name": "mean age (days)", "nameLocation": "end", "nameGap": 14 },
  "yAxis": { "type": "category", "axisTick": { "show": false } },
  "series": [
    {
      "name": "Mean age",
      "type": "bar",
      "barMaxWidth": 26,
      "encode": { "x": "mean_age_days", "y": "queue" },
      "label": { "show": true, "position": "right" }
    }
  ]
}
```

## Data Shape

`dataset.source` is an array of **object rows** — one object per queue with named dimensions. Rows are listed
worst-first: the category axis takes its order from the dataset, so the sort that would otherwise be a
`transform` is done upstream, where the data is produced.

| Field | Used by |
|---|---|
| `queue` | `encode.y` — the category axis, ordered by source row order |
| `mean_age_days` | `encode.x` — the measure being ranked |
| `open` | Not encoded here, but kept in the row so the same dataset can feed a second series later |

## Key Options

| Option | Effect |
|---|---|
| `dataset.source` with object rows | Named dimensions make `encode` readable and keep the series free of `data` arrays |
| `encode: { x, y }` | Binds dimensions to channels — the series carries no inline data at all |
| No `xAxis.data` / `yAxis.data` | Omitting them lets both axes take their domain and order from the encoded dataset |
| `dataset.dimensions` | Only needed with array rows (`[["queue", 11.8], …]`); object rows carry their own names |
| Source rows in final order | Reacting to a changed ranking means re-emitting the `source` array — see the pitfall on `transform` below |

## Pitfalls

- ❌ Using `dataset.transform` to sort → ✅ **verified broken**: in the bundled ECharts 6.1.0 a `sort`/`filter` transform throws `RangeError: Maximum call stack size exceeded` at `setOption` under both the SVG and the canvas renderer (reproduced 2026-09-21 with a minimal dataset). Sort upstream and hand over ordered rows
- ❌ Setting `yAxis.data` explicitly **and** using `dataset` → ✅ an explicit axis list wins and silently overrides the dataset's order
- ❌ Array rows without `dimensions` → ✅ with array rows you must declare `dimensions`, otherwise `encode` has no names to bind to
- ❌ Mixing an inline `data` series with dataset-bound series → ✅ keep every series on the dataset so they share one order and one domain

## Alternatives

| Variant | Use instead |
|---|---|
| A ranking with no dataset, pre-sorted by hand | `comparison-bars.md` |
| Two measures per queue | `scatter-segment-correlation.md` |
| Age distribution rather than the mean | `boxplot-latency-distribution.md` |

<!-- source: ECharts option manual (dataset.source object rows / encode / dimensions) + the dataset gallery entries; transform boundary reproduced locally against ECharts 6.1.0 -->
