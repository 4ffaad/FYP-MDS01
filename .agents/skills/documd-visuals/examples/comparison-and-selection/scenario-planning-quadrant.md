# Scenario Planning Quadrant — Invest / Protect / Test / Exit (Infographic)

**Best for**: a portfolio view where each business line gets one of four capital decisions
**Avoid when**: the reader needs forecasts or budget totals (pair it with a table)
**Answers**: where we double down, what we defend, what we experiment with, and what we stop funding

```infographic
infographic compare-quadrant-quarter-circular
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
  title Portfolio Review 2027
  desc Each line of business gets one capital decision
  compares
    - label Invest
      desc Growing share, strong margin
      children
        - label Usage-based billing
    - label Protect
      desc Core revenue at stake
      children
        - label Retainer plans
    - label Test
      desc Cheap to trial, unclear upside
      children
        - label AI add-ons
    - label Exit
      desc Shrinking, high cost to serve
      children
        - label Legacy licensing
```

## Data Shape

Four `compares` entries, each with a decision `label`, the rule that produced it in `desc`, and the
business lines in `children`. Direction of reading matters: the first two slots are the "keep" half,
the last two the "change" half.

## Key Options

| Option | Effect |
|---|---|
| `infographic compare-quadrant-quarter-circular` | Rounded quarter shapes; reads as a strategic radar |
| `compare-quadrant-quarter-simple-card` | Same structure with flat cards — more sober |
| `children` | Name the actual business lines, not abstract categories |

## Pitfalls

- ❌ Decision labels that restate the axes ("High growth") → ✅ state the action ("Invest", "Exit")
- ❌ Forgetting the exit quadrant → ✅ an empty exit quadrant means nobody made a hard call
- ❌ Long explanations inside quadrants → ✅ the decision rule belongs in the slot `desc`

## Alternatives

| Variant | Use instead |
|---|---|
| Two-option decision | `buy-vs-build-comparison.md` |
| Marketing entry analysis | `market-entry-swot.md` |
| Business cycle that repeats | `operating-cycle-loop.md` |

<!-- source: AntV Infographic syntax docs + template list (`compare-quadrant-quarter-circular`) -->
