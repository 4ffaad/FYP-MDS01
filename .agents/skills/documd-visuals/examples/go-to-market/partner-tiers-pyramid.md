# Partner Tiers Pyramid — What Each Tier Gets (Infographic)

**Best for**: a partner-facing page showing how tiers differ in commitment and reward
**Avoid when**: the tiers differ by more than three attributes (use a comparison table)
**Answers**: what each partner tier is expected to do, and what it receives in return

```infographic
infographic list-pyramid-rounded-rect-node
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
  title Partner Program Tiers
  desc Commitment climbs from top to bottom
  lists
    - label Strategic
      desc Joint roadmap, named manager
    - label Premier
      desc Shared pipeline, co-marketing budget
    - label Registered
      desc Portal access, deal registration
    - label Referral
      desc Link tracking and payouts
```

## Data Shape

`lists` written apex-first. Each `desc` states the *one* thing that tier unlocks; the full matrix belongs in
the partner agreement, not on the diagram.

## Key Options

| Option | Effect |
|---|---|
| `infographic list-pyramid-rounded-rect-node` | Minimal node styling; safest for print and dark mode |
| `list-pyramid-badge-card` | Heavier badges, good on slides |
| `list-section` layouts (`list-grid-*`) | Use for parallel partner types rather than tiers |

## Pitfalls

- ❌ Mixing obligations and benefits in one line → ✅ state the benefit; obligations go in the tier table
- ❌ Reading order confusion → ✅ say in `desc` which direction commitment climbs
- ❌ Six tiers → ✅ programs with six tiers are really two programs; consolidate before drawing

## Alternatives

| Variant | Use instead |
|---|---|
| Subscription pricing tiers | `subscription-tiers-wheel.md` |
| Two-option commercial choice | `buy-vs-build-comparison.md` |
| Partner onboarding journey | `partner-onboarding-timeline.md` |

<!-- source: AntV Infographic syntax docs + template list (`list-pyramid-rounded-rect-node`) -->
