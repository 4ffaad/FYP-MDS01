# Compliance Audit Card (HTML/CSS)

**Best for**: a compact control review or trust update where the reader needs status, evidence themes, and notable gaps quickly
**Avoid when**: you need a full audit workbook, detailed controls matrix, or searchable export text for every evidence note
**Answers**: what controls were checked, what passed, and what remains open

<div style="max-width: 900px; box-sizing: border-box; position: relative;">
  <style scoped>
    .card-audit { background: #eef2fb;  padding: 30px; font-family: 'Segoe UI', sans-serif; }
    .card-audit-meta { margin: 0 0 8px; font-size: 11px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase;  }
    .card-audit-title { margin: 0 0 16px; font-size: 30px; font-weight: 700; }
    .card-audit-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
    .card-audit-panel { padding: 16px; background: #eef2fb; border-top: 4px solid #334155; }
    .card-audit-label { margin: 0 0 8px; font-size: 11px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase;  }
    .card-audit-stat { margin: 0 0 10px; font-size: 26px; font-weight: 700;  }
    .card-audit-text { margin: 0; font-size: 13px; line-height: 1.55;  }
  </style>
  <section class="card-audit">
    <p class="card-audit-meta">Trust Update · Internal Audit</p>
    <h1 class="card-audit-title">Control Review Summary</h1>
    <div class="card-audit-grid">
      <section class="card-audit-panel"><p class="card-audit-label">Controls Passed</p><p class="card-audit-stat">17 / 19</p><p class="card-audit-text">Identity policy, encryption at rest, logging retention, backup restore, and privileged access checks all passed review.</p></section>
      <section class="card-audit-panel"><p class="card-audit-label">Open Gaps</p><p class="card-audit-stat">2</p><p class="card-audit-text">Evidence packaging for vendor review is inconsistent, and quarterly key-rotation proof is not yet centrally archived.</p></section>
      <section class="card-audit-panel"><p class="card-audit-label">Remediation Window</p><p class="card-audit-stat">21 Days</p><p class="card-audit-text">Owners are assigned, mitigation steps are approved, and the follow-up check is scheduled for the next governance review.</p></section>
    </div>
  </section>
</div>

## Data Shape

Use 3–4 compact panels: one for pass status, one for gaps, and one for next action or timeline.

## Key Options

| Option | Effect |
|---|---|
| Equal-width audit panels | Keeps the control review summary balanced and structured |
| Stat + explanation pairing | Gives both numeric status and a short interpretation |
| Formal but quiet palette | Fits compliance/trust reporting better than aggressive alert styling |

## Pitfalls

- ❌ Trying to list every control on one card → ✅ summarize; move control-by-control detail to a matrix or appendix
- ❌ Using red/green everywhere → ✅ compliance reviews need emphasis, but not a Christmas tree palette
- ❌ Putting unresolved detail only in the card image → ✅ keep the key issues mirrored in surrounding text

## Alternatives

| Variant | Use instead |
|---|---|
| Rich incident chronology | `incident-review-card.md` |
| Security architecture context | PlantUML security examples |
| KPI-style trust dashboard | `metric-snapshot-board.md` |

<!-- source: HTML/CSS inventory notes + infocard compliance-audit pattern -->