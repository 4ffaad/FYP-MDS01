# Release Plan Trade-Off — Ship Now Or Harden First (Infographic)

**Best for**: framing a binary decision where each side has consequences
**Avoid when**: there are three or more genuinely different options (compare those instead)
**Answers**: what each choice buys, and what it costs

```infographic
infographic compare-binary-horizontal-compact-card-fold
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
  title Ship 4.2 Now, Or Harden First
  desc Fold layout puts the trade-off side by side
  compares
    - label Ship now
      desc Value in customers' hands this week
      children
        - label Pro
          desc Unblocks two enterprise pilots
        - label Pro
          desc Feedback loop starts sooner
        - label Con
          desc Known flaky migration path
    - label Harden first
      desc Two extra weeks of stabilisation
      children
        - label Pro
          desc Migration runs cleanly at scale
        - label Pro
          desc Support load stays flat
        - label Con
          desc Pilots stall on the calendar
```

## Data Shape

Exactly **two** `compares` entries; each side's `children` are the arguments. Keep to three arguments per
side — the fold layout divides the width, so longer lists crowd.

## Key Options

| Option | Effect |
|---|---|
| `infographic compare-binary-horizontal-compact-card-fold` | Compact cards in a folded two-column layout |
| `compare-binary-horizontal-simple-vs` | "vs" marker with plain text |
| `compare-binary-horizontal-underline-text-arrow` | Arrow treatment — reads as a decision point |

## Pitfalls

- ❌ Only listing pros → ✅ a trade-off without cons is advocacy
- ❌ Unequal argument counts → ✅ balance the columns or the diagram looks rigged
- ❌ Three or more options → ✅ binary layouts break past two; use `vendor-selection-scorecard.md`

## Alternatives

| Variant | Use instead |
|---|---|
| Build or buy decision | `buy-vs-build-comparison.md` |
| Choose between architectures | `cloud-migration-approaches.md` |
| Four-quadrant prioritisation | `backlog-priority-quadrant.md` |

<!-- source: AntV Infographic syntax docs + template list (`compare-binary-horizontal-compact-card-fold`) -->
