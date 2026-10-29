# Funnel Conversion — Stage Drop-Off (Infographic)

**Best for**: a stylized conversion funnel where the message is stage attrition rather than analytical axis control
**Avoid when**: the reader needs exact comparative bars, branching paths, or multiple funnels in one frame
**Answers**: where the biggest drop happens, and how much volume survives to each step

```infographic
infographic sequence-filter-mesh-simple
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
  title Conversion Funnel
  desc Trial sign-ups to paid accounts over one quarter
  sequences
    - label Visits
      value 120000
      desc Top-of-funnel traffic
    - label Trials
      value 18000
      desc Visitors who started evaluation
    - label Qualified
      value 5200
      desc Accounts that matched target profile
    - label Paid
      value 1100
      desc Converted paying customers
```

## Data Shape

Use an ordered `sequences` array with a numeric `value` for each stage and a short description that explains what the stage means.

## Key Options

| Option | Effect |
|---|---|
| `sequence-filter-mesh-simple` | Funnel-style sequence layout |
| `value` | Supplies the magnitude used to size or emphasize each stage |
| Ordered `sequences` | Preserves the progression from largest stage to smallest |

## Pitfalls

- ❌ Unordered categories in a funnel → ✅ funnel stages must describe a real progression
- ❌ Branching or merging paths → ✅ use sankey or another flow view instead
- ❌ Too many stages → ✅ the message weakens once the funnel turns into a long staircase

## Alternatives

| Variant | Use instead |
|---|---|
| Analytical funnel with chart control | `funnel-stage-conversion.md` |
| Branching flow | `sankey-channel-to-fulfilment.md` |
| Time-phased milestones | `platform-milestone-timeline.md` |

<!-- source: AntV Infographic template reference (`sequence-filter-mesh-simple`) + syntax docs for sequences/value -->