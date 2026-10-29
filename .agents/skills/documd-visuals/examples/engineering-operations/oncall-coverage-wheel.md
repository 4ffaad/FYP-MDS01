# On-Call Coverage Wheel — Half Wheel Of Competencies (Infographic)

**Best for**: showing which competencies the on-call rotation must cover
**Avoid when**: the reader needs named engineers per area (use a skills matrix)
**Answers**: the coverage areas for on-call and what each one expects

```infographic
infographic list-sector-half-plain-text
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
  title On-Call Coverage Areas
  desc Four competency areas, one rotation
  lists
    - label Datastores
      desc Restore, failover, migrations
    - label Networking
      desc DNS, load balancers, TLS
    - label Application
      desc Deploys, feature flags, rollback
    - label Third-party
      desc Vendor incidents and quotas
```

## Data Shape

Four `lists` items — the half-wheel gives each sector more room, so four areas is the natural fit. The
`desc` names the class of incident the competency covers.

## Key Options

| Option | Effect |
|---|---|
| `infographic list-sector-half-plain-text` | Half wheel, large labels |
| `list-sector-simple` | Full wheel when there are five or six areas |
| `list-grid-compact-card` | Cards when each area needs an owner named |

## Pitfalls

- ❌ Coverage areas nobody is trained on → ✅ the wheel is a training gap detector, use it that way
- ❌ Six areas on a half wheel → ✅ half wheels hold four comfortably
- ❌ Confusing coverage with ownership → ✅ areas are competencies, not people

## Alternatives

| Variant | Use instead |
|---|---|
| Daily checks per area | `daily-ops-checklist-columns.md` |
| Escalation when coverage fails | `incident-escalation-path.md` |
| Team reporting structure | `team-reporting-tree.md` |

<!-- source: AntV Infographic syntax docs + template list (`list-sector-half-plain-text`) -->
