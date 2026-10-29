# Tree — Support Routing Hierarchy (ECharts)

**Best for**: a single rooted hierarchy where the reader needs to understand structure and branching depth
**Avoid when**: nodes can have multiple parents, the structure is mostly quantitative, or the message is dependency density rather than hierarchy
**Answers**: how the hierarchy is organised, where branches split, and which items belong under each parent

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 1120,
  "height": 460,
  "title": { "text": "Support Routing Tree", "subtext": "Tiered ownership from intake to specialist teams", "left": "left" },
  "series": [
    {
      "type": "tree",
      "top": 96,
      "left": 80,
      "bottom": 36,
      "right": 240,
      "orient": "LR",
      "symbol": "emptyCircle",
      "symbolSize": 8,
      "label": { "position": "right", "verticalAlign": "middle", "align": "left", "fontSize": 11 },
      "leaves": { "label": { "position": "right", "align": "left", "fontSize": 11 } },
      "lineStyle": { "curveness": 0.45 },
      "expandAndCollapse": false,
      "initialTreeDepth": -1,
      "data": [
        {
          "name": "Support intake",
          "children": [
            {
              "name": "Account issues",
              "children": [
                { "name": "Password reset" },
                { "name": "SSO / login" }
              ]
            },
            {
              "name": "Billing issues",
              "children": [
                { "name": "Invoice query" },
                { "name": "Refund request" }
              ]
            },
            {
              "name": "Platform incidents",
              "children": [
                { "name": "Checkout failure" },
                { "name": "Search degradation" }
              ]
            }
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
| `orient: "LR"` | Uses horizontal reading order, which fits operational trees better than a tall top-down layout |
| `expandAndCollapse: false` | Keeps the static export deterministic; no branch depends on interaction to be visible |
| `initialTreeDepth: -1` | Expands the full hierarchy from the start |
| `label` vs `leaves.label` | Lets parent and leaf labels align differently for cleaner reading |
| `lineStyle.curveness` | Softens branches so siblings are easier to visually separate |

## Data Shape

One nested object tree under `data[0]`, where every node may have a `children` array. This chart assumes every node belongs to exactly one parent.

## Pitfalls

- ❌ Using a tree for a graph with shared children → ✅ trees require one parent per node; use `graph` for many-to-many links
- ❌ Depending on collapsed branches → ✅ static exports must show the full intended structure up front
- ❌ Very deep trees in a narrow frame → ✅ switch to a table or split the hierarchy into several charts
- ❌ Quantitative comparisons hidden in node text → ✅ if numbers are the message, use bars or treemaps instead

## Alternatives

| Variant | Use instead |
|---|---|
| Many-to-many routing | `graph` or `sankey` |
| Quantitative hierarchy | `treemap` or `sunburst` |
| Process flow with hand-offs | plantuml workflow / swimlane examples |

<!-- source: ECharts option manual (series-tree) + examples gallery tree family -->