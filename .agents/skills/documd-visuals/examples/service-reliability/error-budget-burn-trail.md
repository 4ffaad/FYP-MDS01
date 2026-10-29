# Trail Mark — Error Budget Burn by Release (Vega-Lite)

**Best for**: a trend whose **width** carries a second measure, so fast and slow burns look different
**Avoid when**: the width measure is nearly constant (the width then reads as noise), sparse points, or the reader must compare widths precisely
**Answers**: not just how the error budget moved, but how fast the spend was at each release

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 520,
  "height": 230,
  "title": {"text": "Error Budget Burn", "subtitle": "Line: budget remaining · width: minutes of budget spent that release", "anchor": "start"},
  "data": {
    "values": [
      {"release": "24.01", "remaining": 100, "burn": 3},
      {"release": "24.02", "remaining": 94, "burn": 6},
      {"release": "24.03", "remaining": 91, "burn": 3},
      {"release": "24.04", "remaining": 76, "burn": 15},
      {"release": "24.05", "remaining": 72, "burn": 4},
      {"release": "24.06", "remaining": 68, "burn": 4},
      {"release": "24.07", "remaining": 41, "burn": 27},
      {"release": "24.08", "remaining": 36, "burn": 5},
      {"release": "24.09", "remaining": 33, "burn": 3},
      {"release": "24.10", "remaining": 9, "burn": 24},
      {"release": "24.11", "remaining": 6, "burn": 3},
      {"release": "24.12", "remaining": 4, "burn": 2}
    ]
  },
  "mark": {"type": "trail", "color": "#2b66c4", "opacity": 0.75},
  "encoding": {
    "x": {"field": "release", "type": "ordinal", "title": null, "axis": {"labelAngle": 0}},
    "y": {"field": "remaining", "type": "quantitative", "title": "% budget remaining", "scale": {"zero": true}},
    "size": {"field": "burn", "type": "quantitative", "scale": {"range": [1.5, 14]}, "legend": {"title": "burn (min)"}}
  }
}
```

## Data Shape

One row per step with a position, a value, and the width measure. The trail interpolates between points, so
each row's width applies to the segment leaving that point.

| Field | Role |
|---|---|
| `release` | Ordinal x — this is a release-by-release walk, not a continuous clock |
| `remaining` | y position of the trail |
| `burn` | `size`, mapped to stroke width in pixels |

## Key Options

| Option | Effect |
|---|---|
| `mark.type: "trail"` | The only mark where size means stroke width rather than marker area |
| `scale.range: [1.5, 14]` | An explicit pixel range stops a single heavy release from flattening every other segment |
| `opacity: 0.75` | Overlapping thick segments stay readable |
| `scale.zero: true` on y | A budget burns to zero; the axis must include the empty state |
| Ordinal x with short labels | Release names are the natural step; a temporal axis would leave gaps between releases |

## Pitfalls

- ❌ Trail where the width measure is nearly constant → ✅ the form then pretends to encode something; use a plain line
- ❌ Sparse points → ✅ trails interpolate between rows, so a gap in the data becomes a misleading smooth segment
- ❌ Reading exact widths → ✅ stroke width is a rough channel; print the values for any release you will discuss
- ❌ A trail plus a point layer → ✅ the thickness already interrupts the line; extra markers muddle the reading

## Alternatives

| Variant | Use instead |
|---|---|
| Two separate measures on two axes | `capacity-cost-dual-axis.md` |
| Burn that must be read against a threshold | `threshold-breach-annotation.md` |
| Volume and share at each step | `quarterly-share-normalized-stack.md` |

<!-- source: Vega-Lite docs (trail mark: size maps to stroke width; point/mark type roster) + the trail entries in the Vega-Lite mark documentation -->
