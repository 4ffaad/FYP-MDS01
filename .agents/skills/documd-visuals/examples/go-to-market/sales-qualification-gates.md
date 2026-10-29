# Sales Qualification Gates — What Must Be True Before The Next Stage (Infographic)

**Best for**: a revenue team aligning on when a deal genuinely advances
**Avoid when**: the reader wants pipeline value or forecast (use a metric board)
**Answers**: the exit criteria for each stage, and what the buyer must have confirmed

```infographic
infographic sequence-steps-badge-card
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
  title Deal Qualification Gates
  desc A stage only advances when its gate passes
  sequences
    - label Discovery
      desc Business problem and owner confirmed
    - label Technical validation
      desc Security review scheduled
    - label Business case
      desc CFO-visible payback model
    - label Procurement
      desc Legal redlines returned
    - label Signature
      desc Order form countersigned
```

## Data Shape

`sequences` where each item is a **gate** rather than an activity: the label names the stage, `desc` states
the condition that must hold to leave it.

## Key Options

| Option | Effect |
|---|---|
| `infographic sequence-steps-badge-card` | Badge steps that read as checkpoints |
| `sequence-steps-simple` | Quieter variant for internal enablement decks |
| `sequence-filter-mesh-*` | Use when the story is drop-off / conversion, not gate criteria |

## Pitfalls

- ❌ Gates phrased as activities ("Do discovery") → ✅ phrase as evidence ("Problem owner confirmed")
- ❌ Gates nobody can verify → ✅ each condition must be observable in the CRM
- ❌ Skipping procurement → ✅ the slowest gate deserves its own step

## Alternatives

| Variant | Use instead |
|---|---|
| Funnel with drop-off volumes | `conversion-funnel-journey.md` |
| Two-option commercial decision | `buy-vs-build-comparison.md` |
| Customer onboarding after signature | `customer-onboarding-journey.md` |

<!-- source: AntV Infographic syntax docs + template list (`sequence-steps-badge-card`) -->
