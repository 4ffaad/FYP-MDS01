# Decision Comparison Card (HTML/CSS)

**Best for**: a one-page A/B decision summary where the reader needs a fast qualitative comparison rather than a formal score model
**Avoid when**: the decision depends on weighted criteria, many options, or full evidence traceability
**Answers**: how two options differ, and where each one is stronger or weaker

<div style="max-width: 900px; box-sizing: border-box; position: relative;">
  <style scoped>
    .card-compare { background: #eef2fb;  padding: 28px; font-family: 'Segoe UI', sans-serif; }
    .card-compare-title { margin: 0 0 16px; font-size: 30px; font-weight: 700; }
    .card-compare-grid { display: grid; grid-template-columns: 1fr 60px 1fr; gap: 12px; align-items: stretch; }
    .card-compare-side { padding: 18px; background: #eef2fb; border-top: 4px solid #1f2937; }
    .card-compare-label { margin: 0 0 10px; font-size: 11px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: #6b7280; }
    .card-compare-head { margin: 0 0 12px; font-size: 22px; font-weight: 700;  }
    .card-compare-list { list-style: none; margin: 0; padding: 0; }
    .card-compare-list li { margin-bottom: 10px; font-size: 14px; line-height: 1.55;  }
    .card-compare-vs { display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; letter-spacing: 0.14em; color: #676f7e; }
  </style>
  <section class="card-compare">
    <h1 class="card-compare-title">Managed Database vs Self-Hosted Cluster</h1>
    <div class="card-compare-grid">
      <div class="card-compare-side">
        <p class="card-compare-label">Option A</p>
        <h2 class="card-compare-head">Managed Service</h2>
        <ul class="card-compare-list">
          <li>Lower operational overhead for upgrades and failover.</li>
          <li>Faster provisioning across regions.</li>
          <li>Higher direct spend, but lower staffing burden.</li>
        </ul>
      </div>
      <div class="card-compare-vs">VS</div>
      <div class="card-compare-side">
        <p class="card-compare-label">Option B</p>
        <h2 class="card-compare-head">Self-Hosted Cluster</h2>
        <ul class="card-compare-list">
          <li>More control over topology and tuning.</li>
          <li>Stronger fit for bespoke compliance boundaries.</li>
          <li>Higher maintenance effort and slower recovery operations.</li>
        </ul>
      </div>
    </div>
  </section>
</div>

## Data Shape

This pattern works when each side can be summarized into 3–5 short points and one clear headline per option.

## Key Options

| Option | Effect |
|---|---|
| Split panel comparison | Makes trade-offs explicit without a full matrix |
| One headline per option | Keeps the scan path simple |
| Short bullet points | Highlights qualitative differences fast |

## Pitfalls

- ❌ Turning this into a full scoring framework → ✅ once weighting matters, use a table or chart
- ❌ Comparing more than two options in the same layout → ✅ this pattern is strictly A vs B
- ❌ Long explanatory paragraphs | ✅ keep each side terse and decision-oriented

## Alternatives

| Variant | Use instead |
|---|---|
| SWOT framing | `market-entry-swot.md` |
| Quantitative trade-off chart | `release-plan-tradeoff-fold.md` or another vega/echarts view |
| Executive narrative | `executive-brief-summary.md` |

<!-- source: HTML/CSS inventory notes + infocard comparison/pros-cons patterns -->