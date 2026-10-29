# Option Map — Hierarchical Comparison (Infographic)

**Best for**: comparing two option families where each side has a few structured sub-dimensions rather than flat bullets
**Avoid when**: the comparison is purely numeric or the reader needs more than two top-level options
**Answers**: how the two option groups are structured, and which sub-areas belong under each one

```infographic
infographic compare-hierarchy-left-right-circle-node-plain-text
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
  title Operating Model Options
  desc Two structured options with distinct capability groupings
  compares
    - label Central Platform
      children
        - label Shared Tooling
        - label Policy Control
        - label Standardized Release Flow
    - label Federated Product Teams
      children
        - label Local Ownership
        - label Flexible Delivery Cadence
        - label Domain-Specific Tooling
```

## Data Shape

Use `compares` with two top-level options, each containing a small `children` set for its sub-structure.

## Key Options

| Option | Effect |
|---|---|
| `compare-hierarchy-left-right-circle-node-plain-text` | Structured left/right comparison rather than a flat A/B list |
| Nested `children` | Shows the decomposition under each compared side |
| Simple labels | Keeps the hierarchy readable inside the comparison layout |

## Pitfalls

- ❌ Using long descriptions for every child node → ✅ this pattern works best with compact labeled dimensions
- ❌ Comparing many top-level options in a binary hierarchy template → ✅ keep it to two structured choices
- ❌ Treating it as a numeric score model | ✅ it is a structural framing artifact |

## Alternatives

| Variant | Use instead |
|---|---|
| Flat pros/cons A vs B | `buy-vs-build-comparison.md` |
| SWOT framing | `market-entry-swot.md` |
| Rich table comparison | `decision-comparison-card.md` |

<!-- source: AntV Infographic template reference (`compare-hierarchy-left-right-circle-node-plain-text`) + syntax docs for compares/children -->