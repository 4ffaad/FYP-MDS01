# Sprint Standup Talking Points — Left-To-Right Agenda (Infographic)

**Best for**: a facilitation slide that keeps a daily standup to ten minutes
**Avoid when**: the content is a status report for stakeholders (use a metric board)
**Answers**: what the meeting covers, in what order, and who speaks when

```infographic
infographic list-row-simple-horizontal-arrow
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
  title Daily Standup Agenda
  desc Five talking points, ten minutes total
  lists
    - label Blockers
      desc Anyone stuck right now
    - label Yesterday
      desc Finished work, one line each
    - label Today
      desc Committed for the next day
    - label Hand-offs
      desc Work leaving the team
    - label Parking lot
      desc Topics taken offline
```

## Data Shape

A short `lists` array; each item is one agenda point with a `label` and a one-line `desc`. Order matters
visually here, so write them in speaking order even though `lists` is unordered by contract.

## Key Options

| Option | Effect |
|---|---|
| `infographic list-row-simple-horizontal-arrow` | Arrows between items; reads as a run-through |
| `list-row-horizontal-icon-line` | Same rhythm with icons — good when each point has a symbol |
| `list-row-simple-illus` | Illustrative variant for onboarding decks |

## Pitfalls

- ❌ Turning each point into a paragraph → ✅ agenda items are prompts, not minutes
- ❌ More than six points → ✅ a standup agenda longer than six lines will not be followed
- ❌ Using arrows for an unordered list → ✅ if there is no sequence, use `list-grid-*` instead

## Alternatives

| Variant | Use instead |
|---|---|
| Unordered feature list | `service-offerings-grid.md` |
| Blockers needing escalation | `release-blockers-escalation.md` |
| Multi-step operational flow | `incident-response-runbook.md` |

<!-- source: AntV Infographic syntax docs + template list (`list-row-simple-horizontal-arrow`) -->
