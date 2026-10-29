# Folded Comparison — Monolith Versus Modular (Infographic)

**Best for**: a two-option decision where the trade-offs should converge toward a single judgement
**Avoid when**: there are three or more options, or the two sides are not true alternatives
**Answers**: which properties favour each option, and where they end up meeting in the middle

```infographic
infographic compare-binary-horizontal-underline-text-fold
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
  title Monolith vs Modular
  desc Two delivery shapes for the same product surface, compared on the properties that decide it
  compares
    - label Single deployable
      children
        - label Debugging
          desc One process tree, one log stream, trivially reproducible locally
        - label Onboarding
          desc New engineers ship in week one without a service map
        - label Blast radius
          desc A bad release risks the whole surface at once
    - label Modular services
      children
        - label Debugging
          desc Cross-service tracing is mandatory before it is useful
        - label Onboarding
          desc Requires understanding contracts, ownership and routing
        - label Blast radius
          desc Failures and load spikes stay inside one boundary
```

## Data Shape

`compares` with exactly **two** entries, each holding a `children` list. Use the same child labels on both
sides so the pair reads as one dimension at a time — the fold layout lines the rows up against each other.

## Key Options

| Option | Effect |
|---|---|
| `compare-binary-horizontal-underline-text-fold` | Rows fold toward a shared centre line, so mirrored items sit next to each other |
| `compare-binary-horizontal-underline-text-vs` | The "vs" variant: sharper opposition, better for a genuine either/or |
| `compare-binary-horizontal-simple-fold` | Plain-text fold when the labels carry the whole message |
| Matched child labels | The comparison only works if both sides answer the same questions |

## Pitfalls

- ❌ Different child labels on each side → ✅ the fold aligns rows by position, so mismatched labels compare the wrong things
- ❌ Unequal child counts → ✅ the shorter side folds against empty space and looks like a gap
- ❌ Choosing properties that both sides win → ✅ a comparison needs real trade-offs; two lists of strengths is marketing
- ❌ More than three children per side → ✅ the fold compresses; split into two comparisons

## Alternatives

| Variant | Use instead |
|---|---|
| A hard either/or decision | `buy-vs-build-comparison.md` |
| Four-way option grouping | `operating-model-option-map.md` |
| Two competing approaches with costs | `cloud-migration-approaches.md` |

<!-- source: AntV Infographic template registry 0.2.20 (`compare-binary-horizontal-underline-text-fold`, structure `compare-binary-horizontal`) -->
