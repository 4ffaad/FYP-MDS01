# Metric Board — KPI Cards (Infographic)

**Best for**: compact scoreboards with a handful of headline metrics on one page
**Avoid when**: the reader needs trends, axes, or many supporting values (use echarts or HTML cards)
**Answers**: what the key numbers are, and whether they collectively look healthy

```infographic
infographic list-grid-badge-card
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
  title Quarterly Operating Snapshot
  desc The smallest set of numbers leadership checks every week
  lists
    - label Revenue
      desc $12.8M | YoY +14%
      icon mdi/currency-usd
    - label Gross Margin
      desc 41.6% | stable
      icon mdi/chart-donut
    - label Active Accounts
      desc 4,820 | +190 net
      icon mdi/account-group
    - label Satisfaction
      desc 93.8% | above target
      icon mdi/emoticon-happy-outline
```

## Data Shape

Use a short unordered `lists` array. Each item should be one metric card with a `label`, a concise `desc`, and optionally an `icon`.

## Key Options

| Option | Effect |
|---|---|
| `infographic list-grid-badge-card` | Grid card layout for peer metrics |
| `lists` | Unordered peer items; the right fit for KPI boards |
| `icon` | Gives each metric a quick visual anchor |

## Pitfalls

- ❌ Mixing primary KPIs with long prose → ✅ keep each card to one number and one short qualifier
- ❌ Ten small cards in one board → ✅ KPI boards should stay selective
- ❌ Using this for trends → ✅ switch to `echarts` or `vega-lite` when time is part of the story

## Alternatives

| Variant | Use instead |
|---|---|
| Ordered milestone flow | `product-roadmap-sequence.md` |
| One metric with distribution | `budget-allocation-donut.md` |
| Richer editorial summary | HTML/CSS infocard layouts |

<!-- source: AntV Infographic syntax docs + template list (`list-grid-badge-card`) -->