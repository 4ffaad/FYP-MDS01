# Sunburst — Hierarchical Share Across Lifecycle Stages (ECharts)

**Best for**: hierarchical composition where the reader should see both parent and child shares in concentric rings
**Avoid when**: exact numeric comparison matters more than hierarchy, or there are too many tiny leaf segments to label clearly
**Answers**: how the total is divided across levels, and which branches dominate inside each parent category

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 860,
  "height": 420,
  "title": { "text": "Lifecycle Revenue Share", "subtext": "Recurring revenue by customer stage and motion", "left": "left" },
  "series": [
    {
      "type": "sunburst",
      "center": ["52%", "58%"],
      "radius": [0, "74%"],
      "sort": null,
      "itemStyle": { "borderColor": "rgba(255,255,255,0.85)", "borderWidth": 1 },
      "label": { "rotate": "radial" },
      "levels": [
        {},
        { "r0": "0%", "r": "28%", "label": { "rotate": 0 } },
        { "r0": "28%", "r": "54%" },
        { "r0": "54%", "r": "74%" }
      ],
      "data": [
        {
          "name": "Acquire",
          "children": [
            { "name": "Self-serve", "value": 28 },
            { "name": "Partner-led", "value": 18 }
          ]
        },
        {
          "name": "Expand",
          "children": [
            { "name": "Cross-sell", "value": 24 },
            { "name": "Upsell", "value": 22 }
          ]
        },
        {
          "name": "Retain",
          "children": [
            { "name": "Renewal", "value": 30 },
            { "name": "Rescue", "value": 12 }
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
| `radius` | Controls how much room the ring hierarchy gets relative to the title and margins |
| `levels` | Lets each ring depth use different radius bands and label behaviour |
| `sort: null` | Preserves the authored sibling order instead of letting ECharts reorder by value |
| `label.rotate: "radial"` | Keeps ring labels aligned with the segment direction |
| Nested `children` | Encodes parent and child share in the same structure |

## Data Shape

Nested `children` arrays, with values at the leaves. Each ring level is one hierarchy depth, so the structure needs to stay shallow enough for the labels to survive export.

## Pitfalls

- ❌ Tiny slices on outer rings → ✅ labels become noise; collapse minor segments into an "Other" bucket when needed
- ❌ Expecting exact value comparisons from curved areas → ✅ use bars if precision matters
- ❌ Letting ECharts reorder siblings unexpectedly → ✅ set `sort: null` when your narrative depends on the original order
- ❌ Deep taxonomies in one sunburst → ✅ static charts need hierarchy restraint more than interactive ones do

## Alternatives

| Variant | Use instead |
|---|---|
| Rectangular hierarchy | `treemap-portfolio-breakdown.md` |
| Flat share of total | `donut-channel-mix.md` |
| Process stages over time | bars or lines |

<!-- source: ECharts option manual (series-sunburst) + examples gallery sunburst family -->