# Nested Pie — Cloud Spend by Environment and Service (ECharts)

**Best for**: a two-level split where the outer ring must stay traceable to its parent in the inner ring
**Avoid when**: there are more than two levels (use a sunburst) or the outer categories belong to several parents at once
**Answers**: how total spend splits by environment, and which services drive each environment

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 800,
  "height": 560,
  "title": { "text": "Cloud Spend by Environment and Service", "subtext": "Inner ring: environment · outer ring: service, share of total", "left": "left" },
  "series": [
    {
      "name": "Environment",
      "type": "pie",
      "radius": ["0%", "30%"],
      "center": ["50%", "54%"],
      "itemStyle": { "borderColor": "transparent", "borderWidth": 2 },
      "label": { "position": "inner", "formatter": "{b}\n{d}%" },
      "data": [
        { "value": 62, "name": "Production" },
        { "value": 22, "name": "Staging" },
        { "value": 16, "name": "Development" }
      ]
    },
    {
      "name": "Service",
      "type": "pie",
      "radius": ["42%", "66%"],
      "center": ["50%", "54%"],
      "itemStyle": { "borderColor": "transparent", "borderWidth": 2 },
      "label": {
        "show": true,
        "formatter": "{name|{b}}\n{share|{c}% of total}",
        "rich": {
          "name": { "fontSize": 12, "fontWeight": "bold", "lineHeight": 16 },
          "share": { "fontSize": 11, "lineHeight": 14 }
        }
      },
      "labelLine": { "length": 12, "length2": 14 },
      "data": [
        { "value": 24, "name": "api" },
        { "value": 21, "name": "search" },
        { "value": 17, "name": "billing" },
        { "value": 13, "name": "ml-lab" },
        { "value": 9, "name": "qa" },
        { "value": 16, "name": "sandbox" }
      ]
    }
  ]
}
```

## Data Shape

Two independent pie series over the **same centre**, with an empty annulus between them. The inner series holds
the parent totals, the outer series holds the children, and the outer values must sum to the same 100 as the
inner ones — ECharts does not check that for you.

| Ring | Radius | Content |
|---|---|---|
| Inner | `["0%", "30%"]` | Production 62 · Staging 22 · Development 16 |
| Gap | 30 % → 42 % | Deliberate whitespace: without it the rings read as one thick donut |
| Outer | `["42%", "66%"]` | Six services, kept in parent order so the arcs stay aligned |

## Key Options

| Option | Effect |
|---|---|
| Two `series` with different `radius` | Nesting is two pies plus a gap, not a built-in chart type |
| `itemStyle.borderWidth` + `borderColor: "transparent"` | Separates adjacent slices so the ring boundaries are visible in both themes |
| `label.rich` with named styles | Two-line labels with different weight per line; the content is a template, so no formatter callback is required |
| `center` shared by both series | Both rings must use the same centre value or the rings drift apart |
| `label.position: "inner"` for the inner ring | Keeps the short parent labels inside, where the outer labels will never collide with them |

## Pitfalls

- ❌ Outer slices ordered by size while the inner ring is ordered by parent → ✅ keep both rings in parent order, otherwise the visual grouping lies
- ❌ More than ~8 outer slices → ✅ use a sunburst (`sunburst-lifecycle-share.md`), which keeps hierarchy visible
- ❌ Relying on `{d}%` for the outer ring → ✅ `{d}` is the share of that ring's own total; write "of total" yourself or use `{c}%` when your data is already normalised
- ❌ Colours by ring instead of by slice → ✅ two separate series means two independent colour cycles; check that parents and children do not accidentally share the same hue in the same sector

## Alternatives

| Variant | Use instead |
|---|---|
| Three or more levels | `sunburst-lifecycle-share.md` |
| Hierarchy plus magnitude in rectangles | `treemap-portfolio-breakdown.md` |
| A flat single-level split | `donut-channel-mix.md` |

<!-- source: ECharts option manual (series-pie radius / center / label.rich) + the rich-text and nested-pie gallery examples -->
