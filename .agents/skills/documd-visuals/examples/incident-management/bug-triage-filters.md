# Filter Mesh — Bug Triage Funnel (Infographic)

**Best for**: a funnel-shaped process where each stage rejects a specific class of item
**Avoid when**: nothing actually gets dropped, or the stages are gates with owners rather than filters
**Answers**: where the noise is removed from an incoming bug report stream

```infographic
infographic sequence-filter-mesh-underline-text
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
  title Bug Triage Filters
  desc Five passes that cut a raw report stream down to work worth scheduling
  sequences
    - label Deduplicate
      desc Collapse reports that match an open issue on the same stack trace
    - label Reproduce
      desc Keep only reports with steps, environment and a failing revision
    - label Classify
      desc Split defects from questions, feature asks and expected behaviour
    - label Assess severity
      desc Apply the impact rubric; downgrade cosmetic-only findings
    - label Schedule
      desc Assign to a squad with a milestone, or park with a stated reason
```

## Data Shape

`sequences` with one entry per filter stage. Each stage should name the **decision** it applies, not the
person who applies it — the mesh rendering reads as a series of narrowing gates.

## Key Options

| Option | Effect |
|---|---|
| `sequence-filter-mesh-underline-text` | Narrowing mesh with emphasised labels |
| `sequence-funnel-simple` | Classic funnel silhouette; use when volume loss is the story |
| `sequence-filter-mesh-underline-text` at five stages | The mesh needs enough passes to look like a mesh; three is the practical minimum |
| `desc` per stage | Names the rule being applied, which is what makes the narrowing legible |

## Pitfalls

- ❌ Stages that add work instead of removing items → ✅ a filter mesh narrows; enrichment belongs before or after it
- ❌ Unstated drop reasons → ✅ readers will assume the dropped items vanished; name the rule in each `desc`
- ❌ More than six stages → ✅ each pass costs vertical space and the mesh loses its "multi-stage sieve" reading
- ❌ Using it as a workflow with owners → ✅ filters are rules, not roles; use `procurement-approval-path.md` when people approve

## Alternatives

| Variant | Use instead |
|---|---|
| Volume loss as a chart | `conversion-funnel-journey.md` |
| Approval gates with owners | `procurement-approval-path.md` |
| Ordered steps with no rejection | `customer-onboarding-journey.md` |

<!-- source: AntV Infographic template registry 0.2.20 (`sequence-filter-mesh-underline-text`, structure `sequence-filter-mesh`) -->
