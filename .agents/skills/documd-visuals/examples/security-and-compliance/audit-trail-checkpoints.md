# Audit Trail Checkpoints — Control Points In A Workflow (Infographic)

**Best for**: showing where a workflow records evidence for auditors
**Avoid when**: the reader needs retention rules per record type (use a table)
**Answers**: which steps are audited, in order, and what is captured at each

```infographic
infographic sequence-zigzag-steps-underline-text
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
  title Audited Workflow Checkpoints
  desc Four checkpoints, four evidence types
  sequences
    - label Request logged
      desc Ticket ID, requester, timestamp
    - label Approval recorded
      desc Approver identity and reason
    - label Change executed
      desc Diff, deploy ID, operator
    - label Review completed
      desc Reviewer sign-off and outcome
```

## Data Shape

`sequences` where each item is a checkpoint and `desc` lists the captured fields. Underlined text keeps the
emphasis on the labels, so keep field lists short.

## Key Options

| Option | Effect |
|---|---|
| `infographic sequence-zigzag-steps-underline-text` | Zigzag with underlined labels |
| `sequence-steps-badge-card` | Use when checkpoints carry owner names |
| `list-grid-done-list` | Use for a checklist without ordering requirements |

## Pitfalls

- ❌ Fields nobody captures → ✅ only list evidence the systems actually store
- ❌ Nine checkpoints → ✅ auditors care about control points, not every click
- ❌ Mixing audit and monitoring → ✅ this is what is recorded, not what is alerted

## Alternatives

| Variant | Use instead |
|---|---|
| Evidence pack assembly | `compliance-evidence-zigzag.md` |
| Change window execution | `migration-cutover-window.md` |
| Control scoring | `vendor-selection-scorecard.md` |

<!-- source: AntV Infographic syntax docs + template list (`sequence-zigzag-steps-underline-text`) -->
