# Vendor Selection Scorecard — Row-by-Criterion Comparison (Infographic)

**Best for**: comparing two or three vendors across the criteria that actually decide the purchase
**Avoid when**: there is a single veto criterion (say so in prose instead)
**Answers**: which vendor wins each criterion, and where the decision is genuinely close

```infographic
infographic compare-hierarchy-row-letter-card-compact-card
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
  title Vendor Shortlist — Observability
  desc Scored on the criteria in our procurement policy
  compares
    - label VendorA
      desc On-prem option, higher cost
      children
        - label Data residency
          desc EU region native
        - label Cost at 5TB/day
          desc $41K per year
        - label Migration effort
          desc 6 weeks
    - label VendorB
      desc Best tooling, no residency
      children
        - label Data residency
          desc US only today
        - label Cost at 5TB/day
          desc $28K per year
        - label Migration effort
          desc 3 weeks
```

## Data Shape

`compares` holds one entry per vendor; each vendor's `children` are the criteria rows. Keep the **same
criteria in the same order** for every vendor — the whole point is vertical comparability.

## Key Options

| Option | Effect |
|---|---|
| `infographic compare-hierarchy-row-letter-card-compact-card` | Letter-marked columns with compact criterion cards |
| `compare-hierarchy-row-letter-card-rounded-rect-node` | Same layout, softer node styling |
| `compare-swot` | Use when the comparison is qualitative (strengths/risks) rather than scored |

## Pitfalls

- ❌ Different criteria per vendor → ✅ identical rows make differences visible
- ❌ Hiding the awkward criterion → ✅ data residency is exactly the row the reader needs
- ❌ Four or more vendors → ✅ past three columns, switch to a scored table

## Alternatives

| Variant | Use instead |
|---|---|
| Two-option build/buy decision | `buy-vs-build-comparison.md` |
| Four-quadrant prioritisation | `backlog-priority-quadrant.md` |
| Market entry strengths and risks | `market-entry-swot.md` |

<!-- source: AntV Infographic syntax docs + template list (`compare-hierarchy-row-letter-card-compact-card`) -->
