# Metric Snapshot Board (HTML/CSS)

**Best for**: a dashboard-like one-page metric summary where the numbers themselves are the main message
**Avoid when**: you need proper statistical charts or a long explanatory narrative
**Answers**: what the current operating snapshot looks like, and which metrics are notably above or below target

<div style="max-width: 860px; box-sizing: border-box; position: relative;">
  <style scoped>
    .card-snapshot { background: #eef2fb;  padding: 34px; font-family: 'Segoe UI', sans-serif; }
    .card-snapshot-meta { margin: 0 0 8px; font-size: 11px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase;  }
    .card-snapshot-title { margin: 0 0 14px; font-size: 30px; line-height: 1.15;  }
    .card-snapshot-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
    .card-snapshot-tile { padding: 16px; background: #eef2fb; border-top: 4px solid #1f2937; }
    .card-snapshot-value { margin: 0; font-size: 28px; font-weight: 700;  }
    .card-snapshot-label { margin: 8px 0 0; font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: #6b7280; }
    .card-snapshot-delta { margin: 6px 0 0; font-size: 12px; font-weight: 600; }
    .card-snapshot-delta.good { color: #1f7a33; }
    .card-snapshot-delta.warn { color: #8a5a00; }
    .card-snapshot-delta.bad { color: #d1242f; }
  </style>
  <section class="card-snapshot">
    <p class="card-snapshot-meta">Metric Snapshot · Week 39</p>
    <h1 class="card-snapshot-title">Operations Dashboard</h1>
    <div class="card-snapshot-grid">
      <div class="card-snapshot-tile"><p class="card-snapshot-value">99.96%</p><p class="card-snapshot-label">Availability</p><p class="card-snapshot-delta good">+0.04% vs target</p></div>
      <div class="card-snapshot-tile"><p class="card-snapshot-value">182ms</p><p class="card-snapshot-label">P95 Latency</p><p class="card-snapshot-delta good">-27ms week-on-week</p></div>
      <div class="card-snapshot-tile"><p class="card-snapshot-value">0.08%</p><p class="card-snapshot-label">Error Rate</p><p class="card-snapshot-delta good">Below threshold</p></div>
      <div class="card-snapshot-tile"><p class="card-snapshot-value">74%</p><p class="card-snapshot-label">CPU Peak</p><p class="card-snapshot-delta warn">Closer to scaling band</p></div>
      <div class="card-snapshot-tile"><p class="card-snapshot-value">2.6M</p><p class="card-snapshot-label">Requests / Day</p><p class="card-snapshot-delta good">+11% demand growth</p></div>
      <div class="card-snapshot-tile"><p class="card-snapshot-value">14</p><p class="card-snapshot-label">Open Incidents</p><p class="card-snapshot-delta bad">+4 unresolved</p></div>
      <div class="card-snapshot-tile"><p class="card-snapshot-value">3.8 min</p><p class="card-snapshot-label">Auto-Scale Delay</p><p class="card-snapshot-delta warn">Near watch level</p></div>
      <div class="card-snapshot-tile"><p class="card-snapshot-value">$4.9K</p><p class="card-snapshot-label">Daily Cloud Cost</p><p class="card-snapshot-delta good">Flat vs budget</p></div>
    </div>
  </section>
</div>

## Data Shape

Use this when you have 6–8 peer metrics and each can be expressed in a single value plus a short delta or qualifier.

## Key Options

| Option | Effect |
|---|---|
| Uniform KPI grid | Gives the metrics equal visual weight |
| Value / label / delta rhythm | Keeps each tile compact and scannable |
| Status color on deltas | Adds quick interpretation without a chart |

## Pitfalls

- ❌ Mixing long prose into KPI tiles → ✅ tiles should stay numeric and short
- ❌ Fifteen metrics on one board → ✅ if everything is on the board, nothing is important
- ❌ Using tiles for trends → ✅ once time matters, move to charts

## Alternatives

| Variant | Use instead |
|---|---|
| Story-first one-page brief | `executive-brief-summary.md` |
| One KPI plus supporting charts | `kpi-dashboard.md` |
| Funnel or sequence narrative | infographic sequence templates |

<!-- source: HTML/CSS inventory notes + infocard metric-board pattern -->