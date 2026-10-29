# Illustrated Steps — Field Operations Playbook (Infographic)

**Best for**: a short playbook where each step deserves an illustration slot and a one-line instruction
**Avoid when**: the steps need dates, owners or measurements — an illustrated sequence carries prose, not data
**Answers**: what a field operator does, in order, from arrival to report

```infographic
infographic sequence-steps-simple-illus
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
  title Field Operations Playbook
  desc Four steps an on-site operator follows for every service visit
  sequences
    - label Arrive & verify
      desc Match the asset tag against the work order before touching anything
    - label Isolate
      desc Take the unit out of rotation and confirm the traffic shift
    - label Service
      desc Apply the fix, then run the smoke check from the same handset
    - label Report
      desc Attach photos and close the order from the field app
```

## Data Shape

`sequences` with one entry per step. Each entry is a `label` plus a `desc` — the template reserves an
illustration slot at the leading edge of every step.

## Key Options

| Option | Effect |
|---|---|
| `sequence-steps-simple-illus` | Illustration-first step list; the leading art carries most of the meaning |
| `sequence-steps-badge-card` | Same data, badge treatment instead of illustration |
| `sequence-zigzag-steps-underline-text` | Zigzag rhythm when the steps deserve more visual movement |
| Four entries | Illustrated steps consume vertical space fast; four is the comfortable maximum |

## Pitfalls

- ❌ Using it as a process diagram with branches → ✅ the template renders one straight path; branching belongs in a different structure
- ❌ Steps that are really roles → ✅ a role list is not a sequence; use `list-grid` or `list-row`
- ❌ Putting the instruction in the label → ✅ the label is the step name; the instruction goes in `desc`
- ❌ More than five illustrated steps → ✅ the illustration slots shrink to icons and the template loses its point

## Alternatives

| Variant | Use instead |
|---|---|
| Steps as physical stations | `device-rollout-phases.md` |
| Steps with owners and dates | `data-platform-migration-waves.md` |
| A checklist with pass/fail state | `daily-ops-checklist-columns.md` |

<!-- source: AntV Infographic template registry 0.2.20 (`sequence-steps-simple-illus`, structure `sequence-steps`) -->
