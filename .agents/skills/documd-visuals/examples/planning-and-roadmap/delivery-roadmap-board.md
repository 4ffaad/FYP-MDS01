# Delivery Roadmap Board (HTML/CSS)

**Best for**: quarter-by-quarter delivery intent where the reader needs several upcoming work buckets on one page
**Avoid when**: exact dates, detailed dependencies, or daily planning matter
**Answers**: what is planned for each phase, and how the roadmap is segmented across time

<div style="max-width: 940px; box-sizing: border-box; position: relative;">
  <style scoped>
    .card-roadmap { background: #eef2fb;  padding: 28px; font-family: 'Segoe UI', sans-serif; }
    .card-roadmap-title { margin: 0 0 16px; font-size: 30px; font-weight: 700; }
    .card-roadmap-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
    .card-roadmap-stage { min-height: 220px; padding: 16px; background: rgba(255,255,255,0.88); border-top: 4px solid #1f2937; }
    .card-roadmap-label { margin: 0 0 8px; font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; color: #6b7280; font-weight: 700; }
    .card-roadmap-head { margin: 0 0 12px; font-size: 20px; font-weight: 700;  }
    .card-roadmap-list { list-style: none; margin: 0; padding: 0; }
    .card-roadmap-list li { position: relative; padding-left: 15px; margin-bottom: 8px; font-size: 13px; line-height: 1.55;  }
    .card-roadmap-list li::before { content: '•'; position: absolute; left: 0; top: 0; color: #1f2937; }
  </style>
  <section class="card-roadmap">
    <h1 class="card-roadmap-title">Delivery Roadmap</h1>
    <div class="card-roadmap-grid">
      <section class="card-roadmap-stage"><p class="card-roadmap-label">Q1</p><h2 class="card-roadmap-head">Foundation</h2><ul class="card-roadmap-list"><li>Self-service onboarding</li><li>Identity policy cleanup</li><li>Observability baseline</li></ul></section>
      <section class="card-roadmap-stage"><p class="card-roadmap-label">Q2</p><h2 class="card-roadmap-head">Monetization</h2><ul class="card-roadmap-list"><li>Usage billing reports</li><li>Discount policy engine</li><li>Partner invoicing API</li></ul></section>
      <section class="card-roadmap-stage"><p class="card-roadmap-label">Q3</p><h2 class="card-roadmap-head">Automation</h2><ul class="card-roadmap-list"><li>Queue-first checkout</li><li>Workflow orchestration</li><li>Policy auto-remediation</li></ul></section>
      <section class="card-roadmap-stage"><p class="card-roadmap-label">Q4</p><h2 class="card-roadmap-head">Expansion</h2><ul class="card-roadmap-list"><li>Region failover drills</li><li>Partner portal release</li><li>Enterprise data exports</li></ul></section>
    </div>
  </section>
</div>

## Data Shape

Use one short list per phase. This pattern assumes 3–5 phases or quarters, each with a small set of bullets.

## Key Options

| Option | Effect |
|---|---|
| Even phase columns | Makes roadmap sequencing easy to scan |
| Short bullet lists per stage | Keeps the board strategic rather than operational |
| Repeated stage card styling | Preserves comparability across phases |

## Pitfalls

- ❌ Treating the roadmap like a gantt chart → ✅ this is phase-level intent, not date-exact scheduling
- ❌ Too many bullets per phase → ✅ once each column turns into a page of text, the board stops working
- ❌ Mixing metrics and milestones in the same card | ✅ keep the content homogeneous per board

## Alternatives

| Variant | Use instead |
|---|---|
| Visual milestone sequence | `platform-milestone-timeline.md` |
| Formal execution plan | PlantUML gantt examples |
| One-page strategy memo | `executive-brief-summary.md` |

<!-- source: HTML/CSS inventory notes + infocard roadmap-board pattern -->