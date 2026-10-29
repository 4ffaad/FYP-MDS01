# Growth Experiment Loop — Hypothesis To Scale (Infographic)

**Best for**: a growth team documenting the loop every experiment follows
**Avoid when**: the reader wants experiment results (link the dashboard)
**Answers**: the four steps of the loop, and the artefact each step produces

```infographic
infographic sequence-zigzag-pucks-3d-indexed-card
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
  title Experiment Loop
  desc Numbered steps around a repeating cycle
  sequences
    - label Hypothesis
      desc Funnel drop at step two
    - label Design
      desc One-week test with a control
    - label Measure
      desc Lift against the control group
    - label Scale or kill
      desc Roll out, or write the learning down
```

## Data Shape

`sequences` of four; the indexed pucks show step numbers and the zigzag alternates depth, so uneven step
counts look wrong — use exactly four or six.

## Key Options

| Option | Effect |
|---|---|
| `infographic sequence-zigzag-pucks-3d-indexed-card` | Numbered 3-D pucks on a zigzag |
| `sequence-zigzag-steps-underline-text` | Flat variant when 3-D styling is too playful |
| `sequence-zigzag-pucks-3d-simple` | Same shape without index numbers |

## Pitfalls

- ❌ Ending at "Measure" → ✅ every loop needs a decision step, even a negative one
- ❌ No control group mentioned → ✅ the measurement step is meaningless without a baseline
- ❌ Ten experiments on one diagram → ✅ this shows the loop, not the backlog

## Alternatives

| Variant | Use instead |
|---|---|
| Feature adoption after launch | `feature-adoption-trend.md` |
| Product roadmap by quarter | `product-roadmap-sequence.md` |
| Rank movement across periods | `rank-movement-over-time.md` (vega-lite) |

<!-- source: AntV Infographic syntax docs + template list (`sequence-zigzag-pucks-3d-indexed-card`) -->
