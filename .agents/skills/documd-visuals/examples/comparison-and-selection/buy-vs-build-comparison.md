# Buy vs Build — Binary Comparison (Infographic)

**Best for**: an A/B choice where the reader needs a quick directional comparison rather than a weighted scoring model
**Avoid when**: there are more than two options or the decision needs precise quantified criteria
**Answers**: how the options differ at a glance, and what each one optimizes for

```infographic
infographic compare-binary-horizontal-underline-text-vs
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
  title Buy vs Build
  desc Decision frame for a new workflow automation capability
  compares
    - label Buy
      children
        - label Speed
          desc Faster launch with lower implementation effort
        - label Maintenance
          desc Vendor handles upgrades and baseline support
        - label Fit
          desc Limited customization around edge-case workflows
    - label Build
      children
        - label Control
          desc Full ownership of workflow logic and domain fit
        - label Maintenance
          desc Internal team owns upgrades and operational burden
        - label Risk
          desc Longer path to value and greater delivery uncertainty
```

## Data Shape

Use `compares` with exactly two top-level items. Each side gets a short set of `children` that explain the trade-offs.

## Key Options

| Option | Effect |
|---|---|
| `compare-binary-horizontal-underline-text-vs` | Direct left/right A-vs-B framing |
| Two `compares` items | Encodes a binary comparison without extra scoring machinery |
| `children` | Holds the specific criteria or arguments under each side |

## Pitfalls

- ❌ Trying to compare three or four options in a binary template → ✅ keep this pattern strictly A vs B
- ❌ Long argumentative paragraphs per side → ✅ use short, decision-oriented criteria instead
- ❌ Treating qualitative comparison as proof of the decision → ✅ this is framing, not a formal scorecard

## Alternatives

| Variant | Use instead |
|---|---|
| SWOT-style strategic framing | `market-entry-swot.md` |
| Quantified trade-off model | Vega-Lite or HTML comparison table |
| One-page decision memo | `decision-comparison-card.md` |

<!-- source: AntV Infographic template reference (`compare-binary-horizontal-underline-text-vs`) + syntax docs for compares/children -->