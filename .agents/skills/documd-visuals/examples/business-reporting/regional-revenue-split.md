# Regional Revenue Split — Where The Money Is Booked (Infographic)

**Best for**: a quarterly review slide showing regional concentration
**Avoid when**: the reader needs regional growth rates (use a chart)
**Answers**: revenue share by region, and which regions are material

```infographic
infographic chart-pie-donut-compact-card
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
  title Revenue By Region — Q3
  desc $12.4M booked, four regions
  values
    - label North America
      value 5.8
    - label Europe
      value 3.9
    - label Asia Pacific
      value 2.1
    - label Rest of world
      value 0.6
```

## Data Shape

`values` in millions; the donut leaves the centre for a total that the surrounding document can annotate.
Keep regions to four or five — more turns the pie into a legend.

## Key Options

| Option | Effect |
|---|---|
| `infographic chart-pie-donut-compact-card` | Donut with descriptive cards |
| `chart-pie-donut-pill-badge` | Badge variant for narrower layouts |
| `chart-pie-donut-plain-text` | Plain text labels — closest to a finance-deck chart |

## Pitfalls

- ❌ Booking region versus delivery region → ✅ state which definition is used
- ❌ Rest-of-world hidden → ✅ small slices still signal where the next investment goes
- ❌ Percentage labels without magnitude → ✅ give the absolute value so the reader can size it

## Alternatives

| Variant | Use instead |
|---|---|
| Revenue by product line | `product-mix-donut-badges.md` |
| Revenue plan over quarters | `revenue-staircase-plan.md` |
| Concentration by top customers | `revenue-concentration-topk-others.md` (vega-lite) |

<!-- source: AntV Infographic syntax docs + template list (`chart-pie-donut-compact-card`) -->
