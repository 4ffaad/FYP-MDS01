# Launch Share by Channel (ECharts)

**Best for**: a chart that will be projected or glanced at — a launch review, a slide, a landing page
**Avoid when**: the figure is a dense reference table or a printed appendix — high chroma wears out
**Answers**: how the launch's volume splits across channels

```echarts
{
  "width": 640, "height": 300,
  "color": ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed", "#0d9488", "#db2777", "#92400e"],
  "series": [{
    "type": "pie",
    "radius": "68%",
    "data": [
      { "name": "Direct", "value": 34 },
      { "name": "Partner", "value": 26 },
      { "name": "Search", "value": 18 },
      { "name": "Social", "value": 14 },
      { "name": "Email", "value": 8 }
    ]
  }]
}
```

## Data Shape

One row per channel with a share or count. The ramp is positional: the first channel gets the first
colour, the second the second, and so on.

## Key Options

| Option | Effect |
|---|---|
| `"color"` at the top level | Sets the ramp for every series in the spec |
| A shorter list | Trimming to the live channel count is fine — any prefix of the ramp, in order |
| `itemStyle.color` on a series | Overrides the ramp for that one series, when one needs to stand out |

## Pitfalls

- ❌ Hand-picking a colour per slice → ✅ that is how a chart ends up with two blues that are not the theme's blue
- ❌ Setting `textStyle.color` or `backgroundColor` → ✅ the renderer owns both; a label colour set here breaks on a dark page
- ❌ Eight categories in a pie → ✅ five or fewer; group the tail

## Alternatives

| Variant | Use instead |
|---|---|
| The same split on a quiet report page | `donut-channel-mix.md` |
| The same split read by a colour-blind audience | `accessible-service-mix.md` |
| The same split on a photocopied handout | `print-handout-graph.md` |
| A funnel rather than a split | `funnel-stage-conversion.md` |

<!-- source: theme showcase — Vivid theme, echarts colour ramp -->
