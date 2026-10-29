# Returns Processing Snake — RMA Path With Badges (Infographic)

**Best for**: a customer-service process where each step changes who is responsible
**Avoid when**: the process branches by return reason (use a decision flowchart)
**Answers**: the standard RMA path and what happens at each hand-off

```infographic
infographic sequence-snake-steps-pill-badge
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
  title Return Merchandise Process
  desc Five steps from request to refund
  sequences
    - label Request received
      desc Portal form or phone
    - label Eligibility check
      desc Within 30 days, unopened
    - label Label issued
      desc Prepaid, tracked
    - label Inspection
      desc Warehouse grading and photos
    - label Refund
      desc Original payment method
```

## Data Shape

`sequences` in process order, five items. Snake layouts wrap across two rows, so pill badges keep the labels
compact and the flow readable.

## Key Options

| Option | Effect |
|---|---|
| `infographic sequence-snake-steps-pill-badge` | Badge steps on a serpentine path |
| `sequence-snake-steps-simple` | Plain variant for internal wikis |
| `sequence-snake-steps-underline-text` | Underlined labels; quietest of the three |

## Pitfalls

- ❌ Branching hidden inside a step → ✅ eligibility is the branch point; name it honestly
- ❌ Missing the refund step → ✅ the process ends when the customer is made whole
- ❌ Six or more steps → ✅ snakes hold five labels before wrapping becomes confusing

## Alternatives

| Variant | Use instead |
|---|---|
| Claims pipeline with volumes | `claims-pipeline-funnel.md` |
| Procurement approvals | `procurement-approval-path.md` |
| Onboarding journey stages | `customer-onboarding-journey.md` |

<!-- source: AntV Infographic syntax docs + template list (`sequence-snake-steps-pill-badge`) -->
