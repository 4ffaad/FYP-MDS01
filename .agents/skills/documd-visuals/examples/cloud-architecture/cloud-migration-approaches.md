# Cloud Migration Approaches — Lift And Shift Or Refactor (Infographic)

**Best for**: an architecture decision page where two migration routes compete
**Avoid when**: the routes are sequential, not alternative (use a sequence)
**Answers**: what each approach optimises for, and which risks it carries

```infographic
infographic compare-binary-horizontal-simple-arrow
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
  title Migration Route Decision
  desc Both routes reach the same target platform
  compares
    - label Lift and shift
      desc Move as-is, then improve
      children
        - label Fastest path off the old estate
        - label Unchanged operational risk
        - label Carries legacy constraints forward
    - label Refactor as you go
      desc Change architecture during the move
      children
        - label Pays down technical debt
        - label Needs parallel expert capacity
        - label Slower, higher change risk
```

## Data Shape

Two `compares` entries with three arguments each. This variant renders the two sides with an arrow between
them, which suits "choose a route" framing.

## Key Options

| Option | Effect |
|---|---|
| `infographic compare-binary-horizontal-simple-arrow` | Arrow between plain-text sides |
| `compare-binary-horizontal-badge-card-arrow` | Badge styling for a slide deck |
| `compare-binary-horizontal-compact-card-fold` | Compact cards in a folded column layout |

## Pitfalls

- ❌ Naming a winner in the diagram → ✅ let the arguments decide; state the call in prose
- ❌ Route names that are marketing slogans → ✅ describe the mechanism, not the vibe
- ❌ Hidden cost of the faster route → ✅ legacy constraints are the usual sting

## Alternatives

| Variant | Use instead |
|---|---|
| Build or buy instead of migrate | `buy-vs-build-comparison.md` |
| Ship-now versus harden-first | `release-plan-tradeoff-fold.md` |
| Cutover execution order | `migration-cutover-window.md` |

<!-- source: AntV Infographic syntax docs + template list (`compare-binary-horizontal-simple-arrow`) -->
