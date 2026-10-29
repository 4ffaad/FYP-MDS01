# Team Capability Icon Grid — What The Team Can Absorb (Infographic)

**Best for**: a resourcing conversation about which kinds of work the team can take on
**Avoid when**: the reader needs seniority levels (use a skills matrix with levels)
**Answers**: which capability areas the team covers today, each with a visual marker

```infographic
infographic list-grid-horizontal-icon-arrow
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
  title Team Capability Coverage
  desc Areas the team can absorb without help
  lists
    - label Payments
      desc Owns authorisation flows
      icon mdi/credit-card-outline
    - label Data pipelines
      desc Batch and streaming
      icon mdi/pipe-valve
    - label Identity
      desc SSO and access reviews
      icon mdi/shield-account
    - label Observability
      desc Traces, metrics, alerting
      icon mdi/chart-timeline-variant
    - label Mobile
      desc iOS and Android clients
      icon mdi/cellphone
    - label Compliance
      desc Evidence and audit support
      icon mdi/clipboard-check-outline
```

## Data Shape

`lists` with icons; grid layout means items should be comparable in length. Six items fill a 3×2 grid
cleanly, which is the practical maximum before the arrows crowd.

## Key Options

| Option | Effect |
|---|---|
| `infographic list-grid-horizontal-icon-arrow` | Icon grid with arrow accents |
| `list-column-vertical-icon-arrow` | Column variant when the list is a workflow, not a portfolio |
| `list-grid-badge-card` | No icons; use when symbols would be invented rather than chosen |

## Pitfalls

- ❌ Claiming capability without owner → ✅ each area needs at least one named person behind the scenes
- ❌ Icons chosen for looks → ✅ the symbol should say what the area is about
- ❌ Nine-plus areas → ✅ a team that covers nine areas covers none deeply

## Alternatives

| Variant | Use instead |
|---|---|
| On-call coverage as a wheel | `oncall-coverage-wheel.md` |
| Department capability tree | `department-capability-tree.md` |
| Service offerings to customers | `service-offerings-grid.md` |

<!-- source: AntV Infographic syntax docs + template list (`list-grid-horizontal-icon-arrow`) -->
