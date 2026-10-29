# Capability Pyramid Framework — Foundation To Differentiator (Infographic)

**Best for**: explaining which capabilities are table stakes and which ones create advantage
**Avoid when**: capabilities are all equally strategic (a grid fits better)
**Answers**: what must exist before higher-level capabilities can be built

```infographic
infographic list-pyramid-badge-card
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
  title Deliverability Capabilities
  desc Foundation at the base, differentiators at the top
  lists
    - label Differentiators
      desc Real-time routing intelligence
    - label Advantages
      desc Multi-region failover
    - label Enablers
      desc Unified event pipeline
    - label Foundation
      desc Identity and access control
```

## Data Shape

`lists` in top-down order: top item is the narrow apex. Each `label` names a tier, `desc` names the
representative capability. Four tiers is the sweet spot.

## Key Options

| Option | Effect |
|---|---|
| `infographic list-pyramid-badge-card` | Badge tiers, reads as a stack of levels |
| `list-pyramid-rounded-rect-node` | Flat nodes; useful for printed one-pagers |
| `list-pyramid-compact-card` | Tighter cards when tier names are long |

## Pitfalls

- ❌ Tiers that overlap ("Platform", "Core") → ✅ tiers should imply build order
- ❌ More than one capability per tier → ✅ pick the most representative; lists belong in a grid
- ❌ Using this for prioritisation → ✅ a pyramid shows dependency, a quadrant shows priority

## Alternatives

| Variant | Use instead |
|---|---|
| Capability ownership by team | `department-capability-tree.md` |
| Capability relationships between systems | `capability-relationship-map.md` |
| Maturity over time | `reliability-maturity-ladder.md` |

<!-- source: AntV Infographic syntax docs + template list (`list-pyramid-badge-card`) -->
