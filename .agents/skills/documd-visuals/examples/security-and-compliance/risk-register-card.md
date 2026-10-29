# Risk Register Card (HTML/CSS)

**Best for**: a compact risk review where the reader needs a few major risks, their status, and the current mitigation focus
**Avoid when**: the register is long, heavily quantified, or needs sortable/filterable detail
**Answers**: what the top risks are, how severe they are, and what mitigation is active now

<div style="max-width: 920px; box-sizing: border-box; position: relative;">
  <style scoped>
    .card-risk { background: #eef2fb;  padding: 28px; font-family: 'Segoe UI', sans-serif; }
    .card-risk-title { margin: 0 0 16px; font-size: 30px; font-weight: 700; }
    .card-risk-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
    .card-risk-item { padding: 16px; background: #eef2fb; border-top: 4px solid #8a5a00; }
    .card-risk-name { margin: 0 0 8px; font-size: 18px; font-weight: 700; color: #1f2937; }
    .card-risk-severity { margin: 0 0 8px; font-size: 11px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #d1242f; }
    .card-risk-text { margin: 0; font-size: 13px; line-height: 1.55;  }
  </style>
  <section class="card-risk">
    <h1 class="card-risk-title">Risk Register Snapshot</h1>
    <div class="card-risk-grid">
      <article class="card-risk-item"><h2 class="card-risk-name">Queue Saturation</h2><p class="card-risk-severity">High · Mitigating</p><p class="card-risk-text">Peak campaigns can still exceed autoscale lag tolerance. Mitigation is focused on queue partitioning and tighter alert thresholds.</p></article>
      <article class="card-risk-item"><h2 class="card-risk-name">Credential Drift</h2><p class="card-risk-severity">Medium · Open</p><p class="card-risk-text">Several legacy service identities remain outside the standard rotation flow. Owners and cutoff dates are now assigned.</p></article>
      <article class="card-risk-item"><h2 class="card-risk-name">Partner Backlog</h2><p class="card-risk-severity">Medium · Watching</p><p class="card-risk-text">External fulfillment volume could outpace reconciliation windows in one region. Buffer capacity and fallback routing are under review.</p></article>
    </div>
  </section>
</div>

## Data Shape

Use 3–5 risk items, each with a short title, one severity/status line, and one mitigation-oriented note.

## Key Options

| Option | Effect |
|---|---|
| Repeated risk cards | Gives every risk the same framing for scanability |
| Severity/status line | Conveys urgency without needing a full matrix |
| Warm alert accent | Signals risk review without turning the page into a red alarm board |

## Pitfalls

- ❌ Trying to fit the full register on one card → ✅ this is a snapshot, not the source of record
- ❌ Mixing action owners, dates, and evidence into each block → ✅ keep each card concise and mitigation-focused
- ❌ Using only color for severity meaning → ✅ the severity text itself must carry the signal

## Alternatives

| Variant | Use instead |
|---|---|
| 2×2 prioritization framing | An infographic quadrant template |
| Compliance or controls summary | `compliance-audit-card.md` |
| Detailed spreadsheet-style register | Use tabular output or xlsx |

<!-- source: HTML/CSS inventory notes + infocard risk-register pattern -->