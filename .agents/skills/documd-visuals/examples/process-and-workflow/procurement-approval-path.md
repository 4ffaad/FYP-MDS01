# Procurement Approval Path — Sign-Off Order (Infographic)

**Best for**: telling a buyer the exact order of approvals a purchase must collect
**Avoid when**: thresholds change the route (use a flowchart with conditions)
**Answers**: who signs, in what order, and what each approver is checking

```infographic
infographic sequence-horizontal-zigzag-simple
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
  title Purchase Approval Route
  desc Under $25K, three approvers
  sequences
    - label Requester
      desc Business justification and budget line
    - label Budget owner
      desc Confirms remaining budget
    - label Finance
      desc Checks vendor terms and tax setup
    - label Security review
      desc Data processing and access scope
```

## Data Shape

`sequences` in approval order, one approver per item, with the check they perform in `desc`. If routes differ
by amount, show the common path and state the exception in the surrounding text.

## Key Options

| Option | Effect |
|---|---|
| `infographic sequence-horizontal-zigzag-simple` | Plain zigzag; unmistakably a route |
| `sequence-steps-*` | Use when the order is a procedure rather than a delegation chain |
| `relation-dagre-flow` design block | Use when branches matter (thresholds, category exceptions) |

## Pitfalls

- ❌ Approvers without their check → ✅ "Finance" alone tells the requester nothing
- ❌ Hiding the slow approver → ✅ the security review is usually the critical path
- ❌ Parallel where sequential → ✅ approvals are sequential by definition; parallel steps need a graph

## Alternatives

| Variant | Use instead |
|---|---|
| Vendor comparison before approval | `vendor-selection-scorecard.md` |
| Compliance evidence gathering | `compliance-evidence-zigzag.md` |
| Purchase as part of a delivery flow | `claims-pipeline-funnel.md` |

<!-- source: AntV Infographic syntax docs + template list (`sequence-horizontal-zigzag-simple`) -->
