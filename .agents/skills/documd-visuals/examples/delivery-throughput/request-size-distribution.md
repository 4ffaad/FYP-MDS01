# Histogram — Request Size Distribution (Vega-Lite)

**Best for**: showing how one numeric measure is distributed, especially where concentration and long tails matter
**Avoid when**: the reader needs exact raw values or the sample is too small for a meaningful distribution
**Answers**: where most observations cluster, and whether the tail is short, wide, or skewed

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 440,
  "height": 250,
  "title": {"text": "Request Size Distribution", "subtitle": "Payload size across recent API calls", "anchor": "start"},
  "data": {"values": [
    {"kb": 8}, {"kb": 10}, {"kb": 11}, {"kb": 13}, {"kb": 15}, {"kb": 16}, {"kb": 19},
    {"kb": 22}, {"kb": 25}, {"kb": 28}, {"kb": 31}, {"kb": 33}, {"kb": 37}, {"kb": 42}, {"kb": 49}
  ]},
  "mark": {"type": "bar", "cornerRadiusEnd": 3},
  "encoding": {
    "x": {"bin": {"maxbins": 8}, "field": "kb", "type": "quantitative", "title": "Payload size (KB)"},
    "y": {"aggregate": "count", "type": "quantitative", "title": "Count"}
  }
}
```

## Data Shape

One row per observation with one numeric field to bin.

## Key Options

| Option | Effect |
|---|---|
| `bin` | Groups continuous values into readable ranges |
| `aggregate: "count"` | Turns raw rows into a frequency distribution |
| Fixed `maxbins` | Keeps the export from becoming too granular |

## Pitfalls

- ❌ Using a histogram for pre-bucketed categories → ✅ histograms expect raw continuous values
- ❌ Too many bins for a tiny sample → ✅ the chart becomes noise instead of shape
- ❌ Reading the tallest bar as the only story → ✅ distribution width and skew matter too

## Alternatives

| Variant | Use instead |
|---|---|
| Category distributions | `release-duration-distribution.md` |
| Repeated distributions for several metrics | `metric-distribution-small-multiples.md` |
| Exact values by item | `comparison-bars.md` |

<!-- source: Vega-Lite docs (bin / histogram) + examples gallery Histograms -->