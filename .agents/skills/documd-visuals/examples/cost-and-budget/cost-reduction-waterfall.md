# Cost Reduction Waterfall — Where The Savings Come From (Infographic)

**Best for**: presenting a savings programme as a bridge from current to target cost
**Avoid when**: savings are still estimates with wide ranges (say so in prose instead)
**Answers**: which levers deliver the reduction, and how much each contributes

```infographic
infographic list-waterfall-badge-card
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
  title Run-Rate Cost Bridge
  desc From $6.8M to $5.2M annualised
  lists
    - label Current run rate
      desc $6.80M
    - label Vendor consolidation
      desc -$0.62M
    - label Storage tiering
      desc -$0.41M
    - label Idle capacity
      desc -$0.35M
    - label Contract renegotiation
      desc -$0.22M
    - label Target run rate
      desc $5.20M
```

## Data Shape

Same waterfall contract as any bridge: opening level, signed movements, closing level. Six items is the
practical maximum before the steps get too small to read.

## Key Options

| Option | Effect |
|---|---|
| `infographic list-waterfall-badge-card` | Badge steps; legible with short labels |
| `list-waterfall-compact-card` | Cards with room for a longer qualifier |
| `compare-hierarchy-row-*` | Use when savings are per-vendor rather than per-lever |

## Pitfalls

- ❌ Levers that overlap (storage tiering inside vendor consolidation) → ✅ one lever per step, or say "included in"
- ❌ Missing the closing level → ✅ a bridge without an endpoint is not a decision
- ❌ Showing only the biggest lever → ✅ small levers are what make the target achievable

## Alternatives

| Variant | Use instead |
|------|------|
| Budget consumption over a year | `budget-drawdown-waterfall.md` |
| Cost split by category | `cost-structure-split.md` |
| Capacity cost trade-off | `capacity-cost-dual-axis.md` (vega-lite) |

<!-- source: AntV Infographic syntax docs + template list (`list-waterfall-badge-card`) -->
