# Engineer Skill Progression — From Guided Tasks To Strategy (Infographic)

**Best for**: a growth framework that shows what changes at each level
**Avoid when**: the reader needs compensation bands (those belong in a policy doc)
**Answers**: what each level is responsible for, and how responsibility grows

```infographic
infographic sequence-ascending-steps
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
  title Engineering Career Progression
  desc Responsibility grows with each step
  sequences
    - label Apprentice
      desc Completes scoped tasks with review
    - label Practitioner
      desc Owns a service end to end
    - label Specialist
      desc Sets standards across teams
    - label Principal
      desc Shapes technical strategy
```

## Data Shape

`sequences` in ascending order — the staircase only reads correctly if the first item is the lowest level.
Each `desc` states the *responsibility shift*, not the skill list.

## Key Options

| Option | Effect |
|---|---|
| `infographic sequence-ascending-steps` | Ascending steps with corner-card items |
| `sequence-ascending-stairs-3d-simple` | Staircase variant with more visual depth |
| `sequence-stairs-front-*` | Front-facing staircase — stronger for slides |

## Pitfalls

- ❌ Levels defined by years of experience → ✅ define them by responsibility
- ❌ Six levels → ✅ four or five keeps the staircase legible at 900×600
- ❌ Confusing with org hierarchy → ✅ this is a growth path, not a reporting line

## Alternatives

| Variant | Use instead |
|---|---|
| Team reporting structure | `team-reporting-tree.md` |
| Individual growth plan | `career-growth-ladder.md` |
| Maturity of a practice | `reliability-maturity-ladder.md` |

<!-- source: AntV Infographic syntax docs + template list (`sequence-ascending-steps`) -->
