# Quarter Roadmap — Data Platform Migration Waves (Infographic)

**Best for**: a migration or build-out expressed as quarterly waves down a single track
**Avoid when**: the work is continuous rather than quarterly, or the waves overlap heavily
**Answers**: which workload moves in which quarter, and what each wave unlocks

```infographic
infographic sequence-roadmap-vertical-quarter-circular
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
  title Data Platform Migration Waves
  desc Four waves from first replica to full cutover
  sequences
    - label Q1
      desc Read replicas for reporting; no writer changes
    - label Q2
      desc Analytics and batch jobs moved off the primary cluster
    - label Q3
      desc Service-owned schemas with contract tests in CI
    - label Q4
      desc Primary writer cutover and legacy cluster decommission
```

## Data Shape

`sequences` with exactly **four** entries — the template draws one quarter marker per entry, so the data has
to match the calendar you are describing.

## Key Options

| Option | Effect |
|---|---|
| `sequence-roadmap-vertical-quarter-circular` | Quarter discs down a vertical spine; the roundest reading of a quarterly plan |
| `sequence-roadmap-vertical-plain-text` | Text-only variant when the quarters are implied by the labels |
| `sequence-roadmap-vertical-badge-card` | Card variant for heavier descriptions |
| Four entries | The template is built around quarters; five or six entries break the metaphor |

## Pitfalls

- ❌ Using it for a weekly or monthly plan → ✅ the quarter discs promise a quarter grid; use `sequence-timeline-simple` instead
- ❌ Empty quarters → ✅ an entry with no real content still draws a disc; either fill it or restructure the plan
- ❌ Two waves in the same quarter → ✅ split the quarter's entry into sub-bullets in `desc` rather than adding a fifth entry
- ❌ Reading the discs as progress → ✅ they mark periods, not completion; say in the copy what has landed

## Alternatives

| Variant | Use instead |
|---|---|
| Milestones on a timeline | `platform-milestone-timeline.md` |
| Sequential steps without dates | `customer-onboarding-journey.md` |
| Quarterly plan with parallel tracks | `hiring-plan-roadmap.md` |

<!-- source: AntV Infographic template registry 0.2.20 (`sequence-roadmap-vertical-quarter-circular`, structure `sequence-roadmap-vertical`) -->
