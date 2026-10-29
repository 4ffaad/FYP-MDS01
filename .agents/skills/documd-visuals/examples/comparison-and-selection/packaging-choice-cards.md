# Packaging Choice Cards — Per-Seat Or Consumption Pricing (Infographic)

**Best for**: a pricing committee deciding between two commercial models
**Avoid when**: the models will be blended (show the blend instead)
**Answers**: what each model does to revenue predictability and to customer behaviour

```infographic
infographic compare-binary-horizontal-badge-card-vs
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
  title Pricing Model Decision
  desc Choose the primary motion, not the only motion
  compares
    - label Per seat
      desc Predictable, familiar to buyers
      children
        - label Recurring revenue is forecastable
        - label Growth tied to customer hiring
        - label Penalises occasional users
    - label Consumption
      desc Aligned to value delivered
      children
        - label Revenue grows with usage
        - label Forecasting needs real telemetry
        - label Bill anxiety slows adoption
```

## Data Shape

Two `compares` entries with three statements each. The `vs` marker variant sets the two sides against each
other explicitly — use it for genuine either/or decisions.

## Key Options

| Option | Effect |
|---|---|
| `infographic compare-binary-horizontal-badge-card-vs` | Badge cards with a "vs" divider |
| `compare-binary-horizontal-simple-vs` | Text-only variant for internal memos |
| `compare-binary-horizontal-underline-text-fold` | Underlined labels, folded layout |

## Pitfalls

- ❌ Treating hybrid pricing as a third option → ✅ pick the dominant motion, then describe the add-on
- ❌ Only financial arguments → ✅ behavioural effects (bill anxiety) decide adoption
- ❌ Missing forecastability → ✅ that is the first question finance will ask

## Alternatives

| Variant | Use instead |
|---|---|
| Tier ladder already decided | `subscription-tiers-wheel.md` |
| Partner tier comparison | `partner-tiers-pyramid.md` |
| Revenue plan under the chosen model | `revenue-staircase-plan.md` |

<!-- source: AntV Infographic syntax docs + template list (`compare-binary-horizontal-badge-card-vs`) -->
