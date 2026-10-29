# Operating Cycle — Circular Loop (Infographic)

**Best for**: recurring cycles where the reader should understand the stages as a loop rather than a line with a hard end
**Avoid when**: the process is really sequential with a start and finish, or when branching logic matters
**Answers**: what the recurring stages are, and how they connect as a cycle

```infographic
infographic sequence-circular-simple
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
  title Operating Cycle
  desc The recurring rhythm of planning, delivery, and review
  sequences
    - label Plan
      desc Prioritize the next batch of work
    - label Build
      desc Implement and integrate
    - label Release
      desc Ship safely to production
    - label Observe
      desc Review usage, incidents, and cost
    - label Improve
      desc Feed findings back into the next plan
```

## Data Shape

Use `sequences` when the stages are ordered but conceptually loop back to the beginning.

## Key Options

| Option | Effect |
|---|---|
| `sequence-circular-simple` | Makes the cycle explicit rather than implying a terminal flow |
| Ordered `sequences` | Preserves the stage order inside the loop |
| Concise descriptions | Clarifies each stage without overloading the circular layout |

## Pitfalls

- ❌ Using a cycle for one-way funnels or roads → ✅ use circular layouts only when recurrence is central to the meaning
- ❌ Too many stages → ✅ cycle diagrams lose clarity as they become crowded |
- ❌ Ambiguous stage names → ✅ each segment should clearly imply an action or phase |

## Alternatives

| Variant | Use instead |
|---|---|
| Straight sequence | `platform-milestone-timeline.md` |
| Funnel attrition | `conversion-funnel-journey.md` |
| Architecture overview | `layer-stack.md` |

<!-- source: AntV Infographic template reference (`sequence-circular-simple`) + syntax docs for sequences -->