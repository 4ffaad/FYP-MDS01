# Customer Health Journey — Adoption Stages With Drift Risk (Infographic)

**Best for**: a customer-success review where each stage has a characteristic risk
**Avoid when**: the reader needs account-level detail (use the CRM)
**Answers**: the adoption stages a customer passes through and where accounts typically stall

```infographic
infographic sequence-color-snake-steps-simple-illus
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
  title Customer Health Journey
  desc Each stage names the risk of stalling
  sequences
    - label Onboarded
      desc Risk: unclear success criteria
    - label First value
      desc Risk: single-team usage
    - label Habitual use
      desc Risk: no executive sponsor
    - label Expansion
      desc Risk: procurement cycle
    - label Advocate
      desc Risk: champion changes role
```

## Data Shape

`sequences` of five stages with the stage risk in `desc`. Illustrative items reserve space, so keep labels to
two or three words.

## Key Options

| Option | Effect |
|---|---|
| `infographic sequence-color-snake-steps-simple-illus` | Coloured serpentine with illustration slots |
| `sequence-snake-steps-pill-badge` | Text-forward variant with pill badges |
| `sequence-funnel-simple` | Use when stage-to-stage volume loss is the story |

## Pitfalls

- ❌ Risks that are generic ("churn") → ✅ name the stall condition, that is the actionable part
- ❌ Six or more stages → ✅ five is the practical limit for a serpentine
- ❌ Missing the advocate stage → ✅ expansion and advocacy are different stages

## Alternatives

| Variant | Use instead |
|---|---|
| Post-signature implementation steps | `customer-onboarding-journey.md` |
| Contact reduction across tiers | `support-escalation-pyramid.md` |
| Retention share by cohort | `quarterly-share-normalized-stack.md` (vega-lite) |

<!-- source: AntV Infographic syntax docs + template list (`sequence-color-snake-steps-simple-illus`) -->
