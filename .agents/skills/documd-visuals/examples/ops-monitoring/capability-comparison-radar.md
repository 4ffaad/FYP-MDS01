# Radar — Capability Comparison with Explicit Geometry (Vega)

**Best for**: comparing a few entities across shared dimensions when you need a radar chart that Vega-Lite cannot express directly
**Avoid when**: exact per-dimension comparison matters more than overall shape, or many entities would overlap
**Answers**: where profiles differ, and whether one option is balanced or skewed across dimensions

```vega
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "width": 360,
  "height": 360,
  "padding": 50,
  "autosize": {"type": "none", "contains": "padding"},
  "signals": [{"name": "radius", "update": "width / 2"}],
  "data": [
    {
      "name": "table",
      "values": [
        {"dim": "Resilience", "val": 82, "cat": "Current"},
        {"dim": "Automation", "val": 61, "cat": "Current"},
        {"dim": "Security", "val": 78, "cat": "Current"},
        {"dim": "Operability", "val": 69, "cat": "Current"},
        {"dim": "Scalability", "val": 74, "cat": "Current"},
        {"dim": "Resilience", "val": 92, "cat": "Target"},
        {"dim": "Automation", "val": 88, "cat": "Target"},
        {"dim": "Security", "val": 91, "cat": "Target"},
        {"dim": "Operability", "val": 85, "cat": "Target"},
        {"dim": "Scalability", "val": 89, "cat": "Target"}
      ]
    },
    {
      "name": "dimensions",
      "values": [
        {"dim": "Resilience"},
        {"dim": "Automation"},
        {"dim": "Security"},
        {"dim": "Operability"},
        {"dim": "Scalability"}
      ]
    }
  ],
  "title": {"text": "Capability Comparison", "subtitle": "Current profile versus target profile", "anchor": "start", "color": "#1f2937", "subtitleColor": "#2b66c4"},
  "scales": [
    {"name": "angular", "type": "point", "range": {"signal": "[-PI, PI]"}, "padding": 0.5, "domain": ["Resilience", "Automation", "Security", "Operability", "Scalability"]},
    {"name": "radial", "type": "linear", "range": {"signal": "[0, radius]"}, "domain": [0, 100], "zero": true},
    {"name": "color", "type": "ordinal", "domain": ["Current", "Target"], "range": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"]}
  ],
  "encode": {"enter": {"x": {"signal": "radius"}, "y": {"signal": "radius"}}},
  "marks": [
    {
      "type": "text",
      "from": {"data": "dimensions"},
      "encode": {
        "enter": {
          "x": {"signal": "(radius + 18) * cos(scale('angular', datum.dim))"},
          "y": {"signal": "(radius + 18) * sin(scale('angular', datum.dim))"},
          "text": {"field": "dim"},
          "fill": {"value": "#676f7e"},
          "fontSize": {"value": 11},
          "align": {"value": "center"}
        }
      }
    },
    {
      "type": "group",
      "from": {"facet": {"data": "table", "name": "facet", "groupby": ["cat"]}},
      "marks": [
        {
          "type": "line",
          "from": {"data": "facet"},
          "encode": {
            "enter": {
              "interpolate": {"value": "linear-closed"},
              "x": {"signal": "scale('radial', datum.val) * cos(scale('angular', datum.dim))"},
              "y": {"signal": "scale('radial', datum.val) * sin(scale('angular', datum.dim))"},
              "stroke": {"scale": "color", "field": "cat"},
              "strokeWidth": {"value": 2},
              "fill": {"scale": "color", "field": "cat"},
              "fillOpacity": {"value": 0.12}
            }
          }
        }
      ]
    }
  ]
}


```

## Data Shape

One row per `{dimension, value, category}` pair. Vega facets the rows by category and draws one closed polygon per compared profile.

## Key Options

| Option | Effect |
|---|---|
| Vega `scales` + trig expressions | Builds the polar geometry explicitly, which is why this needs Vega rather than Vega-Lite |
| `facet` by category | Creates one polygon per compared profile |
| Closed `line` mark | Turns the dimension sequence into a radar polygon |
| Fill opacity | Lets overlapping profiles stay readable |

## Pitfalls

- ❌ Using radar for precise numeric reading → ✅ the overall profile shape is the main message
- ❌ Too many categories → ✅ overlapping polygons quickly turn opaque and unreadable
- ❌ Forgetting consistent dimension order → ✅ one dimension reorder changes the meaning of the whole polygon |

## Alternatives

| Variant | Use instead |
|---|---|
| Exact metric-by-metric comparison | `comparison-bars.md` or a grouped Vega-Lite bar chart |
| One KPI only | `gauge-sla-attainment.md` |
| Multi-metric score grid | `matrix-service-scorecards.md` |

<!-- source: Vega docs (marks / scales / facet) + repo vega examples reference radar pattern -->