# Change Request Columns — What A Change Must Carry (Infographic)

**Best for**: a change-management reminder about what every request must state
**Avoid when**: the reader wants the approval route (use the procurement or escalation diagram)
**Answers**: the fields a change request needs before it can be reviewed

```infographic
infographic list-column-simple-vertical-arrow
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
  title Change Request Requirements
  desc Minimum content before review
  lists
    - label Scope
      desc Services and environments touched
    - label Risk
      desc Blast radius and reversibility
    - label Verification
      desc How success will be confirmed
    - label Rollback
      desc Trigger, owner, time to restore
    - label Window
      desc Start, end, and freeze exceptions
```

## Data Shape

`lists` in the order reviewers read them. Without icons the arrows do the work, so keep each `desc` to one
clause — this is a form, not an essay.

## Key Options

| Option | Effect |
|---|---|
| `infographic list-column-simple-vertical-arrow` | Plain vertical column with arrows |
| `list-column-vertical-icon-arrow` | Adds icons — helpful on posters in an operations room |
| `list-column-done-list` | Checkbox styling; use for a pre-submission checklist |

## Pitfalls

- ❌ Rollback as "revert if needed" → ✅ require a trigger, an owner and a time estimate
- ❌ Window left blank → ✅ change freezes are the most common review failure
- ❌ Seven fields → ✅ five is what reviewers actually validate

## Alternatives

| Variant | Use instead |
|---|---|
| Approval order for a purchase | `procurement-approval-path.md` |
| Cutover execution plan | `migration-cutover-window.md` |
| Evidence for auditors | `compliance-evidence-zigzag.md` |

<!-- source: AntV Infographic syntax docs + template list (`list-column-simple-vertical-arrow`) -->
