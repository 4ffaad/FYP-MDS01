# Backlog Priority Quadrant — Impact vs Effort (Infographic)

**Best for**: sorting a messy initiative list into four action groups the reader can act on
**Avoid when**: every item has the same impact/effort rating, or ranking must be numeric (use a scored table)
**Answers**: which work we start now, which we schedule, which we hand to an intern, and which we drop

```infographic
infographic compare-quadrant-quarter-simple-card
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
  title Q3 Backlog Triage
  desc 12 open initiatives sorted by impact and effort
  compares
    - label Do Now
      desc High impact, low effort
      children
        - label Fix signup validation
        - label Cache pricing API
    - label Schedule
      desc High impact, high effort
      children
        - label Billing service split
    - label Hand Off
      desc Low impact, low effort
      children
        - label Refresh help screenshots
    - label Drop
      desc Low impact, high effort
      children
        - label Custom report builder
```

## Data Shape

Use `compares` with exactly **four entries** — the quadrant slots, in reading order (top-left, top-right,
bottom-left, bottom-right). Each slot carries a `label`, a short `desc` naming the decision rule, and a
`children` list holding the items that landed there.

## Key Options

| Option | Effect |
|---|---|
| `infographic compare-quadrant-quarter-simple-card` | Four quarter cards; the plainest reading of a priority matrix |
| `compare-quadrant-quarter-circular` | Same data with curved quarter shapes — softer, more decorative |
| `compare-quadrant-simple-illus` | Adds illustration space inside each quadrant |
| `children` | The items placed in that quadrant; keep to 2–3 per slot |

## Pitfalls

- ❌ Slot labels like "Q1 / Q2 / Q3 / Q4" → ✅ name the decision ("Do Now", "Schedule", "Drop")
- ❌ Packing ten items into one quadrant → ✅ the visual argument is balance; 2–3 per slot reads instantly
- ❌ Using this for scoring → ✅ quadrants classify, they do not rank; use a scorecard when you need numbers

## Alternatives

| Variant | Use instead |
|---|---|
| Two-option trade-off instead of four | `buy-vs-build-comparison.md` |
| Initiative list with progress facts | `program-status-ribbons.md` |
| Ordered sequence of work over time | `product-roadmap-sequence.md` |

<!-- source: AntV Infographic syntax docs + template list (`compare-quadrant-quarter-simple-card`) -->
