# Executive Brief — One-Page Summary (HTML/CSS)

**Best for**: summarising one situation, decision, or update in a single page with a strong editorial hierarchy
**Avoid when**: the reader needs charts with axes, deep tables, or editable export text inside the final DOCX/HTML output
**Answers**: what happened, why it matters, and what the reader should pay attention to first

<div style="max-width: 860px; box-sizing: border-box; position: relative;">
  <style scoped>
    .card-brief { background: linear-gradient(180deg, #f4e5ea 0%, #e7e1dc 100%);  padding: 36px; font-family: Georgia, 'Times New Roman', serif; border: 1px solid rgba(0,0,0,0.08); }
    .card-brief-kicker { margin: 0 0 10px; font-size: 11px; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase; color: #8a5a00; }
    .card-brief-title { margin: 0 0 14px; font-size: 34px; line-height: 1.1;  }
    .card-brief-summary { margin: 0 0 22px; max-width: 620px; font-size: 16px; line-height: 1.7;  }
    .card-brief-grid { display: grid; grid-template-columns: 1.4fr 0.9fr; gap: 18px; }
    .card-brief-panel { padding: 18px 20px; background: rgba(255,255,255,0.55); border-top: 4px solid #1f2937; }
    .card-brief-label { margin: 0 0 8px; font-size: 11px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: #8a5a00; }
    .card-brief-text { margin: 0; font-size: 14px; line-height: 1.65;  }
    .card-brief-metrics { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
    .card-brief-metric { padding: 14px; background: rgba(0,0,0,0.04); }
    .card-brief-value { margin: 0; font-size: 24px; font-weight: 700;  }
    .card-brief-name { margin: 6px 0 0; font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;  }
  </style>
  <section class="card-brief">
    <p class="card-brief-kicker">Executive Brief · Platform Update</p>
    <h1 class="card-brief-title">Checkout Reliability Improved After Queue Refactor</h1>
    <p class="card-brief-summary">The team simplified the queueing path between order intake and fulfilment, which removed the main source of timeout spikes during peak campaigns. Customer-facing latency and incident frequency both improved within one release cycle.</p>
    <div class="card-brief-grid">
      <div class="card-brief-panel">
        <p class="card-brief-label">What Changed</p>
        <p class="card-brief-text">The old synchronous enrichment step was replaced with a smaller write path plus background processing. This reduced checkout coupling, shortened request time, and moved non-critical work off the customer path.</p>
      </div>
      <div class="card-brief-metrics">
        <div class="card-brief-metric"><p class="card-brief-value">-38%</p><p class="card-brief-name">P95 latency</p></div>
        <div class="card-brief-metric"><p class="card-brief-value">-61%</p><p class="card-brief-name">Timeout incidents</p></div>
        <div class="card-brief-metric"><p class="card-brief-value">+0.09%</p><p class="card-brief-name">Availability</p></div>
        <div class="card-brief-metric"><p class="card-brief-value">4 min</p><p class="card-brief-name">Peak autoscale lag</p></div>
      </div>
    </div>
  </section>
</div>

## Data Shape

This pattern works best when you have one headline, one short explanatory paragraph, and 3–4 support metrics or highlights.

## Key Options

| Option | Effect |
|---|---|
| Two-column split | Gives one side to narrative and one side to KPI proof |
| Clear kicker/title/summary hierarchy | Tells the reader what to read first without needing charts |
| Small metric tiles | Turns supporting numbers into proof rather than the main story |

## Pitfalls

- ❌ Turning the whole card into prose → ✅ the point is compressed hierarchy, not a mini article
- ❌ Hiding all important facts inside the image-only card → ✅ keep the key message available in surrounding document text too
- ❌ Using many equal-weight boxes → ✅ one-page briefs need a dominant reading order

## Alternatives

| Variant | Use instead |
|---|---|
| Metric-first board | `metric-snapshot-board.md` |
| Architecture overview | `layer-stack.md` |
| Formal comparison | `decision-comparison-card.md` |

<!-- source: HTML/CSS inventory notes + infocard layout patterns (`metric-board`, editorial hierarchy) -->