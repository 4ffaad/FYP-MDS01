# News Bulletin Card (HTML/CSS)

**Best for**: short update headlines where the reader needs several announcements grouped into one page-like bulletin
**Avoid when**: each update needs deep narrative, formal decision logging, or analytics-heavy visuals
**Answers**: what the latest announcements are, and which updates deserve immediate attention

<div style="max-width: 920px; box-sizing: border-box; position: relative;">
  <style scoped>
    .card-news { background: #eef2fb;  padding: 28px; font-family: 'Segoe UI', sans-serif; }
    .card-news-title { margin: 0 0 16px; font-size: 30px; font-weight: 700; }
    .card-news-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
    .card-news-item { padding: 16px; background: #eef2fb; border-top: 4px solid #1f2937; }
    .card-news-tag { margin: 0 0 8px; font-size: 11px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #6b7280; }
    .card-news-head { margin: 0 0 8px; font-size: 18px; font-weight: 700;  }
    .card-news-text { margin: 0; font-size: 13px; line-height: 1.55; color: #4b5563; }
  </style>
  <section class="card-news">
    <h1 class="card-news-title">Platform Bulletin</h1>
    <div class="card-news-grid">
      <article class="card-news-item"><p class="card-news-tag">Release</p><h2 class="card-news-head">Queue-First Checkout Enabled</h2><p class="card-news-text">The new path is now active in the primary region and will expand after one more week of observation.</p></article>
      <article class="card-news-item"><p class="card-news-tag">Policy</p><h2 class="card-news-head">90-Day Credential Rotation Standard</h2><p class="card-news-text">Service owners must now register and evidence all production credential rotation events centrally.</p></article>
      <article class="card-news-item"><p class="card-news-tag">Metrics</p><h2 class="card-news-head">Latency Improved During Peak Demand</h2><p class="card-news-text">Observed P95 checkout latency improved by 38% during the latest promotion window.</p></article>
    </div>
  </section>
</div>

## Data Shape

Use 3–4 short bulletin items, each with one tag, one headline, and one short supporting paragraph.

## Key Options

| Option | Effect |
|---|---|
| Equal-width bulletin cards | Gives each announcement one quick scan unit |
| Tag + headline pattern | Helps readers categorize the update before reading details |
| Tight card grid | Makes several updates fit on one page without becoming a memo wall |

## Pitfalls

- ❌ Long article-style updates in each card → ✅ bulletin cards should stay brief and headline-led
- ❌ Mixing too many unrelated formatting styles → ✅ keep the bulletin visually consistent |
- ❌ Using bulletins for one single message → ✅ switch to a memo or brief when one update dominates |

## Alternatives

| Variant | Use instead |
|---|---|
| One dominant update | `executive-brief-summary.md` |
| Incident-specific operational update | `incident-review-card.md` |
| Customer-facing case summary | `customer-story-card.md` |

<!-- source: HTML/CSS inventory notes + infocard news-bulletin pattern -->