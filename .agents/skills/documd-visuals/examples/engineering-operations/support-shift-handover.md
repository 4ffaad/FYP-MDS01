# Support Shift Handover — Notes For The Next Shift (Infographic)

**Best for**: a handover note where each item carries state from one shift to the next
**Avoid when**: the reader wants ticket-level detail (link the queue)
**Answers**: what is in flight, who owns it now, and what must not be forgotten

```infographic
infographic
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
design
  structure sequence-interaction
  item simple
data
  title Shift Handover — 22:00
  desc Three items carried into night shift
  sequences
    - label Queue depth
      desc 34 open, 4 breaching in 2 hours
    - label Active incident
      desc INC-2291 mitigations applied, monitoring
    - label Pending change
      desc Cache flush scheduled 02:00 UTC, customer update due 09:00
```

## Data Shape

`sequences` with one line per handover item. The interaction structure connects items visually, which suits
"everything currently in flight" better than a strict timeline.

## Key Options

| Option | Effect |
|---|---|
| `design structure sequence-interaction` | Generic sequence layout with connector treatment |
| `design item simple` | Plain items; swap for `badge-card` when owners are shown |
| `sequence-timeline-*` templates | Use when items have clock times and a fixed order |

## Pitfalls

- ❌ `infographic sequence-interaction` as an entry line → ✅ no such template; declare it in a `design` block
- ❌ Four items on one line → ✅ this structure spends about **390 px per item** (measured: 3 items → 1190 px,
  4 items → 1559 px wide); hand over three things, not ten
- ❌ Handing over opinions → ✅ hand over state: counts, IDs, deadlines

## Alternatives

| Variant | Use instead |
|---|---|
| Escalation ladder for active incidents | `incident-escalation-path.md` |
| Response steps for the incoming shift | `incident-response-runbook.md` |
| Timed cutover plan | `migration-cutover-window.md` |

<!-- source: AntV Infographic syntax docs + structure registry (`sequence-interaction`) -->
