# Difference from Average — Deviation Bars (Vega-Lite)

**Best for**: showing which categories sit above or below the group average without requiring the reader to compute the benchmark mentally
**Avoid when**: the audience needs raw totals only or the average itself is not a meaningful reference
**Answers**: who is above the norm, who is below it, and by how much each category deviates

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 440,
  "height": 260,
  "title": {"text": "Deviation from Average", "subtitle": "Category performance relative to the group mean", "anchor": "start"},
  "data": {"values": [
    {"team": "Core", "score": 92},
    {"team": "Billing", "score": 104},
    {"team": "Identity", "score": 87},
    {"team": "Search", "score": 111},
    {"team": "Warehouse", "score": 95}
  ]},
  "transform": [
    {"joinaggregate": [{"op": "mean", "field": "score", "as": "avg_score"}]},
    {"calculate": "datum.score - datum.avg_score", "as": "delta"}
  ],
  "mark": {"type": "bar", "cornerRadiusEnd": 3},
  "encoding": {
    "y": {"field": "team", "type": "nominal", "sort": "-x", "title": null},
    "x": {"field": "delta", "type": "quantitative", "title": "Difference from average"},
    "color": {"condition": {"test": "datum.delta >= 0", "value": "#2b66c4"}, "value": "#d1242f"}
  }
}
```

## Data Shape

One row per category with the measure to compare. The spec computes the mean and then derives each row’s deviation from it.

## Key Options

| Option | Effect |
|---|---|
| `joinaggregate` | Computes the overall benchmark inside the spec |
| `calculate` delta | Turns raw values into relative-above/below bars |
| Signed quantitative axis | Makes over- and under-performance symmetrical around zero |
| Conditional color | Separates positive and negative deviation instantly |

## Pitfalls

- ❌ Comparing raw bars when relative deviation is the point → ✅ the benchmark should be explicit
- ❌ Using the mean when the distribution is badly skewed → ✅ check whether median or another reference is more appropriate
- ❌ Hiding the sign of the difference → ✅ positive and negative direction is the core message |

## Alternatives

| Variant | Use instead |
|---|---|
| Absolute category comparison | `comparison-bars.md` |
| Rank movement over time | `rank-movement-over-time.md` |
| Summary uncertainty around the mean | `team-variance-interval.md` |

<!-- source: Vega-Lite docs (joinaggregate / calculate) + examples gallery Advanced Calculations diff-from-average -->