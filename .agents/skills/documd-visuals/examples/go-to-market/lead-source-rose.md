# Rose Chart — Lead Sources by Volume and Win Rate (ECharts)

**Best for**: a single-period split where the "winner" should dominate visually, not just numerically
**Avoid when**: the reader must compare slices precisely, or the values are close together
**Answers**: which acquisition channels carry the pipeline, and how concentrated the mix is

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 760,
  "height": 520,
  "title": { "text": "Pipeline by Lead Source", "subtext": "Rose chart — radius encodes volume, so large channels are emphasised", "left": "left" },
  "legend": { "data": ["Reseller partners", "OEM partners", "Outbound", "Website", "Community", "Events"], "bottom": 0 },
  "series": [
    {
      "name": "Lead source",
      "type": "pie",
      "roseType": "radius",
      "radius": ["14%", "74%"],
      "center": ["50%", "52%"],
      "itemStyle": { "borderRadius": 6 },
      "label": { "show": true, "formatter": "{b}\n{d}%" },
      "labelLine": { "length": 10, "length2": 12 },
      "data": [
        { "value": 420, "name": "Reseller partners" },
        { "value": 310, "name": "OEM partners" },
        { "value": 240, "name": "Outbound" },
        { "value": 180, "name": "Website" },
        { "value": 120, "name": "Community" },
        { "value": 60, "name": "Events" }
      ]
    }
  ]
}
```

## Data Shape

One row per slice: `value` drives both the sector angle and the petal length, `name` supplies the label. With
`roseType: "radius"` the angle and the radius encode the **same** field, which is exactly why the chart is
read as "big stays big".

## Key Options

| Option | Effect |
|---|---|
| `roseType: "radius"` | Both angle and radius follow the value — the classic Nightingale look |
| `roseType: "area"` | Keeps the angle proportional to the value and only the radius moves; a gentler variant |
| `radius: ["14%", "74%"]` | An inner radius leaves the centre free so labels do not collide with the smallest petals |
| `itemStyle.borderRadius` | Rounds each petal; with dense mixes it keeps neighbouring petals legible |
| `label.formatter: "{b}\n{d}%"` | Names the slice and its share on two lines with a built-in template — no callback needed |

## Pitfalls

- ❌ Reading a rose like a normal pie → ✅ in the `radius` variant the angle is still proportional, but the *area* overstates large values; say so in the subtitle when the exaggeration is deliberate
- ❌ Comparing near-equal slices → ✅ the eye cannot rank petals; use a bar chart when the ranking is the point
- ❌ Two data items with the same `name` → ✅ they render as separate petals but collapse into one legend entry; split the names or merge the values
- ❌ Many tiny slices plus `roseType: "radius"` → ✅ small values shrink into unreadable slivers; group them into "Other"

## Alternatives

| Variant | Use instead |
|---|---|
| Precise ranking of the same channels | `comparison-bars.md` |
| A flat share of a small total | `donut-channel-mix.md` |
| Nesting the mix under a second dimension | `cloud-spend-nested-pie.md` |

<!-- source: ECharts option manual (series-pie roseType / radius / label) + the pie how-to page on rose charts -->
