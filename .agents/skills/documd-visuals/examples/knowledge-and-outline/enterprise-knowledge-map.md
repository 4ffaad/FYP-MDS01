# Enterprise Knowledge Map — Mindmap Of A Domain (Infographic)

**Best for**: an explorable map of one domain, spreading outward instead of downward
**Avoid when**: the reader must trace a single path (use a sequence)
**Answers**: what the domain contains, and how the parts hang off the central idea

```infographic
infographic
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
design
  structure hierarchy-mindmap
  item rounded-rect-node
data
  title Payments Domain Map
  desc Central topic with two levels of concepts
  root
    label Payments
    children
      - label Authorization
        children
          - label Fraud rules
          - label 3-D Secure
      - label Capture
        children
          - label Partial capture
      - label Settlement
        children
          - label Payouts
          - label Reconciliation
```

## Data Shape

`root` plus `children`; the mindmap places nodes radially, so wide-but-shallow (two levels, three to four
branches) reads far better than a deep chain.

## Key Options

| Option | Effect |
|---|---|
| `design structure hierarchy-mindmap` | Radial layout around the root topic |
| `design item rounded-rect-node` | Boxed leaves; `plain-text` gives a lighter, sketched feel |
| `hierarchy-structure` template | Use when a left-to-right outline is enough |

## Pitfalls

- ❌ Deep chains (five levels) → ✅ mindmaps fan out; convert deep chains into a tree
- ❌ Missing that the mindmap reserves a **fixed wide canvas** (measured 2086 px wide regardless of item count)
  → ✅ treat it as a wide hero image; for a portrait page use `hierarchy-structure` or a list layout instead
- ❌ Sentence-long leaves → ✅ two or three words per node, detail belongs in the surrounding doc

## Alternatives

| Variant | Use instead |
|---|---|
| Strict three-level decomposition | `department-capability-tree.md` |
| Concept relationships, not containment | `capability-relationship-map.md` |
| Ordered learning path | `certification-study-roadmap.md` |

<!-- source: AntV Infographic syntax docs + structure registry (`hierarchy-mindmap`) -->
