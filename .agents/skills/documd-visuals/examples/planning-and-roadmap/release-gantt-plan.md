# Release Plan (Gantt)

**Best for**: dated schedules with dependencies — phases, parallel tracks, milestones and owners
**Avoid when**: you only need a sequence of steps without dates (use an activity diagram) or a marketing-style roadmap (use an infographic timeline)
**Answers**: when each workstream runs, what blocks what, and when the milestones land

```plantuml
@startgantt
title Platform Release 3.0 — Delivery Schedule
Project starts 2026-10-05

-- Discovery --
[Requirements workshop] requires 5 days
[Architecture decision record] requires 3 days
[Architecture decision record] starts at [Requirements workshop]'s end

-- Implementation --
[API v2 implementation] requires 15 days
[API v2 implementation] starts at [Architecture decision record]'s end
[Data migration scripts] requires 8 days
[Data migration scripts] starts at [Architecture decision record]'s end
[Web client update] requires 12 days
[Web client update] starts at [API v2 implementation]'s end

-- Verification --
[Integration test suite] requires 6 days
[Integration test suite] starts at [Data migration scripts]'s end
[Load test] requires 4 days
[Load test] starts at [Integration test suite]'s end
[Security review] requires 5 days
[Security review] starts at [API v2 implementation]'s end

-- Release --
[Staging deployment] requires 2 days
[Staging deployment] starts at [Load test]'s end
[Release candidate] happens at [Staging deployment]'s end
[Production rollout] requires 3 days
[Production rollout] starts at [Release candidate]'s end
[General availability] happens at [Production rollout]'s end

[API v2 implementation] is colored in SteelBlue
[Data migration scripts] is colored in LightSteelBlue
[Web client update] is colored in LightSteelBlue
[Security review] is colored in FireBrick
@endgantt
```

## Key Options

| Syntax | Effect |
|---|---|
| `Project starts 2026-10-05` | Sets the calendar origin (otherwise only relative days exist) |
| `[Task] requires 15 days` | Duration (`N days`, `N weeks`, `N weeks and M days`) |
| `[Task] starts at [Other]'s end` | Dependency — the backbone of a useful Gantt |
| `[Task] starts D+3` | Relative start offset from project start |
| `[Milestone] happens at [Task]'s end` | Zero-duration milestone |
| `[Task] is colored in SteelBlue` | Colour a bar; colour by *track* (implementation / verification / release), not by taste |
| `-- Section --` | Visual separator between phases |

## Data Shape

Tasks with durations + dependency edges, grouped into phases by separators. Colour carries the track/owner so the
reader can answer "who is on the critical path".

## Pitfalls

- ❌ Durations without dependencies → ✅ the dependency edges are what makes a Gantt more than a table
- ❌ Hiding verification work → ✅ tests and security reviews are tasks; omitting them is a silent schedule lie
- ❌ Colour per task → ✅ colour per track; rainbow Gantts lose the critical path
- ❌ No milestones → ✅ a release without an explicit `happens at` date has no commitment

## Alternatives

| Variant | Use instead |
|---|---|
| Audience is external / no dates yet | Infographic timeline or roadmap template (`planning-and-roadmap`) |
| Process with owners, no dates | `approval-workflow-swimlane.md` |
| Milestone list only | A card / list template with badge items |

<!-- source: draw-uml gantt parser (L1, 111 fixtures); syntax verified against fixtures 001/009/010/011 -->
