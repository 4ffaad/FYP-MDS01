# Bullet Chart — Target Attainment by Team (Vega-Lite)

**Best for**: a compact target-versus-actual view where the reader needs one benchmark line and one attainment bar per category
**Avoid when**: the target is ambiguous, or the audience needs a full trend rather than a status-versus-threshold comparison
**Answers**: how each team is performing against its goal, and which teams are under target

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 420,
  "height": 220,
  "title": {"text": "Target Attainment by Team", "subtitle": "Actual throughput against the operating target", "anchor": "start"},
  "data": {
    "values": [
      {"team": "Core", "actual": 92, "target": 100},
      {"team": "Billing", "actual": 104, "target": 100},
      {"team": "Identity", "actual": 87, "target": 100},
      {"team": "Search", "actual": 111, "target": 100}
    ]
  },
  "layer": [
    {
      "mark": {"type": "bar", "cornerRadiusEnd": 3, "height": 18},
      "encoding": {
        "y": {"field": "team", "type": "nominal", "title": null},
        "x": {"field": "actual", "type": "quantitative", "title": "Throughput", "scale": {"domain": [0, 120]}},
        "color": {"value": "#2b66c4"}
      }
    },
    {
      "mark": {"type": "rule", "strokeWidth": 3, "color": "#f3a33c"},
      "encoding": {
        "y": {"field": "team", "type": "nominal"},
        "x": {"field": "target", "type": "quantitative"}
      }
    }
  ]
}
```

## Data Shape

One row per category with `actual` and `target` values. The layered bar and rule marks turn each row into a bullet-like comparison.

## Key Options

| Option | Effect |
|---|---|
| Layered `bar` + `rule` | Creates a compact actual-versus-target display |
| Shared quantitative domain | Makes category comparisons fair |
| Horizontal layout | Keeps category labels readable in a small export |
| Rule mark for target | Makes the benchmark visually distinct from the attainment bar |

## Pitfalls

- ❌ Using a bullet chart without a meaningful benchmark → ✅ the target is the point of the view
- ❌ Multiple unrelated benchmarks in one thin frame → ✅ once the viewer cannot decode the lines, use another chart
- ❌ Treating it like a trend chart → ✅ bullet charts answer status against target, not change over time

## Alternatives

| Variant | Use instead |
|---|---|
| Simple ranked comparison | `comparison-bars.md` |
| Single KPI status | `gauge-sla-attainment.md` |
| Variance around mean | `team-variance-interval.md` |

<!-- source: Vega-Lite layered examples (bullet / ranged dot family) + docs on layered plots -->