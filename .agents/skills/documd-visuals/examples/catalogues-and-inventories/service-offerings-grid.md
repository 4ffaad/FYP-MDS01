# Service Offerings — Feature Grid (Infographic)

**Best for**: presenting a small set of peer services or offerings where the reader needs quick side-by-side scanning
**Avoid when**: you need ranked comparison, long descriptions, or process order
**Answers**: what the main offerings are, and how they differ at a glance

```infographic
infographic list-grid-candy-card-lite
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
  title Platform Service Offerings
  desc The main service families exposed to internal product teams
  lists
    - label Identity
      desc Access control, SSO, token issuance
    - label Billing
      desc Metering, invoicing, discounts
    - label Search
      desc Query, indexing, ranking
    - label Notifications
      desc Email, SMS, webhook delivery
```

## Data Shape

Use `lists` when the items are peer offerings with no meaningful order between them.

## Key Options

| Option | Effect |
|---|---|
| `list-grid-candy-card-lite` | Equal-weight feature/service card grid |
| `lists` | Unordered peer items |
| Short `desc` text | Lets each offering carry one sentence of scope |

## Pitfalls

- ❌ Using this for ordered process steps → ✅ this is a grid of peers, not a sequence
- ❌ Unequal description lengths everywhere → ✅ large text imbalance breaks the grid rhythm
- ❌ Treating it like a pricing table → ✅ if trade-offs matter, switch to compare templates or HTML comparison cards

## Alternatives

| Variant | Use instead |
|---|---|
| Ordered rollout roadmap | `product-roadmap-sequence.md` |
| Binary option framing | `buy-vs-build-comparison.md` |
| One-page executive summary | `executive-brief-summary.md` |

<!-- source: AntV Infographic template reference (`list-grid-candy-card-lite`) + syntax docs for lists -->