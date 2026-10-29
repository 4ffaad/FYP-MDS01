# Donut — Where the Release Cycle Time Goes (Vega-Lite)

**Best for**: a small share-of-total split where the hole can carry a headline number
**Avoid when**: there are more than ~6 parts, or the parts must be compared precisely
**Answers**: which phase eats the release cycle, and how lopsided the split is

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 300,
  "height": 300,
  "title": {"text": "Where Release Time Goes", "subtitle": "Average of the last 8 releases, hours per phase", "anchor": "start"},
  "data": {
    "values": [
      {"phase": "Verification", "hours": 31},
      {"phase": "Waiting on reviews", "hours": 18},
      {"phase": "Staging soak", "hours": 12},
      {"phase": "Build and test", "hours": 9},
      {"phase": "Deploy and watch", "hours": 6},
      {"phase": "Rollback and rework", "hours": 4}
    ]
  },
  "mark": {"type": "arc", "innerRadius": 62, "outerRadius": 124, "padAngle": 0.02, "cornerRadius": 3},
  "encoding": {
    "theta": {"field": "hours", "type": "quantitative", "sort": "descending"},
    "color": {"field": "phase", "type": "nominal", "legend": {"title": null}},
    "order": {"field": "hours", "type": "quantitative", "sort": "descending"}
  }
}
```

## Data Shape

One row per part with a single positive measure. `theta` sizes the wedge, `color` separates the wedges, and
`order` (or `sort` on theta) fixes which end of the circle the largest slice starts from.

## Key Options

| Option | Effect |
|---|---|
| `mark.type: "arc"` | The circular mark family: wedge geometry without a coordinate trick |
| `innerRadius` | Turns the pie into a donut; the hole is what makes room for a total |
| `outerRadius` | Fixes the ring thickness in pixels — set it rather than relying on defaults when the view is small |
| `padAngle: 0.02` | Radiates a hairline gap between wedges so neighbours never look merged |
| `cornerRadius: 3` | Rounds each wedge; keep it small or thin slices disappear |
| `theta.sort: "descending"` | Largest slice first, going clockwise from twelve o'clock |
| `color.legend.title: null` | The labels are self-evident; a legend title is noise |

## Pitfalls

- ❌ Nine or ten slices → ✅ beyond about six parts the labels collide and the shares stop being readable
- ❌ Encoding a second measure in `radius` as well → ✅ a rose-style double encoding exaggerates large parts; keep the radius constant
- ❌ Adding up the numbers in your head → ✅ the arc carries no values; print the total in the title or add a text layer in the hole
- ❌ Forgetting `order` → ✅ without it the wedge order is arbitrary, and the same data can render in a different sequence

## Alternatives

| Variant | Use instead |
|---|---|
| Part-to-whole with exact comparison | `comparison-bars.md` (ECharts) |
| A mix that changes over time | `quarterly-share-normalized-stack.md` |
| Ranking of the same phases | `revenue-concentration-topk-others.md` |

<!-- source: Vega-Lite docs (arc mark: innerRadius / outerRadius / padAngle / cornerRadius; theta and order channels) + the circular-plot gallery section -->
