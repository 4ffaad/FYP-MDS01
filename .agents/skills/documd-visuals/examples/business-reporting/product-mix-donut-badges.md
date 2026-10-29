# Product Mix Donut — Which Lines Carry The Quarter (Infographic)

**Best for**: a portfolio review that needs product-line contribution at a glance
**Avoid when**: lines have negative or zero values (pies cannot show them)
**Answers**: each product line's contribution and how concentrated the portfolio is

```infographic
infographic chart-pie-donut-pill-badge
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
  title Revenue Mix By Product Line
  desc Two lines carry two-thirds of revenue
  values
    - label Subscriptions
      value 46
    - label Usage
      value 27
    - label Services
      value 17
    - label Marketplace
      value 10
```

## Data Shape

`values` in percentages or currency — this example uses percentage of total. With a donut the centre stays
open, which suits a headline callout like "top two lines = 73%".

## Key Options

| Option | Effect |
|---|---|
| `infographic chart-pie-donut-pill-badge` | Donut with compact badges |
| `chart-pie-donut-plain-text` | Neutral text labels for finance audiences |
| `chart-pie-donut-compact-card` | Cards when each line needs a note |

## Pitfalls

- ❌ Adding an "other" slice for a single line → ✅ name the line if it is material
- ❌ Mixing recurring and one-off revenue → ✅ if Services is one-off, say so
- ❌ Reading it as growth → ✅ composition only; the trend belongs in a separate chart

## Alternatives

| Variant | Use instead |
|---|---|
| Regional split instead of product | `regional-revenue-split.md` |
| Spend split instead of revenue | `cost-structure-split.md` |
| Plan stepping up by quarter | `revenue-staircase-plan.md` |

<!-- source: AntV Infographic syntax docs + template list (`chart-pie-donut-pill-badge`) -->
