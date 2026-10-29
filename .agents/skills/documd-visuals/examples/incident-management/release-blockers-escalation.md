# Release Blockers Escalation — Icon-Annotated Open Items (Infographic)

**Best for**: a release-readiness note listing exactly what is blocking the cut
**Avoid when**: the list is long enough to need owners and dates (use a table)
**Answers**: which blockers are still open, and which kind of help each one needs

```infographic
infographic list-row-horizontal-icon-line
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
  title Blockers Before The 4.2 Cut
  desc Open items, owner named in the description
  lists
    - label Payment migration
      desc Needs DBA window — owner: Priya
      icon mdi/database-alert
    - label Localization review
      desc Missing ja/ko strings — owner: Marco
      icon mdi/translate
    - label Perf regression
      desc p95 up 220ms — owner: Dana
      icon mdi/speedometer-slow
    - label Store assets
      desc Screenshots pending — owner: Wen
      icon mdi/image-multiple
```

## Data Shape

`lists` with `icon` per item. The icon doubles as a category cue — use it for the *kind* of blocker
(data, content, performance, packaging) rather than a decorative picture.

## Key Options

| Option | Effect |
|---|---|
| `infographic list-row-horizontal-icon-line` | Icon plus connector line per item |
| `list-row-horizontal-icon-arrow` | Adds arrowheads — reads as a progression |
| `list-grid-horizontal-icon-arrow` | Grid variant when there are more than five items |

## Pitfalls

- ❌ Icons that all look alike → ✅ pick distinct symbols; a repeated icon adds noise, not signal
- ❌ No owner in the item → ✅ blockers without an owner are the ones that slip
- ❌ Mixing resolved and open items → ✅ show open only; history belongs in the changelog

## Alternatives

| Variant | Use instead |
|---|---|
| Release checklist with completion state | `launch-readiness-checklist.md` |
| Quality gate metrics | `team-throughput-bars.md` |
| Blocker flow across an escalation ladder | `incident-escalation-path.md` |

<!-- source: AntV Infographic syntax docs + template list (`list-row-horizontal-icon-line`) -->
