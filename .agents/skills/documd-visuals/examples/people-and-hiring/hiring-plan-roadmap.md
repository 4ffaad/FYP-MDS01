# Hiring Plan Roadmap — Roles Per Quarter (Infographic)

**Best for**: a headcount plan where each quarter opens specific roles
**Avoid when**: the reader needs cost per role (use a spreadsheet)
**Answers**: which roles open when, and what each hire unblocks

```infographic
infographic sequence-roadmap-vertical-pill-badge
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
  title FY27 Hiring Roadmap
  desc Roles grouped by quarter
  sequences
    - label Q1
      desc 2 backend, 1 designer
    - label Q2
      desc 1 SRE, 1 data engineer
    - label Q3
      desc 2 backend, 1 PM
    - label Q4
      desc Backfill only
```

## Data Shape

`sequences` in time order with the period in the label and the roles in `desc`. The vertical roadmap keeps
quarters aligned on one axis, so details should be short.

## Key Options

| Option | Effect |
|---|---|
| `infographic sequence-roadmap-vertical-pill-badge` | Vertical roadmap with pill badges |
| `sequence-roadmap-vertical-badge-card` | Card variant when each quarter needs commentary |
| `sequence-roadmap-vertical-quarter-simple-card` | Quarter-marker variant for planning decks |

## Pitfalls

- ❌ Roles without purpose → ✅ tie each hire to what it unblocks, or it reads as empire building
- ❌ Backfill hidden inside growth → ✅ separate backfill from net new
- ❌ Six quarters → ✅ a year is the planning horizon; replan before extending

## Alternatives

| Variant | Use instead |
|------|------|
| Team capacity in waves | `team-capacity-ramp.md` |
| Product plan by quarter | `product-roadmap-sequence.md` |
| Individual growth path | `engineer-skill-progression.md` |

<!-- source: AntV Infographic syntax docs + template list (`sequence-roadmap-vertical-pill-badge`) -->
