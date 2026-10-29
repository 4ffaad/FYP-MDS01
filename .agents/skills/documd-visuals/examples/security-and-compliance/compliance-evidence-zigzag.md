# Compliance Evidence Zigzag — Audit Pack Assembly (Infographic)

**Best for**: tracking which artefacts an audit needs and who is producing each one
**Avoid when**: evidence has expiry dates that must be tracked (use a table with dates)
**Answers**: the evidence list, its owners, and what is still missing

```infographic
infographic list-zigzag-down-compact-card
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
  title SOC 2 Evidence Pack
  desc Owner and status per artefact
  lists
    - label Access review exports
      desc Owner: IT — collected
    - label Change tickets
      desc Owner: Platform — collected
    - label Incident reports
      desc Owner: SRE — 2 of 3 collected
    - label Vendor risk assessments
      desc Owner: Legal — outstanding
```

## Data Shape

`lists` ordered as the auditor will read them. Status words stay in `desc` — this structure has no progress
primitive, so be explicit in text.

## Key Options

| Option | Effect |
|---|---|
| `infographic list-zigzag-down-compact-card` | Descending zigzag with compact cards |
| `list-zigzag-up-simple` | Ascending variant for process steps rather than artefacts |
| `list-grid-progress-card` | Use when each artefact has a numeric completion state |

## Pitfalls

- ❌ "In progress" without an owner → ✅ owner plus status; audits fail on unowned evidence
- ❌ Hiding the outstanding item → ✅ the gap is the reason this diagram exists
- ❌ Long file paths as labels → ✅ name the artefact, link it from the surrounding document

## Alternatives

| Variant | Use instead |
|---|---|
| Readiness checklist before launch | `launch-readiness-checklist.md` |
| Audit trail as an ordered sequence | `audit-trail-checkpoints.md` |
| Control-by-control scoring | `vendor-selection-scorecard.md` |

<!-- source: AntV Infographic syntax docs + template list (`list-zigzag-down-compact-card`) -->
