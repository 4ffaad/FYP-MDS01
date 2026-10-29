# Launch Effort Curve — Where The Work Peaks (Infographic)

**Best for**: setting expectations about when a launch will consume the most team time
**Avoid when**: you have real effort data per sprint (use a bar chart)
**Answers**: the shape of effort across the phases, and which phase is the crunch

```infographic
infographic sequence-mountain-underline-text
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
  title Effort Across The Launch
  desc The build phase carries the peak
  sequences
    - label Scoping
      desc Light — two people, one week
    - label Build
      desc Peak — full team, six weeks
    - label Hardening
      desc Medium — QA and docs, three weeks
    - label Launch and hypercare
      desc Light — on-call plus support
```

## Data Shape

`sequences` where position encodes height. Put the peak in the middle for the mountain silhouette to read
correctly; the effort words ("Light", "Peak") live in `desc`.

## Key Options

| Option | Effect |
|---|---|
| `infographic sequence-mountain-underline-text` | Rises then falls; shape carries the message |
| `sequence-horizontal-zigzag-*` | Use when phases are equal effort and only order matters |
| `chart-bar-plain-text` | Use when the quantities are measured, not estimated |

## Pitfalls

- ❌ Peak at the last item → ✅ mountains rise and fall; the last phase is hypercare, not the summit
- ❌ Precise numbers implied → ✅ qualitative bands are honest for planning conversations
- ❌ Using it to argue for more headcount → ✅ this is a shape, not a capacity model

## Alternatives

| Variant | Use instead |
|---|---|
| Headcount ramp over waves | `team-capacity-ramp.md` |
| Ordered launch steps | `launch-readiness-checklist.md` |
| Delivery timeline with dates | `platform-milestone-timeline.md` |

<!-- source: AntV Infographic syntax docs + template list (`sequence-mountain-underline-text`) -->
