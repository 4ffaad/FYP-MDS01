# Strategy Focus Wheel — Where Investment Goes (Infographic)

**Best for**: a strategy slide that shows the handful of areas receiving investment this year
**Avoid when**: the areas have budgets that must add up visibly (use a donut or table)
**Answers**: what leadership chose to focus on, and what each focus area means in practice

```infographic
infographic list-sector-plain-text
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
  title FY27 Investment Focus
  desc Five focus areas, no ranking implied
  lists
    - label Durable Data
      desc Own the warehouse layer
    - label Edge Delivery
      desc Push compute closer to users
    - label Trust
      desc Compliance as a feature
    - label AI Assistance
      desc Automate the busywork
    - label Cost Discipline
      desc Unit economics on every launch
```

## Data Shape

Five `lists` items map cleanly onto wheel sectors. Text-only rendering means labels must be short; the
explanation lives in `desc`.

## Key Options

| Option | Effect |
|---|---|
| `infographic list-sector-plain-text` | Equal sectors with plain text labels |
| `list-sector-simple` | Filled sectors with slightly stronger visual weight |
| `list-sector-half-plain-text` | Half wheel for four areas with larger type |

## Pitfalls

- ❌ Implying priority by sector size → ✅ sectors are equal; state explicitly that order is arbitrary
- ❌ Six or seven focus areas → ✅ a strategy with seven focuses has none
- ❌ Abstract nouns ("Excellence") → ✅ use phrases a team could put in a roadmap

## Alternatives

| Variant | Use instead |
|---|---|
| Commercial tiers around a wheel | `subscription-tiers-wheel.md` |
| Focus areas grouped as cards | `service-offerings-grid.md` |
| Strategy expressed as a cycle | `operating-cycle-loop.md` |

<!-- source: AntV Infographic syntax docs + template list (`list-sector-plain-text`) -->
