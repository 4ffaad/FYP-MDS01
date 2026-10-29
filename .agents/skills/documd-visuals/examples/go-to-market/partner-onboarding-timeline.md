# Partner Onboarding Timeline — From Signature To First Deal (Infographic)

**Best for**: a partner-facing timeline showing the path from signing to first registered deal
**Avoid when**: the reader needs the contract terms (link the agreement)
**Answers**: what the partner must do and when, with a realistic time to first deal

```infographic
infographic sequence-timeline-rounded-rect-node
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
  title Partner Onboarding — 60 Days
  desc Four milestones from signature to first deal
  sequences
    - label Day 0 — Signed
      desc Agreement countersigned, portal invite sent
    - label Day 10 — Enabled
      desc Training complete, sandbox credentials issued
    - label Day 30 — Certified
      desc Two people certified on the integration
    - label Day 60 — First deal
      desc Deal registered with co-selling support
```

## Data Shape

`sequences` with the day offset at the start of each label. Rounded nodes suit longer phrases, so the
milestone name can carry both the day and the state.

## Key Options

| Option | Effect |
|---|---|
| `infographic sequence-timeline-rounded-rect-node` | Rounded nodes along a horizontal spine |
| `sequence-timeline-simple` | Plain variant for internal enablement docs |
| `sequence-roadmap-vertical-*` | Use when the path spans quarters rather than days |

## Pitfalls

- ❌ Certification optional → ✅ the certification milestone is what predicts partner activity
- ❌ Time to first deal unstated → ✅ partners plan around that number
- ❌ Seven milestones → ✅ four milestones in 60 days is the credible shape

## Alternatives

| Variant | Use instead |
|---|---|
| Partner tiers after onboarding | `partner-tiers-pyramid.md` |
| Customer implementation stages | `customer-onboarding-journey.md` |
| Study path for certification | `certification-study-roadmap.md` |

<!-- source: AntV Infographic syntax docs + template list (`sequence-timeline-rounded-rect-node`) -->
