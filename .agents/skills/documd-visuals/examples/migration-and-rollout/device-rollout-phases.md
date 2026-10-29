# 3D Pucks — Device Rollout Phases (Infographic)

**Best for**: a short physical rollout plan where the stages are tangible objects, not abstract tasks
**Avoid when**: the steps are parallel workstreams (the zigzag implies one path) or there are more than six
**Answers**: what happens at each station of a hardware rollout, and how many devices move at each step

```infographic
infographic sequence-zigzag-pucks-3d-simple
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
  title Field Device Rollout
  desc Five stations from warehouse to handover
  sequences
    - label Stage
      desc 240 units staged in the regional warehouse
    - label Flash
      desc Firmware and tenant config written and verified
    - label Ship
      desc Couriers dispatched with per-site manifests
    - label Install
      desc On-site mounting, network join, smoke test
    - label Handover
      desc Local owner signs off on the asset record
```

## Data Shape

`sequences` with one entry per station, in travel order. Each entry carries a short `label` (the station name)
and a `desc` with the operational detail.

## Key Options

| Option | Effect |
|---|---|
| `sequence-zigzag-pucks-3d-simple` | Renders each step as a 3D puck on an alternating zigzag path |
| `sequence-zigzag-pucks-3d-underline-text` | Same geometry with emphasised labels |
| `sequence-steps-simple-illus` | Drops the 3D treatment; use when the steps are conceptual rather than physical |
| Five to six entries | The zigzag needs a readable rhythm; beyond six the pucks crowd the canvas |

## Pitfalls

- ❌ Using 3D pucks for abstract process steps → ✅ the object metaphor implies a physical thing moving; for logic-only flows use `sequence-steps-simple-illus`
- ❌ Long `desc` strings → ✅ each puck has a narrow column; keep the description to one clause
- ❌ A rollout plan where stations run in parallel → ✅ the zigzag asserts a single order
- ❌ Pucks used for quantities → ✅ they are labels, not counts; put numbers in the `desc`

## Alternatives

| Variant | Use instead |
|---|---|
| Conceptual ordered steps | `customer-onboarding-journey.md` |
| Steps against a calendar | `data-platform-migration-waves.md` |
| A checklist with progress facts | `launch-readiness-checklist.md` |

<!-- source: AntV Infographic template registry 0.2.20 (`sequence-zigzag-pucks-3d-simple`, structure `sequence-zigzag-pucks-3d`) -->
