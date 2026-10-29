# Product Roadmap — Quarter-by-Quarter (Infographic)

**Best for**: ordered milestones where the reader needs a compact roadmap rather than a full project plan
**Avoid when**: exact dates, dependencies, or resourcing matter (use gantt / project tooling)
**Answers**: what ships in what order, and how the next few milestones fit together

```infographic
infographic sequence-roadmap-vertical-simple
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
  title Product Roadmap 2026
  desc The next four milestones in release order
  sequences
    - label Q1
      desc Self-service onboarding
      icon mdi/account-plus
    - label Q2
      desc Billing usage reports
      icon mdi/file-chart
    - label Q3
      desc Partner API expansion
      icon mdi/api
    - label Q4
      desc Policy automation
      icon mdi/shield-check
```

## Data Shape

Use an ordered `sequences` array. Each item should represent one milestone or stage in the roadmap.

## Key Options

| Option | Effect |
|---|---|
| `sequence-roadmap-vertical-simple` | Vertical roadmap layout |
| `sequences` | Ordered items; the right structure for roadmap stages |
| `icon` | Helps the reader scan the theme of each milestone |

## Pitfalls

- ❌ Treating a roadmap like a detailed schedule → ✅ this is for milestone sequencing, not critical-path management
- ❌ Too many quarters or workstreams in one frame → ✅ split the roadmap before it becomes a wall of text
- ❌ Mixing roadmap and KPI cards → ✅ keep milestones and metrics as different artifacts

## Alternatives

| Variant | Use instead |
|---|---|
| Timed execution plan | PlantUML gantt or HTML roadmap board |
| Funnel of staged attrition | `conversion-funnel-journey.md` |
| Side-by-side option comparison | `market-entry-swot.md` |

<!-- source: AntV Infographic syntax docs + template list (`sequence-roadmap-vertical-simple`) -->