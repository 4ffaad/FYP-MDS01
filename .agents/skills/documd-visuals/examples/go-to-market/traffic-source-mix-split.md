# Traffic Source Mix — Where Sessions Come From (Infographic)

**Best for**: a marketing snapshot where the split matters more than the trend
**Avoid when**: the reader needs volume over time (use a line chart)
**Answers**: the share each acquisition source contributes, with the definition on the card

```infographic
infographic chart-pie-compact-card
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
  title Session Sources — August
  desc Definitions travel with each slice
  values
    - label Organic search
      value 42
    - label Direct
      value 26
    - label Paid social
      value 18
    - label Referral
      value 9
    - label Email
      value 5
```

## Data Shape

`values` with numbers that sum to a meaningful whole (here, percentages of sessions). Definitions belong in
`desc`; the compact-card variant keeps them visible next to the slice.

## Key Options

| Option | Effect |
|---|---|
| `infographic chart-pie-compact-card` | Slices with descriptive cards |
| `chart-pie-pill-badge` | Badge labels — tighter, good for five slices |
| `chart-pie-plain-text` | No cards at all; quietest option |

## Pitfalls

- ❌ Mixed units (sessions and revenue in one pie) → ✅ one unit per chart
- ❌ Ten slices → ✅ group the tail into "Other" past five slices
- ❌ Using it for growth → ✅ pies show composition, not change

## Alternatives

| Variant | Use instead |
|---|---|
| Cost categories rather than traffic | `cost-structure-split.md` |
| Revenue by region | `regional-revenue-split.md` |
| Channel efficiency comparison | `channel-performance-comparison.md` |

<!-- source: AntV Infographic syntax docs + template list (`chart-pie-compact-card`) -->
