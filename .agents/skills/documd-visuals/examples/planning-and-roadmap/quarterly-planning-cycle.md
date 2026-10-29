# Quarterly Planning Cycle — The Loop With Underlined Beats (Infographic)

**Best for**: a quiet, text-forward version of the planning cadence for internal docs
**Avoid when**: the audience needs dates (pair it with a calendar)
**Answers**: the repeating beats of quarterly planning and what each one settles

```infographic
infographic sequence-circular-underline-text
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
  title Quarterly Planning Cycle
  desc Four beats that repeat every quarter
  sequences
    - label Review
      desc Last quarter’s actuals agreed
    - label Decide
      desc Bets and cut lines chosen
    - label Align
      desc Teams map work to bets
    - label Commit
      desc Owners and dates published
```

## Data Shape

Four `sequences` items on a ring. Underlined labels carry the verb; `desc` states the artefact each beat
produces. Keep it to four — a ring with five or more labels overlaps.

## Key Options

| Option | Effect |
|---|---|
| `infographic sequence-circular-underline-text` | Ring with underlined text, no decoration |
| `sequence-circular-simple` | Slightly stronger shapes, same loop |
| `sequence-color-snake-steps-*` | Use when the cadence should read as motion across a slide |

## Pitfalls

- ❌ Beats without artefacts → ✅ planning beats are defined by what they output
- ❌ Five or more beats → ✅ quarterly planning has four moves; more means it never closes
- ❌ Using a ring for a one-off plan → ✅ rings imply repetition; use a timeline for a single run

## Alternatives

| Variant | Use instead |
|---|---|
| Company rhythm with icons | `quarterly-business-rhythm.md` |
| Weekly operating cycle | `operating-cycle-loop.md` |
| Dated milestone plan | `platform-milestone-timeline.md` |

<!-- source: AntV Infographic syntax docs + template list (`sequence-circular-underline-text`) -->
