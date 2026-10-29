# Strip Plot — Regional Spread of Resolution Time (Vega-Lite)

**Best for**: showing all observations across categories when you want to preserve individual points rather than summarize them away
**Avoid when**: there are too many points for a clean export or the reader only needs summary statistics
**Answers**: how each category spreads, where points cluster, and whether one group is noisier than another

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 460,
  "height": 250,
  "title": {"text": "Regional Resolution Spread", "subtitle": "All observed ticket resolution times by region", "anchor": "start"},
  "data": {"values": [
    {"region": "NA", "hours": 6}, {"region": "NA", "hours": 8}, {"region": "NA", "hours": 12},
    {"region": "EMEA", "hours": 7}, {"region": "EMEA", "hours": 11}, {"region": "EMEA", "hours": 14},
    {"region": "APAC", "hours": 5}, {"region": "APAC", "hours": 9}, {"region": "APAC", "hours": 15}
  ]},
  "mark": {"type": "tick", "thickness": 3, "size": 22},
  "encoding": {
    "x": {"field": "hours", "type": "quantitative", "title": "Resolution time (hours)"},
    "y": {"field": "region", "type": "nominal", "title": null},
    "color": {"field": "region", "type": "nominal", "legend": null}
  }
}
```

## Data Shape

One row per observation, grouped by a category field and plotted as one mark per row.

## Key Options

| Option | Effect |
|---|---|
| `mark: "tick"` | Preserves individual observations in a compact strip-plot form |
| Quantitative `x` + nominal `y` | Spreads values across comparable category rows |
| Color by category | Helps each row separate visually |

## Pitfalls

- ❌ Too many points in a static export → ✅ switch to boxplots or density summaries when the strip becomes cluttered
- ❌ Using strip plots when only the mean matters → ✅ the value of the strip plot is in preserving individual observations
- ❌ Unequal category semantics → ✅ every row should represent the same measure type

## Alternatives

| Variant | Use instead |
|---|---|
| Summary distribution | `release-duration-distribution.md` |
| Relationship between two measures | `segment-pattern-small-multiples.md` |
| One-dimensional histogram | `request-size-distribution.md` |

<!-- source: Vega-Lite docs (tick mark / strip plot) + examples gallery Scatter & Strip -->