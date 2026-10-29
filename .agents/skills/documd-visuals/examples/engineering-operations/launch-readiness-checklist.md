# Launch Checklist — Readiness Snapshot (Infographic)

**Best for**: showing a short go-live or release readiness checklist where completion state matters more than long explanations
**Avoid when**: each checklist item needs owner, due date, and detailed status history
**Answers**: what is already complete, and what still blocks the launch

```infographic
infographic list-column-done-list
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
  title Launch Readiness Checklist
  desc Final checks before production cutover
  lists
    - label Security review completed
      done true
    - label Rollback plan approved
      done true
    - label Synthetic monitoring enabled
      done true
    - label Support runbook published
      done false
    - label Final stakeholder sign-off
      done false
```

## Data Shape

Use an unordered `lists` array with a `done` boolean per item. Keep labels short and action-oriented.

## Key Options

| Option | Effect |
|---|---|
| `list-column-done-list` | Checklist layout with completion treatment |
| `done true/false` | Encodes readiness status directly in the template |
| Short action labels | Keeps the checklist scannable in one pass |

## Pitfalls

- ❌ Turning each checklist row into a paragraph → ✅ a readiness checklist should read as short actions
- ❌ More than a handful of items in one frame → ✅ split large launch checklists into phases or owners
- ❌ Using it as the system of record → ✅ this is a communication artifact, not the tracked task system

## Alternatives

| Variant | Use instead |
|---|---|
| Ordered milestone sequence | `platform-milestone-timeline.md` |
| Incident action summary | `incident-review-card.md` |
| KPI-style launch board | `metric-snapshot-board.md` |

<!-- source: AntV Infographic template reference (`list-column-done-list`) + syntax docs for lists/done -->