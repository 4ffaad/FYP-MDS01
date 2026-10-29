# Chord — Cross-Team Handoffs (ECharts)

**Best for**: showing bidirectional relationship strength between a small set of peer groups
**Avoid when**: the flow is directional by stage or needs an explicit process sequence (use sankey or lines)
**Answers**: which groups exchange the most work, where the strongest pairings sit, and which groups are relatively isolated

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 860,
  "height": 420,
  "title": { "text": "Cross-Team Handoffs", "subtext": "Weekly ticket transfer volume", "left": "left" },
  "series": [
    {
      "type": "chord",
      "radius": ["34%", "68%"],
      "center": ["50%", "58%"],
      "clockwise": false,
      "sort": "descending",
      "sortSub": "descending",
      "label": { "show": true, "fontSize": 11 },
      "lineStyle": { "color": "target", "opacity": 0.55, "width": 1 },
      "data": [
        { "name": "Core" },
        { "name": "Billing" },
        { "name": "Support" },
        { "name": "Identity" },
        { "name": "Data" }
      ],
      "links": [
        { "source": "Core", "target": "Billing", "value": 32 },
        { "source": "Core", "target": "Support", "value": 24 },
        { "source": "Core", "target": "Identity", "value": 18 },
        { "source": "Core", "target": "Data", "value": 12 },
        { "source": "Billing", "target": "Support", "value": 16 },
        { "source": "Billing", "target": "Data", "value": 14 },
        { "source": "Support", "target": "Identity", "value": 10 },
        { "source": "Support", "target": "Data", "value": 12 },
        { "source": "Identity", "target": "Data", "value": 6 }
      ]
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `series.type: "chord"` | Encodes pairwise relationship strength in a circular matrix form |
| `links` | Supplies the relationship list directly, which is the simpler official pattern |
| `sort` / `sortSub` | Keeps the strongest arcs grouped more readably |
| `radius` / `center` | Reserves enough whitespace for labels around the ring |
| `lineStyle.opacity` | Prevents dense ribbons from turning into a solid blob |

## Data Shape

One `data` array naming each group, plus `links[{ source, target, value }]` describing the strongest relationships between them.

## Pitfalls

- ❌ Too many entities → ✅ chord diagrams saturate quickly; keep the set small
- ❌ Treating the matrix as directional stages → ✅ chord is about peer-to-peer strength, not sequence
- ❌ Mixing weak incidental links with the main structure → ✅ aggregate or drop minor ribbons so the ring stays readable
- ❌ Weak relationships left unaggregated → ✅ tiny ribbons clutter the ring and add little value

## Alternatives

| Variant | Use instead |
|---|---|
| Directional staged flow | `sankey-channel-to-fulfilment.md` |
| Fixed-path links on a plane | `lines-route-flows.md` |
| General dependency network | `graph-platform-dependencies.md` |

<!-- source: ECharts option manual (series-chord) + v6 chord examples -->