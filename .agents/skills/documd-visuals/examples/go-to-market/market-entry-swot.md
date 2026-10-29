# SWOT — Market Entry Position (Infographic)

**Best for**: framing a strategic discussion across strengths, weaknesses, opportunities, and threats in one board
**Avoid when**: the reader needs weighted scoring or a decision recommendation with evidence tables
**Answers**: what helps, what hurts, and what external conditions shape the choice

```infographic
infographic compare-swot
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
  title Market Entry SWOT
  desc Expansion into a regulated mid-market segment
  compares
    - label Strengths
      children
        - label Brand trust
          desc Existing enterprise reputation
        - label Platform maturity
          desc Core workflows already proven
    - label Weaknesses
      children
        - label Limited field sales
          desc Small regional presence
        - label Pricing complexity
          desc Packaging still confusing
    - label Opportunities
      children
        - label Compliance demand
          desc Buyers need policy automation
        - label Partner channel
          desc Resellers can accelerate reach
    - label Threats
      children
        - label Local incumbents
          desc Faster procurement relationships
        - label Long evaluation cycles
          desc Budget sign-off takes longer
```

## Data Shape

Use `compares` with four top-level items named `Strengths`, `Weaknesses`, `Opportunities`, and `Threats`, each with `children` for the actual points.

## Key Options

| Option | Effect |
|---|---|
| `compare-swot` | Four-quadrant SWOT board |
| `compares` | Structured side-by-side comparison content |
| `children` | Lists the points under each quadrant |

## Pitfalls

- ❌ More or fewer than four SWOT quadrants → ✅ keep the canonical four-way frame
- ❌ Long paragraphs in each child item → ✅ use short evidence snippets, not essays
- ❌ Treating SWOT as a final decision → ✅ it frames discussion; it does not replace prioritization or scoring

## Alternatives

| Variant | Use instead |
|---|---|
| Direct A/B comparison | A binary compare template |
| Weighted choice matrix | Vega-Lite or HTML comparison table |
| Capability structure only | `platform-org-structure.md` |

<!-- source: AntV Infographic template reference (`compare-swot`) + syntax docs for compares/children -->