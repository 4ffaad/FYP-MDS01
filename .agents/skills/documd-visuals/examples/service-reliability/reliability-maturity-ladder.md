# Reliability Maturity Ladder — Four Stages From Reactive To Optimized (Infographic)

**Best for**: framing where a service sits on an operational maturity curve
**Avoid when**: the reader wants a score against a checklist (use a progress grid)
**Answers**: what each maturity stage looks like, and what the next one requires

```infographic
infographic list-pyramid-compact-card
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
  title Operational Maturity Model
  desc Bottom stage is where most services start
  lists
    - label Optimized
      desc Error budgets drive roadmap
    - label Measured
      desc SLOs tracked and reviewed
    - label Managed
      desc Runbooks and on-call exist
    - label Reactive
      desc Alerts fire, nobody owns them
```

## Data Shape

Four to six `lists` items ordered from the **top of the pyramid downward**. The pyramid narrows upward, so
put the aspirational stage first and the baseline stage last.

## Key Options

| Option | Effect |
|---|---|
| `infographic list-pyramid-compact-card` | Pyramid silhouette with compact stage cards |
| `list-pyramid-badge-card` | Badge-style stages; sturdier for long labels |
| `list-pyramid-rounded-rect-node` | Node look without cards — the most restrained option |

## Pitfalls

- ❌ Reversing the order → ✅ first item renders at the apex; write from most to least mature
- ❌ Seven stages → ✅ four or five stages spark recognition without becoming a taxonomy
- ❌ Claiming a stage without evidence → ✅ each `desc` states the observable practice

## Alternatives

| Variant | Use instead |
|---|---|
| Individual service progress | `onboarding-task-progress.md` |
| Capability tiers and owners | `capability-pyramid-framework.md` |
| Ordered growth journey | `engineer-skill-progression.md` |

<!-- source: AntV Infographic syntax docs + template list (`list-pyramid-compact-card`) -->
