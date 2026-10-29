# Career Stairs — Growth Levels (Infographic)

**Best for**: ordered maturity or growth levels where the upward metaphor itself helps the reader understand progression
**Avoid when**: the levels are not hierarchical or when exact schedule timing matters more than stage progression
**Answers**: what the growth ladder looks like, and what each step represents

```infographic
infographic sequence-stairs-front-pill-badge
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
  title Career Growth Ladder
  desc A simple progression from entry to leadership scope
  sequences
    - label Junior
      desc Foundational delivery skills
    - label Mid-Level
      desc Independent project execution
    - label Senior
      desc System design and mentoring
    - label Staff
      desc Cross-team technical influence
    - label Principal
      desc Platform-wide direction
```

## Data Shape

Use `sequences` when each level is ordered and represents progression rather than peer comparison.

## Key Options

| Option | Effect |
|---|---|
| `sequence-stairs-front-pill-badge` | Encodes progression as an upward step structure |
| Ordered levels | Turns each item into a rung on the same ladder |
| Short descriptions | Keeps the stage meaning legible without drowning the shape |

## Pitfalls

- ❌ Using stair metaphors for unrelated categories → ✅ this layout is for progression, not grouping
- ❌ Too many micro-levels → ✅ compressed ladders quickly lose their visual clarity
- ❌ Treating the card like a skills matrix → ✅ it is a stage model, not a capability spreadsheet |

## Alternatives

| Variant | Use instead |
|---|---|
| Circular life-cycle | `operating-cycle-loop.md` |
| Linear onboarding path | `customer-onboarding-journey.md` |
| Richer narrative roadmap | `delivery-roadmap-board.md` |

<!-- source: AntV Infographic template reference (`sequence-stairs-front-pill-badge`) + syntax docs for sequences -->