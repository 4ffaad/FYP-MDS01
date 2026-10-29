# Cost Structure Split — Cloud Spend By Category (Infographic)

**Best for**: an infrastructure review where the categories are the decision levers
**Avoid when**: the reader needs month-over-month movement (use bars or a line)
**Answers**: how spend divides across categories, and which category dominates

```infographic
infographic chart-pie-pill-badge
theme
  colorPrimary #2b66c4
  palette
    - #2b66c4
    - #2f9e44
    - #f3a33c
    - #d1242f
    - #7048e8
    - #0f9b9b
    - #c16f8a
    - #7c5a3d
data
  title Monthly Cloud Spend
  desc $412K total, August
  values
    - label Compute
      value 186
    - label Storage
      value 94
    - label Databases
      value 71
    - label Egress
      value 38
    - label Observability
      value 23
```

## Data Shape

`values` in the **same unit** (here thousands of dollars). Badge labels are compact, so keep category names to
one or two words and put the absolute amount in `desc` if needed.

## Key Options

| Option | Effect |
|---|---|
| `infographic chart-pie-pill-badge` | Compact badge labels around the pie |
| `chart-pie-compact-card` | Cards when each slice needs a sentence |
| `chart-pie-donut-pill-badge` | Donut variant — leaves the centre free for a total |

## Pitfalls

- ❌ Percentages and dollars mixed → ✅ pick one; mixed units break the slice maths
- ❌ Egress ignored → ✅ data transfer is where surprise bills live
- ❌ Showing spend without a target → ✅ add the budget line in the surrounding text

## Alternatives

| Variant | Use instead |
|---|---|
| Cost reduction lever bridge | `cost-reduction-waterfall.md` |
| Spend allocation across programmes | `budget-allocation-donut.md` |
| Capacity versus cost over time | `capacity-cost-dual-axis.md` (vega-lite) |

<!-- source: AntV Infographic syntax docs + template list (`chart-pie-pill-badge`) -->
