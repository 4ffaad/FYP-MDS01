# Top-K with Others — Revenue Concentration (Vega-Lite)

**Best for**: long category tails where the reader needs the top contributors without losing the remainder of the distribution
**Avoid when**: every category matters individually or the tail is too small to justify aggregation
**Answers**: which items dominate, and how much of the total sits outside the top group

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 460,
  "height": 260,
  "data": {
    "values": [
      {"product": "Core API", "revenue": 128},
      {"product": "Billing", "revenue": 112},
      {"product": "Search", "revenue": 94},
      {"product": "Warehouse", "revenue": 83},
      {"product": "Identity", "revenue": 76},
      {"product": "Support Tools", "revenue": 41},
      {"product": "Data Sync", "revenue": 36},
      {"product": "Partner Portal", "revenue": 32},
      {"product": "Notifications", "revenue": 25}
    ]
  },
  "title": {"text": "Top Revenue Contributors", "subtitle": "Top 5 products with the long tail collapsed into Others", "anchor": "start"},
  "transform": [
    {"window": [{"op": "rank", "as": "rank"}], "sort": [{"field": "revenue", "order": "descending"}]},
    {"calculate": "datum.rank <= 5 ? datum.product : 'Others'", "as": "bucket"},
    {"calculate": "datum.rank <= 5 ? datum.rank : 99", "as": "bucket_order"},
    {"aggregate": [{"op": "sum", "field": "revenue", "as": "revenue"}], "groupby": ["bucket", "bucket_order"]}
  ],
  "mark": {"type": "bar", "cornerRadiusEnd": 4},
  "encoding": {
    "y": {"field": "bucket", "type": "nominal", "sort": {"field": "bucket_order", "order": "ascending"}, "title": null},
    "x": {"field": "revenue", "type": "quantitative", "title": "Revenue (k$)"},
    "color": {"field": "bucket", "type": "nominal", "legend": null},
    "tooltip": [
      {"field": "bucket", "type": "nominal", "title": "Group"},
      {"field": "revenue", "type": "quantitative", "format": ",.0f", "title": "Revenue (k$)"}
    ]
  }
}
```

## Data Shape

One row per category. The spec ranks rows, rewrites tail categories into `Others`, and re-aggregates them into a single bar.

## Key Options

| Option | Effect |
|---|---|
| `window` + `rank` | Finds the top records without preprocessing the data outside the spec |
| `calculate` | Re-buckets low-ranked categories into `Others` |
| `aggregate` | Re-sums the rewritten bucket values after the transform |
| `sort` on the y encoding | Keeps the top ranks in order and pushes `Others` to the end |

## Pitfalls

- ❌ Manually editing the dataset to build `Others` → ✅ let the transform document the rule in the spec itself
- ❌ Using a pie chart for a long tail → ✅ top-k + others is easier to read as a sorted bar view
- ❌ Forgetting to re-aggregate after relabeling → ✅ the tail will still appear as several rows named `Others`

## Alternatives

| Variant | Use instead |
|---|---|
| Exact comparison for all categories | A full sorted bar chart |
| Part-to-whole for a few categories | `pie-budget-share.md` or `donut-channel-mix.md` |
| Need multiple grouped dimensions | `comparison-bars.md` or a faceted Vega-Lite view |

<!-- source: Vega-Lite docs (window / calculate / aggregate) + examples gallery Advanced Calculations top-k/top-k+others -->