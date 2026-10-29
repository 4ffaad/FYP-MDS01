# Sales Brief Card (HTML/CSS)

**Best for**: a short sales-facing summary where the reader needs the positioning angle, proof point, and commercial hook in one page
**Avoid when**: the content needs full battlecards, pricing tables, or detailed customer segmentation logic
**Answers**: what the sales message is, and what proof or hook supports it

<div style="max-width: 900px; box-sizing: border-box; position: relative;">
  <style scoped>
    .card-sales { background: #eef2fb;  padding: 30px; font-family: 'Segoe UI', sans-serif; }
    .card-sales-kicker { margin: 0 0 8px; font-size: 11px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: #7c5a3d; }
    .card-sales-title { margin: 0 0 14px; font-size: 30px; font-weight: 700; }
    .card-sales-grid { display: grid; grid-template-columns: 1fr 0.9fr; gap: 14px; }
    .card-sales-panel { padding: 18px; background: #eef2fb; border-top: 4px solid #7c5a3d; }
    .card-sales-label { margin: 0 0 8px; font-size: 11px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #7c5a3d; }
    .card-sales-text { margin: 0; font-size: 14px; line-height: 1.6;  }
    .card-sales-proof { margin-top: 12px; font-size: 28px; font-weight: 700;  }
  </style>
  <section class="card-sales">
    <p class="card-sales-kicker">Sales Brief · Positioning</p>
    <h1 class="card-sales-title">Queue-First Checkout Reduces Peak-Campaign Risk</h1>
    <div class="card-sales-grid">
      <div class="card-sales-panel"><p class="card-sales-label">Talk Track</p><p class="card-sales-text">Position the offer around operational resilience during demand spikes: shorter synchronous paths, fewer visible timeout incidents, and better release safety for high-volume campaigns.</p></div>
      <div class="card-sales-panel"><p class="card-sales-label">Proof Point</p><p class="card-sales-text">Observed improvement in the first high-traffic rollout window.</p><p class="card-sales-proof">-38% P95 latency</p></div>
    </div>
  </section>
</div>

## Data Shape

Use one positioning headline, one short sales talk-track panel, and one proof panel with a single dominant number.

## Key Options

| Option | Effect |
|---|---|
| Sales message + proof split | Separates positioning from evidence |
| Single dominant proof metric | Gives the reader one memorable commercial hook |
| Warm commercial palette | Fits sales/enablement tone without looking like a dashboard |

## Pitfalls

- ❌ Turning the brief into a full battlecard → ✅ this should stay compact and message-first
- ❌ Including too many proof points → ✅ one strong metric is stronger than many weak ones |
- ❌ Using sales language with no evidence | ✅ every pitch card needs one proof anchor |

## Alternatives

| Variant | Use instead |
|---|---|
| Partner-facing framing | `partner-brief-card.md` |
| Customer outcome narrative | `customer-story-card.md` |
| Metric-heavy board | `metric-snapshot-board.md` |

<!-- source: HTML/CSS inventory notes + infocard sales-room / sales-brief patterns -->