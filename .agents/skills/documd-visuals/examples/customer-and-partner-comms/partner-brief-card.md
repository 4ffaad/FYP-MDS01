# Partner Brief Card (HTML/CSS)

**Best for**: a short partner-facing summary where the reader needs the offer, context, and next-step framing in one page-like card
**Avoid when**: the content needs contractual detail, long legal wording, or searchable export text for every clause
**Answers**: what the partnership focus is, and why it matters right now

<div style="max-width: 900px; box-sizing: border-box; position: relative;">
  <style scoped>
    .card-partner { background: #eef2fb;  padding: 30px; font-family: 'Segoe UI', sans-serif; }
    .card-partner-meta { margin: 0 0 8px; font-size: 11px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase;  }
    .card-partner-title { margin: 0 0 14px; font-size: 30px; font-weight: 700; }
    .card-partner-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    .card-partner-panel { padding: 16px 18px; background: #eef2fb; border-top: 4px solid #2b66c4; }
    .card-partner-label { margin: 0 0 8px; font-size: 11px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase;  }
    .card-partner-text { margin: 0; font-size: 14px; line-height: 1.6;  }
  </style>
  <section class="card-partner">
    <p class="card-partner-meta">Partner Brief · Channel Update</p>
    <h1 class="card-partner-title">Regional Resellers Can Now Offer Queue-First Checkout</h1>
    <div class="card-partner-grid">
      <div class="card-partner-panel"><p class="card-partner-label">What’s New</p><p class="card-partner-text">Partners can position the queue-first checkout path as a reliability upgrade for high-traffic retail operations, with a focused story around latency reduction and better operational resilience.</p></div>
      <div class="card-partner-panel"><p class="card-partner-label">How to Use It</p><p class="card-partner-text">Lead with the simplified architecture and measurable checkout improvement, then connect the story to customer-specific campaign risk, traffic surges, and rollout safety.</p></div>
    </div>
  </section>
</div>

## Data Shape

Use one short external-facing headline plus two compact panels: the update itself and how the partner should position it.

## Key Options

| Option | Effect |
|---|---|
| Two-panel external brief | Separates announcement from guidance |
| Clean partner-facing palette | Keeps the card formal and distribution-ready |
| Short framing text | Preserves scanability for shared enablement assets |

## Pitfalls

- ❌ Turning a partner brief into a full sales deck → ✅ keep it to the one-page summary and talking point framing
- ❌ Overloading it with internal implementation detail → ✅ the partner needs a positioning story, not the whole architecture |
- ❌ Using dense KPI walls in place of a message → ✅ one strong partner story is usually better than many small metrics |

## Alternatives

| Variant | Use instead |
|---|---|
| Sales metric snapshot | `sales-brief-card.md` |
| Executive internal brief | `executive-brief-summary.md` |
| Customer outcome story | `customer-story-card.md` |

<!-- source: HTML/CSS inventory notes + infocard partner-channel / partner-brief patterns -->