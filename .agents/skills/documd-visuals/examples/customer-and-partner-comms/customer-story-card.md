# Customer Story Card (HTML/CSS)

**Best for**: a concise customer outcome story where the reader needs the challenge, intervention, and result in one glance
**Avoid when**: the case study needs deep quotations, many metrics, or a full narrative export in searchable text
**Answers**: what changed for the customer, and what measurable result came out of it

<div style="max-width: 900px; box-sizing: border-box; position: relative;">
  <style scoped>
    .card-story { background: #eef2fb;  padding: 30px; font-family: Georgia, 'Times New Roman', serif; }
    .card-story-kicker { margin: 0 0 10px; font-size: 11px; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase; color: #8a5a00; }
    .card-story-title { margin: 0 0 16px; font-size: 32px; line-height: 1.15; }
    .card-story-grid { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 14px; }
    .card-story-panel { padding: 18px; background: rgba(255,255,255,0.62); border-top: 4px solid #7c5a3d; }
    .card-story-label { margin: 0 0 8px; font-size: 11px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #8a5a00; }
    .card-story-text { margin: 0; font-size: 14px; line-height: 1.65;  }
    .card-story-metric { margin-top: 14px; font-size: 28px; font-weight: 700;  }
  </style>
  <section class="card-story">
    <p class="card-story-kicker">Customer Story · Operations Platform</p>
    <h1 class="card-story-title">A National Retailer Cut Checkout Latency During Peak Campaigns</h1>
    <div class="card-story-grid">
      <div class="card-story-panel"><p class="card-story-label">What Changed</p><p class="card-story-text">The retailer moved from a synchronous checkout enrichment path to a queue-first architecture with smaller write transactions and asynchronous fulfillment enrichment.</p></div>
      <div class="card-story-panel"><p class="card-story-label">Measured Result</p><p class="card-story-text">The revised path reduced peak timeout spikes and stabilized cart completion during flash campaigns.</p><p class="card-story-metric">-38% P95 latency</p></div>
    </div>
  </section>
</div>

## Data Shape

Use one customer headline, one compact intervention summary, and one strong result panel with 1–2 proof points.

## Key Options

| Option | Effect |
|---|---|
| Story + result split | Keeps the case narrative separate from the proof metric |
| One dominant outcome number | Gives the reader a quick reason to care |
| Warm editorial styling | Fits external-facing story content |

## Pitfalls

- ❌ Turning the card into a full case study → ✅ keep it to the setup and the measured result
- ❌ Listing many weak metrics → ✅ one strong result is more memorable than a wall of numbers
- ❌ Hiding the intervention itself → ✅ the reader needs both the action and the outcome

## Alternatives

| Variant | Use instead |
|---|---|
| Internal metric board | `metric-snapshot-board.md` |
| Research-style finding summary | `research-abstract-card.md` |
| Executive status memo | `executive-brief-summary.md` |

<!-- source: HTML/CSS inventory notes + infocard customer-story pattern -->