# Repeat Histograms — Distribution Across Metrics (Vega-Lite)

**Best for**: comparing the shape of several numeric fields without overlaying them into one unreadable chart
**Avoid when**: the reader only needs one metric or expects exact raw values rather than distribution shape
**Answers**: how multiple measures differ in spread, concentration, and skew under the same visual grammar

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "title": {"text": "Metric Distributions", "subtitle": "Repeated histograms for latency, queue depth, and retries", "anchor": "start"},
  "data": {
    "values": [
      {"latency": 118, "queue": 22, "retries": 1}, {"latency": 132, "queue": 25, "retries": 1}, {"latency": 145, "queue": 30, "retries": 2},
      {"latency": 151, "queue": 31, "retries": 2}, {"latency": 166, "queue": 36, "retries": 3}, {"latency": 177, "queue": 42, "retries": 4},
      {"latency": 184, "queue": 39, "retries": 3}, {"latency": 196, "queue": 46, "retries": 5}, {"latency": 208, "queue": 51, "retries": 5}
    ]
  },
  "repeat": {"column": ["latency", "queue", "retries"]},
  "spec": {
    "width": 170,
    "height": 180,
    "mark": "bar",
    "encoding": {
      "x": {"field": {"repeat": "column"}, "bin": true, "type": "quantitative", "title": null},
      "y": {"aggregate": "count", "type": "quantitative", "title": "Count"}
    }
  }
}
```

## Data Shape

One row per observation with several numeric fields. The `repeat` operator projects the same histogram grammar across each selected metric field.

## Key Options

| Option | Effect |
|---|---|
| `repeat.column` | Reuses one histogram spec across multiple numeric fields |
| Binned quantitative `x` | Turns each repeated panel into a distribution view |
| Shared `y` aggregate | Makes the repeated panels comparable as counts |
| Fixed facet sizes | Keeps the export stable and evenly balanced |

## Pitfalls

- ❌ Different units with implied comparability → ✅ repeated panels compare shape, not necessarily scale semantics
- ❌ Too many repeated fields → ✅ small multiples stop working once each panel is too small to read
- ❌ Overlaying all metrics together → ✅ repeat exists precisely to avoid overplotting different distributions

## Alternatives

| Variant | Use instead |
|---|---|
| One metric only | A single histogram spec |
| Segment comparison by facet | `segment-pattern-small-multiples.md` |
| Category distributions | `release-duration-distribution.md` |

<!-- source: Vega-Lite docs (repeat / histogram) + examples gallery Repeat & Concatenation -->