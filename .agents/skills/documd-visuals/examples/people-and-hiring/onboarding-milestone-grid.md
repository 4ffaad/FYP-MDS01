# Onboarding Milestone Grid — Customers Moving Through Stages (Infographic)

**Best for**: a delivery team tracking many accounts in one view by milestone
**Avoid when**: the reader follows a single account (use a timeline)
**Answers**: how many accounts sit at each milestone, and what that milestone requires

```infographic
infographic list-grid-progress-card
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
  title Implementation Milestones
  desc 24 accounts across four stages
  lists
    - label Kick-off complete
      desc 9 accounts
    - label Data connected
      desc 7 accounts
    - label Pilot live
      desc 5 accounts
    - label Handover to CSM
      desc 3 accounts
```

## Data Shape

`lists` of stages with a count in `desc`. The progress-card layout gives each item a bar, so use the `desc`
to carry the number the bar would otherwise imply.

## Key Options

| Option | Effect |
|---|---|
| `infographic list-grid-progress-card` | Cards with progress bars |
| `list-grid-circular-progress` | Ring instead of bar — easier to scan in a grid |
| `list-grid-compact-card` | Drop the progress primitive when numbers are not tracked |

## Pitfalls

- ❌ Percentages that do not correspond to reality → ✅ state the actual count; the card shows movement
- ❌ Stage names invented per project → ✅ fixed stage vocabulary keeps cohorts comparable
- ❌ Ten stages → ✅ four or five stages per implementation method

## Alternatives

| Variant | Use instead |
|---|---|
| Individual task progress | `onboarding-task-progress.md` |
| Stage-by-stage customer journey | `customer-onboarding-journey.md` |
| Programme status with owners | `program-status-ribbons.md` |

<!-- source: AntV Infographic syntax docs + template list (`list-grid-progress-card`) -->
