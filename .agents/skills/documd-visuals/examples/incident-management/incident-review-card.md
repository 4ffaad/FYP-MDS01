# Incident Review Card (HTML/CSS)

**Best for**: one-page incident summaries that need a short timeline, impact statement, and remediation status in one frame
**Avoid when**: the reader needs deep root-cause detail, long logs, or searchable export text inside the card itself
**Answers**: what happened, what the impact was, and what is being done next

<div style="max-width: 880px; box-sizing: border-box; position: relative;">
  <style scoped>
    .card-incident { background: #eef2fb;  padding: 30px; font-family: 'Segoe UI', sans-serif; }
    .card-incident-kicker { margin: 0 0 8px; font-size: 11px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: #d1242f; }
    .card-incident-title { margin: 0 0 14px; font-size: 30px; line-height: 1.15;  }
    .card-incident-grid { display: grid; grid-template-columns: 1.2fr 0.9fr; gap: 14px; }
    .card-incident-panel { padding: 18px; background: rgba(255,255,255,0.65); border-top: 4px solid #7c5a3d; }
    .card-incident-label { margin: 0 0 8px; font-size: 11px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #d1242f; }
    .card-incident-text { margin: 0; font-size: 14px; line-height: 1.6;  }
    .card-incident-timeline { list-style: none; margin: 0; padding: 0; }
    .card-incident-timeline li { display: grid; grid-template-columns: 62px 1fr; gap: 10px; margin-bottom: 10px; font-size: 13px; line-height: 1.5;  }
    .card-incident-timeline li:last-child { margin-bottom: 0; }
    .card-incident-time { font-weight: 700; color: #d1242f; }
  </style>
  <section class="card-incident">
    <p class="card-incident-kicker">Incident Review · SEV-2</p>
    <h1 class="card-incident-title">Checkout Timeout Spike During Campaign Launch</h1>
    <div class="card-incident-grid">
      <div class="card-incident-panel">
        <p class="card-incident-label">Summary</p>
        <p class="card-incident-text">A synchronous enrichment step saturated the order queue during a demand surge, which caused customer-facing checkout timeouts for 23 minutes. Traffic was stabilized by disabling the slow path and draining the queue backlog.</p>
      </div>
      <div class="card-incident-panel">
        <p class="card-incident-label">Timeline</p>
        <ul class="card-incident-timeline">
          <li><span class="card-incident-time">09:12</span><span>Timeout alerts triggered in the primary region.</span></li>
          <li><span class="card-incident-time">09:18</span><span>Queue depth exceeded fallback threshold.</span></li>
          <li><span class="card-incident-time">09:27</span><span>Slow enrichment path disabled via feature flag.</span></li>
          <li><span class="card-incident-time">09:35</span><span>Error rate and latency returned to normal.</span></li>
        </ul>
      </div>
    </div>
  </section>
</div>

## Data Shape

This works best when you have one incident summary paragraph plus 3–5 timeline points or actions.

## Key Options

| Option | Effect |
|---|---|
| Two-panel split | Separates narrative summary from operational timeline |
| Time/value grid rows | Makes the incident timeline scannable |
| Warm severity accent | Signals operational seriousness without a full red alert board |

## Pitfalls

- ❌ Writing the full postmortem inside the card → ✅ keep the card to the operational summary and timeline
- ❌ Mixing too many secondary metrics into the same frame → ✅ this pattern is about the incident story first
- ❌ Relying on the image-only export for all details → ✅ keep the core facts available in surrounding text too

## Alternatives

| Variant | Use instead |
|---|---|
| Metric-heavy status board | `metric-snapshot-board.md` |
| Formal executive update | `executive-brief-summary.md` |
| Sequenced remediation roadmap | `delivery-roadmap-board.md` |

<!-- source: HTML/CSS inventory notes + infocard incident-review pattern -->