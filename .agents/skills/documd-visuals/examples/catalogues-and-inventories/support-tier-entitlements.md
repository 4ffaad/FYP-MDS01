# Icon Rows — Support Tier Entitlements (Infographic)

**Best for**: a row-per-item list where an icon makes each entry scannable at a glance
**Avoid when**: the items have no meaningful icon, or their order carries steps
**Answers**: what each support tier includes, and how the tiers escalate

```infographic
infographic list-row-horizontal-icon-arrow
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
  title Support Tier Entitlements
  desc What each tier buys, from self-service to a named engineer
  lists
    - label Self-serve
      desc Docs, status page and community forum
      icon mdi/book-open-page-variant
    - label Standard
      desc Business-hours queue with a 1 business day target
      icon mdi/headset
    - label Priority
      desc 24x5 queue, 4 hour first response, named CSM
      icon mdi/clock-fast
    - label Enterprise
      desc 24x7 queue, 1 hour first response, shared Slack channel
      icon mdi/shield-account
    - label Mission critical
      desc Dedicated engineer, quarterly resilience review
      icon mdi/account-hard-hat
```

## Data Shape

`lists` with one entry per tier, each carrying `label`, `desc` and an `icon`. Order the entries by escalation
level — the horizontal arrows read left to right as an upgrade path.

## Key Options

| Option | Effect |
|---|---|
| `list-row-horizontal-icon-arrow` | Icon at the leading edge, arrow at the trailing edge of every row |
| `list-row-simple-horizontal-arrow` | No icons, same walking rhythm |
| `list-row-circular-progress` | Adds a progress ring when each row has a completion state |
| `icon` | Any `mdi/*` name; icons are the only decoration this template draws |

## Pitfalls

- ❌ Decorative icons that mean nothing → ✅ an icon is a scan anchor; if it does not label the item, drop it
- ❌ Mixed concepts in one list → ✅ tiers here escalate along one axis; mixing ownership, quality and process in the same list breaks the arrow
- ❌ Long descriptions → ✅ the row is horizontal and thin; keep to one clause per item
- ❌ Arrows on the last row → ✅ the arrow promises a next step; make sure the last entry is a real end state

## Alternatives

| Variant | Use instead |
|---|---|
| Equal-weight inventory with no escalation | `tooling-standard-inventory.md` |
| Progress per item | `onboarding-task-progress.md` |
| Tiers as a pyramid | `partner-tiers-pyramid.md` |

<!-- source: AntV Infographic template registry 0.2.20 (`list-row-horizontal-icon-arrow`, structure `list-row`) -->
