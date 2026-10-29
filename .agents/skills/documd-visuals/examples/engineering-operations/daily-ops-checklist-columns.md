# Daily Ops Checklist Columns — Vertical Icon List (Infographic)

**Best for**: a daily operator checklist where each item is one visual verification
**Avoid when**: items need to be checked off interactively (use a task list, not an image)
**Answers**: the routine checks, in the order they are performed, with an icon per check

```infographic
infographic list-column-vertical-icon-arrow
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
  title Morning Platform Checks
  desc One icon per check, top to bottom
  lists
    - label Cluster health
      desc All nodes green
      icon mdi/server-network
    - label Queue depth
      desc Below 500 messages
      icon mdi/tray-full
    - label Certificate expiry
      desc Nothing under 30 days
      icon mdi/certificate-outline
    - label Backup completion
      desc Last night’s snapshot verified
      icon mdi/backup-restore
```

## Data Shape

`lists` with one `icon` per item, ordered top to bottom. The vertical arrow layout implies order, so write the
checks in the sequence they are performed.

## Key Options

| Option | Effect |
|---|---|
| `infographic list-column-vertical-icon-arrow` | Vertical column with icons and arrows |
| `list-column-simple-vertical-arrow` | No icons; use when symbols add nothing |
| `list-grid-horizontal-icon-arrow` | Grid variant when the checks are independent |

## Pitfalls

- ❌ Icons that duplicate the label → ✅ the icon should encode the check type, not repeat the words
- ❌ Vague pass criteria → ✅ "below 500 messages" beats "check the queue"
- ❌ Twelve checks → ✅ a morning checklist has four to six that matter

## Alternatives

| Variant | Use instead |
|---|---|
| Release readiness checks | `launch-readiness-checklist.md` |
| Ordered response steps | `incident-response-runbook.md` |
| Coverage areas as a wheel | `oncall-coverage-wheel.md` |

<!-- source: AntV Infographic syntax docs + template list (`list-column-vertical-icon-arrow`) -->
