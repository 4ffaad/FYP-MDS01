# Density Curve — Latency Spread Without Bins (Vega-Lite)

**Best for**: the *shape* of a distribution — where the mass sits and how long the tail runs
**Avoid when**: exact counts per range are needed, or there are only a handful of observations
**Answers**: whether latency clusters tightly or trails away, and where the second hump lives

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 520,
  "height": 220,
  "title": {"text": "Checkout Latency Distribution", "subtitle": "Kernel density over 28 sampled requests", "anchor": "start"},
  "data": {
    "values": [
      {"ms": 118}, {"ms": 124}, {"ms": 131}, {"ms": 137}, {"ms": 142},
      {"ms": 146}, {"ms": 151}, {"ms": 158}, {"ms": 163}, {"ms": 169},
      {"ms": 174}, {"ms": 181}, {"ms": 188}, {"ms": 196}, {"ms": 204},
      {"ms": 213}, {"ms": 221}, {"ms": 232}, {"ms": 244}, {"ms": 258},
      {"ms": 271}, {"ms": 289}, {"ms": 308}, {"ms": 331}, {"ms": 356},
      {"ms": 391}, {"ms": 438}, {"ms": 512}
    ]
  },
  "transform": [
    {"density": "ms", "bandwidth": 14}
  ],
  "mark": {"type": "area", "opacity": 0.6, "line": {"color": "#2b66c4"}, "color": "#0f9b9b"},
  "encoding": {
    "x": {"field": "value", "type": "quantitative", "title": "latency (ms)"},
    "y": {"field": "density", "type": "quantitative", "title": "density", "stack": null}
  }
}
```

## Data Shape

A single quantitative column — **one row per observation**, not a pre-binned count. The `density` transform
emits two fields: `value` (the smoothed position) and `density` (the curve height).

## Key Options

| Option | Effect |
|---|---|
| `transform.density` | Replaces binning with a kernel estimate; no bin width to justify |
| `bandwidth` | The smoothing knob: too small shows every bump, too large flattens real structure |
| `y.stack: null` | Prevents Vega-Lite from stacking the area to zero — a density curve is already normalised |
| `mark.line` + `opacity` | The outline carries the shape, the fill carries the mass; keep the fill translucent |
| `mark.color` fixed | One series, one hue — a legend for a single distribution is clutter |

## Pitfalls

- ❌ Reading the y-axis as a count → ✅ density is a normalised estimate; say "density" or drop the axis and label the x range instead
- ❌ Overlaying two densities with opaque fills → ✅ translucent fills plus stroked outlines, or the second curve hides the first
- ❌ Tiny samples with heavy smoothing → ✅ under ~20 points the curve invents structure; use a strip plot (`stripplot-region-spread.md`)
- ❌ A density that ignores `extent` → ✅ the tail is cut where the data ends; state the observation window

## Alternatives

| Variant | Use instead |
|---|---|
| Exact bin counts | `release-duration-distribution.md` |
| Median with quartiles per region | `boxplot-latency-distribution.md` |
| Every observation as a dot | `stripplot-region-spread.md` |

<!-- source: Vega-Lite docs (density transform output fields value/density, area mark, y.stack) + the histogram/density gallery section -->
