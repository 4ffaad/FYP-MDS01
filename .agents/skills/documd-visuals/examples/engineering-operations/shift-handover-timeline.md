# Shift Handover Timeline — Done List Of A Working Day (Infographic)

**Best for**: an end-of-shift note that shows what was completed and what carries over
**Avoid when**: the reader needs incident detail (link the incident channel)
**Answers**: the day's completed work in order, with the carry-over at the end

```infographic
infographic sequence-timeline-done-list
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
  title On-Call Day Log — Tuesday
  desc Completed items, then the carry-over
  sequences
    - label 09:10 Database failover drill
      desc Completed, no customer impact
    - label 11:40 Certificate renewal
      desc Completed for two of three services
    - label 14:05 Latency alert triage
      desc Completed, rooted to cache eviction
    - label 17:30 Carry-over
      desc Third certificate needs vendor input
```

## Data Shape

`sequences` where each label leads with the clock time. The done-list styling implies completion, so the last
item should be explicitly marked as carry-over.

## Key Options

| Option | Effect |
|---|---|
| `infographic sequence-timeline-done-list` | Timeline with check-list styling |
| `sequence-timeline-plain-text` | Neutral variant when nothing is "done" yet |
| `sequence-timeline-rounded-rect-node` | Softer nodes for customer-facing write-ups |

## Pitfalls

- ❌ Backdating entries → ✅ the log is evidence; accuracy beats tidiness
- ❌ Hiding the carry-over → ✅ the next shift needs it more than the day's wins
- ❌ Ten entries → ✅ four to six is what a human actually reads

## Alternatives

| Variant | Use instead |
|---|---|
| Handover state for the next shift | `support-shift-handover.md` |
| Timed change window | `migration-cutover-window.md` |
| Weekly milestone timeline | `platform-milestone-timeline.md` |

<!-- source: AntV Infographic syntax docs + template list (`sequence-timeline-done-list`) -->
