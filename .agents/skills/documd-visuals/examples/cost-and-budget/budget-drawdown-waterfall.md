# Budget Drawdown Waterfall — From Approval To Remaining (Infographic)

**Best for**: showing how an approved budget is consumed line by line
**Avoid when**: the reader needs time-series spend (use a chart)
**Answers**: what was approved, what each commitment consumed, and what is left

```infographic
infographic list-waterfall-compact-card
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
  title Platform Budget Drawdown
  desc Approved to remaining, FY27
  lists
    - label Approved budget
      desc $2.40M
    - label Platform work
      desc -$0.64M
    - label Vendor renewals
      desc -$0.31M
    - label Remaining
      desc $1.45M
```

## Data Shape

`lists` where the **first item is the starting level** and the **last item is the closing level**; middle
items are the movements, written as signed amounts so the direction is unambiguous.

## Key Options

| Option | Effect |
|---|---|
| `infographic list-waterfall-compact-card` | Stepped cards descending like a waterfall |
| `list-waterfall-badge-card` | Badge variant for shorter labels |
| `list-pyramid-*` | Use only if the reader should read levels, not flows |

## Pitfalls

- ❌ Unsigned movements → ✅ always write `-$0.64M`; the waterfall is about direction
- ❌ Adding a "total" row that double counts → ✅ closing balance only, once
- ❌ Using it for year-over-year comparison → ✅ waterfalls decompose one number, they do not compare periods

## Alternatives

| Variant | Use instead |
|--------|------|
| Spend over time | `budget-allocation-donut.md` |
| Cost reduction programme | `cost-reduction-waterfall.md` |
| Headcount plan as levels | `team-capacity-ramp.md` |

<!-- source: AntV Infographic syntax docs + template list (`list-waterfall-compact-card`) -->
