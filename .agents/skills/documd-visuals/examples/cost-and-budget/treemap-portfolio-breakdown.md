# Treemap — Portfolio Breakdown by Domain and Product (ECharts)

**Best for**: hierarchical share-of-total where both the grouping and the relative area matter
**Avoid when**: exact comparisons between many siblings matter more than the hierarchy, or the hierarchy is very deep and text must remain readable
**Answers**: where the largest areas are, how the total is split across groups, and which child items dominate inside each group

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 860,
  "height": 460,
  "title": { "text": "Product Portfolio Mix", "subtext": "Annual recurring revenue by domain and product", "left": "left" },
  "series": [
    {
      "type": "treemap",
      "top": 92,
      "left": 20,
      "right": 20,
      "bottom": 24,
      "breadcrumb": { "show": false },
      "label": { "show": true, "formatter": "{b}" },
      "upperLabel": { "show": true, "height": 24 },
      "itemStyle": { "borderColor": "rgba(255,255,255,0.75)", "borderWidth": 1, "gapWidth": 2 },
      "levels": [
        { "itemStyle": { "borderColor": "rgba(255,255,255,0.9)", "borderWidth": 2, "gapWidth": 4 } },
        { "colorSaturation": [0.35, 0.7], "itemStyle": { "gapWidth": 2, "borderColorSaturation": 0.7 } }
      ],
      "data": [
        {
          "name": "Commerce",
          "children": [
            { "name": "Checkout", "value": 38 },
            { "name": "Catalog", "value": 26 },
            { "name": "Search", "value": 18 }
          ]
        },
        {
          "name": "Operations",
          "children": [
            { "name": "Fulfilment", "value": 30 },
            { "name": "Support", "value": 20 }
          ]
        },
        {
          "name": "Platform",
          "children": [
            { "name": "Identity", "value": 24 },
            { "name": "Observability", "value": 16 }
          ]
        }
      ]
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `upperLabel.show` | Keeps parent group names visible above their child tiles |
| `levels` | Lets you style hierarchy levels differently so parent/child structure remains legible |
| `breadcrumb.show: false` | Removes interaction-oriented navigation that does not help static exports |
| `gapWidth` + borders | Separates adjacent tiles so area changes remain readable |
| Nested `data.children` | Encodes the hierarchy directly in the option JSON |

## Data Shape

Nested `children` arrays with `value` at the leaf nodes. Parents group related leaves; the rendered area is driven by the leaf values.

## Pitfalls

- ❌ Deep hierarchies with tiny leaves → ✅ labels become unreadable fast; keep the depth shallow in static exports
- ❌ Using a treemap for exact comparison → ✅ area is good for proportional reading, not precise ranking
- ❌ Missing parent labels → ✅ show the group layer or the hierarchy collapses into coloured rectangles
- ❌ Too many similar-sized tiles → ✅ when hierarchy stops helping, switch to bars or a table

## Alternatives

| Variant | Use instead |
|---|---|
| Hierarchical share in rings | `sunburst-lifecycle-share.md` |
| Exact comparison across groups | `comparison-bars.md` |
| Plain hierarchy without values | `tree-support-routing.md` |

<!-- source: ECharts option manual (series-treemap) + examples gallery treemap family -->