# Subscription Tiers Wheel — Commercial Ladder Around A Circle (Infographic)

**Best for**: presenting a product's tier ladder as one closed set rather than a ranked list
**Avoid when**: tiers must be compared on features (use a comparison table)
**Answers**: what each tier is called, who it is for, and how the ladder progresses

```infographic
infographic list-sector-simple
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
  title Plans At A Glance
  desc Four tiers, ordered by team size
  lists
    - label Starter
      desc Solo builders
    - label Team
      desc Up to 20 seats
    - label Business
      desc SSO, audit logs
    - label Enterprise
      desc Custom terms, SLA
```

## Data Shape

Four to six `lists` items arranged as wheel sectors. Because sectors are equal-sized, keep labels short and
put the qualifier in `desc`.

## Key Options

| Option | Effect |
|---|---|
| `infographic list-sector-simple` | Full-wheel sectors with simple labels |
| `list-sector-plain-text` | Text-only sectors; quietest rendering |
| `list-sector-half-plain-text` | Half-wheel — fewer sectors, larger text |

## Pitfalls

- ❌ Uneven value implied by equal sectors → ✅ say in `desc` that sectors are equal width, or add a note
- ❌ Price inside the label → ✅ prices change; keep them in `desc` or the pricing page
- ❌ Six-plus tiers → ✅ beyond six the sector labels become unreadable

## Alternatives

| Variant | Use instead |
|---|---|
| Tier ladder as a hierarchy | `partner-tiers-pyramid.md` |
| Coverage areas of one team | `oncall-coverage-wheel.md` |
| Revenue split by plan | `product-mix-donut-badges.md` |

<!-- source: AntV Infographic syntax docs + template list (`list-sector-simple`) -->
