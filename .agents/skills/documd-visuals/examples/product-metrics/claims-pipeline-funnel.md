# Claims Pipeline Funnel — Where Volume Narrows (Infographic)

**Best for**: an operations review showing how many cases survive each processing stage
**Avoid when**: the stages are not strictly narrowing (then it is a sequence, not a funnel)
**Answers**: the volume at each stage and the size of the largest drop

```infographic
infographic sequence-funnel-simple
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
  title Claims Processing — Last 30 Days
  desc 1,200 received, 480 paid
  sequences
    - label Received
      desc 1,200 claims
    - label Documents verified
      desc 940 claims
    - label Assessed
      desc 610 claims
    - label Paid
      desc 480 claims
```

## Data Shape

`sequences` in descending volume order — this is what makes the funnel shape truthful. The number belongs in
`desc`, since the structure scales blocks by order rather than by value.

## Key Options

| Option | Effect |
|---|---|
| `infographic sequence-funnel-simple` | Nested trapezoids, largest at the top |
| `sequence-filter-mesh-simple` | Use when you want to show *filters* removing cases |
| `chart-bar-plain-text` | Use when exact comparison matters more than flow |

## Pitfalls

- ❌ Non-monotonic volumes → ✅ if a stage grows, it is a rework loop; show it as a sequence
- ❌ Percentages without volumes → ✅ give counts, derive percentages in the text
- ❌ Nine stages → ✅ group into four or five meaningful phases

## Alternatives

| Variant | Use instead |
|---|---|
| Marketing conversion journey | `conversion-funnel-journey.md` |
| Stage gates in a sales process | `sales-qualification-gates.md` |
| Queue behaviour over a day | `traffic-source-mix-split.md` |

<!-- source: AntV Infographic syntax docs + template list (`sequence-funnel-simple`) -->
