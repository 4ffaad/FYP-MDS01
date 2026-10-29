# Sunburst — Catalog Share by Nesting Level (Vega)

**Best for**: three levels of hierarchy as concentric rings, where the centre is the whole
**Avoid when**: more than three levels, or exact shares at the deepest level matter
**Answers**: how the catalog divides between publish, preview and archive, and what drives each ring

```vega
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "width": 500,
  "height": 470,
  "padding": 10,
  "title": {"text": "Catalog Share", "subtitle": "Inner ring: disposition · outer ring: content type, % of catalog", "anchor": "start"},
  "data": [
    {
      "name": "tree",
      "values": [
        {"id": "catalog", "parent": null, "name": "Catalog", "size": 100},
        {"id": "publish", "parent": "catalog", "name": "Published", "size": 58},
        {"id": "guides", "parent": "publish", "name": "Guides", "size": 14},
        {"id": "reference", "parent": "publish", "name": "Reference", "size": 10},
        {"id": "tutorials", "parent": "publish", "name": "Tutorials", "size": 12},
        {"id": "blog", "parent": "publish", "name": "Blog", "size": 22},
        {"id": "preview", "parent": "catalog", "name": "Preview", "size": 26},
        {"id": "staging", "parent": "preview", "name": "Staging", "size": 15},
        {"id": "sandbox", "parent": "preview", "name": "Sandbox", "size": 11},
        {"id": "archive", "parent": "catalog", "name": "Archived", "size": 16},
        {"id": "expiring", "parent": "archive", "name": "Expiring", "size": 9},
        {"id": "sunset", "parent": "archive", "name": "Sunset", "size": 7}
      ],
      "transform": [
        {"type": "stratify", "key": "id", "parentKey": "parent"},
        {
          "type": "partition",
          "field": "size",
          "sort": {"field": "value"},
          "size": [{"signal": "2 * PI"}, {"signal": "width / 2 - 24"}],
          "as": ["a0", "r0", "a1", "r1"]
        }
      ]
    }
  ],
  "scales": [
    {"name": "color", "type": "ordinal", "domain": {"data": "tree", "field": "depth"}, "range": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"]},
    {"name": "label", "type": "ordinal", "domain": {"data": "tree", "field": "depth"}, "range": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"]}
  ],
  "marks": [
    {
      "type": "arc",
      "from": {"data": "tree"},
      "encode": {
        "update": {
          "x": {"signal": "width / 2"},
          "y": {"signal": "height / 2"},
          "startAngle": {"field": "a0"},
          "endAngle": {"field": "a1"},
          "innerRadius": {"field": "r0"},
          "outerRadius": {"field": "r1"},
          "fill": {"scale": "color", "field": "depth"},
          "stroke": {"value": "#ffffff"},
          "strokeWidth": {"value": 1.2}
        }
      }
    },
    {
      "type": "text",
      "from": {"data": "tree"},
      "interactive": false,
      "encode": {
        "update": {
          "x": {"signal": "width / 2"},
          "y": {"signal": "height / 2"},
          "startAngle": {"field": "a0"},
          "endAngle": {"field": "a1"},
          "radius": {"signal": "(datum.r0 + datum.r1) / 2"},
          "theta": {"signal": "(datum.a0 + datum.a1) / 2"},
          "text": {"field": "name"},
          "fontSize": {"value": 10},
          "align": {"value": "center"},
          "baseline": {"value": "middle"},
          "fill": {"scale": "label", "field": "depth"}
        }
      }
    }
  ]
}


```

## Data Shape

The flat parent/child table again, this time with the `partition` transform producing **angles and radii**:

| Output | Meaning |
|---|---|
| `a0`, `a1` | Start and end angle of the sector (in radians) |
| `r0`, `r1` | Inner and outer radius — one ring per tree depth |

## Key Options

| Option | Effect |
|---|---|
| `size: [2π, width/2]` | Full circle for the angles, radius for the depth axis |
| `arc` mark | The ring primitive driven by `startAngle`/`endAngle` + `innerRadius`/`outerRadius` |
| `theta` + `radius` on text marks | Vega's polar positioning for text, which centres labels inside their sector |
| Depth colour ramp + label ramp | Distinguishes rings while keeping every label legible |
| `stroke: "#ffffff"`, width 1.2 | Hairline separators; without them adjacent sectors of one ring merge |

## Pitfalls

- ❌ Four or more rings → ✅ the outer rings become thin lines; keep two data levels plus the root
- ❌ Labels on narrow sectors → ✅ they overflow into neighbours; either drop labels below a size threshold or annotate outside
- ❌ Reading the angle of an outer sector as its share of the whole → ✅ outer sectors are sliced within their parent, so the share is conditional — say so
- ❌ Sorting sectors alphabetically → ✅ sort by value so the rings line up with the eye's expectation of descending size

## Alternatives

| Variant | Use instead |
|---|---|
| Hierarchy as nested rectangles | `cost-center-treemap.md` |
| Two levels, ring + donut | `cloud-spend-nested-pie.md` (ECharts) |
| Hierarchy with left/right comparison | `platform-org-structure.md` (Infographic) |

<!-- source: Vega docs (stratify + partition transforms with a0/r0/a1/r1 outputs; arc mark angles and radii; text theta/radius) + the sunburst gallery example -->
