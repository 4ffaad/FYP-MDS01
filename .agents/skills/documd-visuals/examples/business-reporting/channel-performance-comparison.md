# Channel Performance Comparison — Same Metrics, Three Channels (Infographic)

**Best for**: putting acquisition channels side by side on identical metrics
**Avoid when**: channels are measured on different scales or windows
**Answers**: which channel is efficient, which is growing, and which needs intervention

```infographic
infographic compare-hierarchy-row-letter-card-rounded-rect-node
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
  title Acquisition Channel Review
  desc Same three metrics, same 90-day window
  compares
    - label Paid Search
      desc Highest volume, rising cost
      children
        - label New customers
          desc 2,140
        - label Cost per signup
          desc $38
        - label 90-day retention
          desc 71%
    - label Partner Referrals
      desc Smaller, cheapest, stickiest
      children
        - label New customers
          desc 860
        - label Cost per signup
          desc $12
        - label 90-day retention
          desc 88%
    - label Content
      desc Slow compounding
      children
        - label New customers
          desc 1,180
        - label Cost per signup
          desc $21
        - label 90-day retention
          desc 79%
```

## Data Shape

One `compares` entry per channel, each with three `children` rows using the **same labels**. Units live in
the `desc` (`$38`, `71%`) because this structure renders text, not axes.

## Key Options

| Option | Effect |
|---|---|
| `infographic compare-hierarchy-row-letter-card-rounded-rect-node` | Rounded nodes; gentler than compact cards |
| `compare-hierarchy-row-letter-card-compact-card` | Denser variant for longer labels |
| `compare-hierarchy-left-right-circle-node-plain-text` | Use when each side is one block of prose, not rows |

## Pitfalls

- ❌ Mixed units without labels → ✅ write `$38` and `71%`, the reader cannot infer them
- ❌ Winner-by-count only → ✅ partner referrals win on efficiency despite lower volume; say so
- ❌ More than four metrics → ✅ beyond four rows this collapses into a table

## Alternatives

| Variant | Use instead |
|---|---|
| Trend of one metric over time | `feature-adoption-trend.md` |
| Share-of-total split | `regional-revenue-split.md` |
| Ordered funnel with drop-off | `conversion-funnel-journey.md` |

<!-- source: AntV Infographic syntax docs + template list (`compare-hierarchy-row-letter-card-rounded-rect-node`) -->
