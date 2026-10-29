# Research Abstract Card (HTML/CSS)

**Best for**: summarising one investigation, experiment, or study into a concise abstract with method and findings
**Avoid when**: the audience needs raw tables, a long literature review, or fully searchable export text inside the card itself
**Answers**: what was studied, how it was checked, and what the main finding was

<div style="max-width: 860px; box-sizing: border-box; position: relative;">
  <style scoped>
    .card-abstract { background: #eef2fb;  padding: 32px; font-family: Georgia, 'Times New Roman', serif; border-left: 6px solid #1f2937; }
    .card-abstract-meta { margin: 0 0 10px; font-size: 11px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: #6b7280; }
    .card-abstract-title { margin: 0 0 14px; font-size: 30px; line-height: 1.18;  }
    .card-abstract-grid { display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 14px; }
    .card-abstract-panel { padding: 16px 18px; background: rgba(0,0,0,0.03); }
    .card-abstract-label { margin: 0 0 8px; font-size: 11px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #6b7280; }
    .card-abstract-text { margin: 0; font-size: 14px; line-height: 1.7;  }
  </style>
  <section class="card-abstract">
    <p class="card-abstract-meta">Research Abstract · Platform Study</p>
    <h1 class="card-abstract-title">Queue-First Checkout Reduced Peak Latency Without Harming Completion Rate</h1>
    <div class="card-abstract-grid">
      <div class="card-abstract-panel"><p class="card-abstract-label">Summary</p><p class="card-abstract-text">We compared synchronous checkout enrichment with a queue-first design across four high-volume campaigns. The queue-first path lowered tail latency and error spikes while preserving conversion within normal variance bounds.</p></div>
      <div class="card-abstract-panel"><p class="card-abstract-label">Key Finding</p><p class="card-abstract-text">Peak latency fell by 38%, timeout incidents fell by 61%, and completion rate stayed statistically flat relative to the previous release path.</p></div>
    </div>
  </section>
</div>

## Data Shape

Use one abstract-style headline, one short findings paragraph, and one compact result panel or method panel.

## Key Options

| Option | Effect |
|---|---|
| Abstract-style left rule | Signals “study / memo / finding” rather than dashboard or memo board |
| One main summary plus one result panel | Gives the card a clean academic rhythm |
| Serif-heavy editorial style | Fits the abstract/reporting tone |

## Pitfalls

- ❌ Listing every experiment detail inside the card → ✅ keep this to the abstract and main takeaway
- ❌ Turning the finding into a KPI wall → ✅ this is about the result narrative, not a dashboard |
- ❌ Using the card as the only place the conclusion exists → ✅ mirror the result in surrounding prose too

## Alternatives

| Variant | Use instead |
|---|---|
| KPI-heavy summary | `metric-snapshot-board.md` |
| Executive one-page narrative | `executive-brief-summary.md` |
| Rich analytical chart support | Vega / ECharts examples |

<!-- source: HTML/CSS inventory notes + infocard research-abstract pattern -->