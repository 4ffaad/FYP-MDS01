# Board Committee Charter — Mandate And Cadence (Infographic)

**Best for**: a governance page stating what a committee decides and how often it meets
**Avoid when**: the reader needs membership and voting rules in detail (use prose)
**Answers**: why this committee exists, what it owns, and its operating rhythm

```infographic
infographic list-row-simple-illus
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
  title Risk Committee Charter
  desc Mandate, authority, cadence, escalation
  lists
    - label Mandate
      desc Own the enterprise risk register
    - label Authority
      desc Approve risk appetite changes
    - label Cadence
      desc Monthly, first Thursday
    - label Escalation
      desc Material issues go to the board
```

## Data Shape

Four to five `lists` items, each a governance attribute. `desc` is the operative sentence — keep it under
about 60 characters so the illustration column stays readable.

## Key Options

| Option | Effect |
|---|---|
| `infographic list-row-simple-illus` | Reserves an illustration slot beside the text |
| `list-row-simple-horizontal-arrow` | Text-only variant when no illustration is available |
| `list-grid-compact-card` | Use when there are six or more charter clauses |

## Pitfalls

- ❌ Charter clauses pasted verbatim → ✅ one sentence per attribute; the full text lives in the doc
- ❌ `illus` set to a missing resource → ✅ omit illustrations rather than referencing absent files
- ❌ Using it to show committee membership → ✅ that is an org chart, not a charter

## Alternatives

| Variant | Use instead |
|---|---|
| Policy summary with numbered clauses | `policy-memo-card.md` (HTML/CSS) |
| Committee membership structure | `platform-org-structure.md` |
| Ordered governance cycle | `operating-cycle-loop.md` |

<!-- source: AntV Infographic syntax docs + template list (`list-row-simple-illus`) -->
