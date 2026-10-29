# Test Automation Quadrant — What to Automate First (Infographic)

**Best for**: agreeing which regression tests deserve engineering time this quarter
**Avoid when**: the audience wants test-case counts or pass rates (use a metric board)
**Answers**: automate now, automate next, keep manual, or delete the test entirely

```infographic
infographic compare-quadrant-simple-illus
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
  title Test Coverage Triage
  desc Frequency of failure vs cost to automate
  compares
    - label Automate Now
      desc Runs every commit, stable oracle
      children
        - label Login and session expiry
    - label Automate Next
      desc Frequent, needs test data work
      children
        - label Checkout totals
    - label Keep Manual
      desc Rare and cheap to check
      children
        - label Marketing copy review
    - label Retire
      desc Rare, flaky, expensive upkeep
      children
        - label Legacy export snapshots
```

## Data Shape

Four `compares` entries describing the decision slots; `children` holds the concrete tests. Keep test names
recognisable to the team — this diagram is a shared backlog, not a taxonomy.

## Key Options

| Option | Effect |
|---|---|
| `infographic compare-quadrant-simple-illus` | Leaves room for an illustration in each quadrant |
| `compare-quadrant-quarter-simple-card` | Denser, more list-like alternative |
| `children` | Two to three tests per slot keeps the render inside the 900×600 canvas |

## Pitfalls

- ❌ Quadrant axes hidden in the title → ✅ name axes in `desc`, e.g. "Frequent + expensive upkeep"
- ❌ Treating "Retire" as an insult → ✅ deleting tests is a cost decision, phrase it neutrally
- ❌ Listing the whole suite → ✅ pick the contested cases; this is a decision aid

## Alternatives

| Variant | Use instead |
|---|---|
| Sequence of test phases | `incident-response-runbook.md` |
| Scorecard with numeric weights | `vendor-selection-scorecard.md` |
| Coverage metrics over time | `feature-adoption-trend.md` |

<!-- source: AntV Infographic syntax docs + template list (`compare-quadrant-simple-illus`) -->
