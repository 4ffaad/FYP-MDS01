# Milestone Timeline — Ordered Events (Infographic)

**Best for**: a compact history or milestone sequence where the reader needs order and a short note per event
**Avoid when**: the reader needs dependencies, critical path logic, or detailed schedule tracking
**Answers**: what happened in what order, and which milestones define the story arc

```infographic
infographic sequence-timeline-simple
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
  title Platform Milestones
  desc The four events that changed the platform operating model
  sequences
    - label 2023 Q3
      desc First multi-region deployment
    - label 2024 Q1
      desc Zero-downtime schema migration shipped
    - label 2024 Q4
      desc Self-service onboarding launched
    - label 2025 Q2
      desc Queue-first checkout path cut over
```

## Data Shape

Use an ordered `sequences` array, with one concise label and one short description per milestone.

## Key Options

| Option | Effect |
|---|---|
| `sequence-timeline-simple` | Straightforward milestone timeline layout |
| `sequences` | Ordered events rather than unordered peer items |
| Short `label` + `desc` | Keeps the timeline readable without turning into a paragraph stack |

## Pitfalls

- ❌ Long narrative text per milestone → ✅ each point should stay short enough to scan in sequence
- ❌ Using a timeline for parallel workstreams → ✅ timelines are strongest when one ordered thread is the message
- ❌ Treating it like a project schedule → ✅ use gantt or roadmap formats when dates and dependencies matter

## Alternatives

| Variant | Use instead |
|---|---|
| Future delivery sequence | `product-roadmap-sequence.md` |
| Step-by-step process | A snake/steps sequence template |
| Executive narrative with metrics | `executive-brief-summary.md` |

<!-- source: AntV Infographic template reference (`sequence-timeline-simple`) + syntax docs for sequences -->