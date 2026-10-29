# Service Lifecycle Wheel — Propose To Retire (Infographic)

**Best for**: showing that a service has a lifecycle, including an exit
**Avoid when**: the reader needs current service health (use a status board)
**Answers**: the four phases of a service and what a go/no-go decision looks like at each

```infographic
infographic sequence-circle-arrows-indexed-card
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
  title Service Lifecycle
  desc Numbered phases with a return arrow
  sequences
    - label Propose
      desc Business case and owner named
    - label Pilot
      desc One region, measured against success criteria
    - label Scale
      desc Global rollout with platform support
    - label Retire
      desc Data exported, consumers migrated
```

## Data Shape

`sequences` of four to five phases. Indexed cards show the numbering, so the order must be meaningful; the
circular structure implies the cycle continues with new services.

## Key Options

| Option | Effect |
|---|---|
| `infographic sequence-circle-arrows-indexed-card` | Numbered cards on a ring — reads as a closed loop |
| `sequence-circular-simple` | Ring without numbering; use when phases are qualitative |
| `sequence-lifecycle` alternatives: `sequence-steps-*` | Use when the process is linear, not cyclical |

## Pitfalls

- ❌ Omitting the retire phase → ✅ a lifecycle without an exit is just a launch funnel
- ❌ Phases that repeat yearly → ✅ if the loop is a cadence, use `operating-cycle-loop.md`
- ❌ Five-plus phases on a ring → ✅ rings hold four comfortably, five at most

## Alternatives

| Variant | Use instead |
|---|---|
| Repeating operating cadence | `operating-cycle-loop.md` |
| Quarterly planning rhythm | `quarterly-planning-cycle.md` |
| Feature adoption over time | `feature-adoption-trend.md` |

<!-- source: AntV Infographic syntax docs + template list (`sequence-circle-arrows-indexed-card`) -->
