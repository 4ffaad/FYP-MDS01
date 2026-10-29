# Quarterly Business Rhythm — Plan Build Review Adjust (Infographic)

**Best for**: explaining the cadence a company runs on, quarter after quarter
**Avoid when**: the reader needs a one-off schedule (use a timeline)
**Answers**: the four beats of the quarter and what each one produces

```infographic
infographic sequence-color-snake-steps-horizontal-icon-line
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
  title Quarterly Operating Rhythm
  desc Each beat produces one artefact
  sequences
    - label Plan
      desc Targets and bets agreed
      icon mdi/calendar-check
    - label Build
      desc Feature work in flight
      icon mdi/hammer-wrench
    - label Review
      desc Results measured against targets
      icon mdi/chart-line
    - label Adjust
      desc Reallocation decisions made
      icon mdi/tune-variant
    - label Plan again
      desc Next quarter’s bets
      icon mdi/calendar-refresh
```

## Data Shape

`sequences` with five beats where the last one loops back to the first. Colour progression comes from item
order, so the rhythm must genuinely advance.

## Key Options

| Option | Effect |
|---|---|
| `infographic sequence-color-snake-steps-horizontal-icon-line` | Colour-swept serpentine with icons |
| `sequence-horizontal-zigzag-horizontal-icon-line` | Same rhythm without colour emphasis |
| `sequence-circular-simple` | Use when the loop should be explicit rather than implied |

## Pitfalls

- ❌ Five beats that do not loop → ✅ the last step should hand back to the first
- ❌ Icons reused decoratively → ✅ one icon per beat, consistently across all company decks
- ❌ Turning it into a Gantt chart → ✅ this is a cadence, not a schedule with dates

## Alternatives

| Variant | Use instead |
|---|---|
| Product milestone timeline | `platform-milestone-timeline.md` |
| Lifecycle with an exit | `service-lifecycle-wheel.md` |
| Weekly operating cadence | `operating-cycle-loop.md` |

<!-- source: AntV Infographic syntax docs + template list (`sequence-color-snake-steps-horizontal-icon-line`) -->
