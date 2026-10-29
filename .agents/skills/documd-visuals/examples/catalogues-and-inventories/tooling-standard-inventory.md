# Simple Grid — Approved Internal Tooling (Infographic)

**Best for**: a flat inventory where every item has equal weight and nothing is sequential
**Avoid when**: the items have an order, a hierarchy or per-item numbers
**Answers**: what the standard toolset is, and what each item is responsible for

```infographic
infographic list-grid-simple
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
  title Approved Internal Tooling
  desc The default stack for new services — anything else needs a waiver
  lists
    - label Observability
      desc OpenTelemetry traces, Prometheus metrics, Loki logs
    - label CI/CD
      desc Shared pipeline templates with signed artifacts
    - label Secrets
      desc Vault-backed injection, no long-lived credentials
    - label Feature flags
      desc Percentage rollout with per-tenant overrides
    - label Schema migrations
      desc Versioned, backward-compatible, gated in CI
    - label Incident tooling
      desc Paging, on-call rotation, postmortem template
```

## Data Shape

`lists` with one entry per item and no ordering semantics — the plainest reading of an inventory. Six entries
fill the grid evenly; odd counts leave a ragged last row.

## Key Options

| Option | Effect |
|---|---|
| `list-grid-simple` | The neutral grid: no progress, no badges, no icons |
| `list-grid-badge-card` | Adds a badge slot when items carry a status |
| `list-grid-compact-card` | Tighter cards, better when entries are text-heavy |
| `list-grid-candy-card-lite` | Softer card treatment for outward-facing decks |
| Even entry count | The grid has no emphasis, so a ragged row is the only visible irregularity |

## Pitfalls

- ❌ Using the plainest grid for a prioritised list → ✅ nothing here ranks the items; use `list-pyramid` or a scored table
- ❌ Items whose descriptions differ wildly in length → ✅ the grid is uniform, so long cells stretch every row
- ❌ Seven or eight entries → ✅ the grid wraps to a second row with no emphasis; group instead
- ❌ Reusing it for categories plus counts → ✅ that is a chart; the list carries names, not magnitudes

## Alternatives

| Variant | Use instead |
|---|---|
| Items with icons and arrows | `support-tier-entitlements.md` |
| Items with progress state | `onboarding-task-progress.md` |
| Ranked capabilities | `capability-pyramid-framework.md` |

<!-- source: AntV Infographic template registry 0.2.20 (`list-grid-simple`, structure `list-grid`) -->
