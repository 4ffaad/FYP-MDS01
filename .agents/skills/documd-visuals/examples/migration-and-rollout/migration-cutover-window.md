# Migration Cutover Window — Clock Order (Infographic)

**Best for**: a change-window plan where each step must happen in a fixed order and timebox
**Avoid when**: the steps run in parallel (use a relation graph)
**Answers**: what happens inside the window, in order, with the icon marking each action type

```infographic
infographic sequence-horizontal-zigzag-horizontal-icon-line
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
  title Database Cutover — 90 Minute Window
  desc Each step is reversible until the traffic switch
  sequences
    - label Freeze writes
      desc 00:00 — change window opens
      icon mdi/snowflake
    - label Replicate
      desc 00:15 — logical replication caught up
      icon mdi/database-arrow-right
    - label Verify
      desc 00:35 — row counts and checksums match
      icon mdi/check-decagram
    - label Switch traffic
      desc 00:50 — connection strings flipped
      icon mdi/swap-horizontal
    - label Watch
      desc 01:00 — burn-in on new primary
      icon mdi/eye-outline
```

## Data Shape

`sequences` with a time offset at the start of `desc` and one `icon` per action type. The zigzag keeps the
line readable when descriptions are non-trivial.

## Key Options

| Option | Effect |
|---|---|
| `infographic sequence-horizontal-zigzag-horizontal-icon-line` | Zigzag with icon line; good for 5–6 timed steps |
| `sequence-color-snake-steps-horizontal-icon-line` | Same rhythm, colour-coded sweep — strong on slides |
| `sequence-timeline-*` | Use when steps are milestones, not a scripted window |

## Pitfalls

- ❌ Times inside the label → ✅ put the clock time first in `desc` so the column aligns
- ❌ No rollback step → ✅ say which step is the point of no return
- ❌ Icons with no meaning → ✅ reuse icons consistently across runbooks

## Alternatives

| Variant | Use instead |
|---|---|
| Incident response steps | `incident-response-runbook.md` |
| Procurement approval order | `procurement-approval-path.md` |
| Milestones across quarters | `platform-milestone-timeline.md` |

<!-- source: AntV Infographic syntax docs + template list (`sequence-horizontal-zigzag-horizontal-icon-line`) -->
