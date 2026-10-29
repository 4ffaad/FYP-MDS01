# Support Ticket Mix — Plain Pie For A Weekly Review (Infographic)

**Best for**: a weekly support review where the category split drives staffing
**Avoid when**: categories change weekly (a stable taxonomy is required for a pie)
**Answers**: how the week's tickets divide by category, without decorative styling

```infographic
infographic chart-pie-plain-text
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
  title Support Tickets — Week 34
  desc 612 tickets across five categories
  values
    - label How-to questions
      value 244
    - label Configuration
      value 158
    - label Bug reports
      value 96
    - label Billing
      value 71
    - label Feature requests
      value 43
```

## Data Shape

`values` with raw counts; the plain-text variant renders labels without cards, which suits an internal
weekly review where the numbers are discussed in the room.

## Key Options

| Option | Effect |
|---|---|
| `infographic chart-pie-plain-text` | Bare labels around the pie |
| `chart-pie-compact-card` | Adds a card per slice with a definition |
| `chart-pie-donut-plain-text` | Donut form; leaves the centre for the total |

## Pitfalls

- ❌ Recategorising every week → ✅ a stable taxonomy is what makes week-over-week reading possible
- ❌ "Other" doing the heavy lifting → ✅ split the tail when it exceeds a tenth of volume
- ❌ Treating categories as severities → ✅ severity and category are different axes

## Alternatives

| Variant | Use instead |
|---|---|
| Traffic sources by share | `traffic-source-mix-split.md` |
| Response tiers and escalation | `support-escalation-pyramid.md` |
| Ticket backlog over a day | `support-shift-handover.md` |

<!-- source: AntV Infographic syntax docs + template list (`chart-pie-plain-text`) -->
