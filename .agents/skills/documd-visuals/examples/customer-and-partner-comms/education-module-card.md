# Education Module Card (HTML/CSS)

**Best for**: a compact teaching or enablement unit where the reader needs the lesson objective, key concepts, and one takeaway block
**Avoid when**: the content needs a full course page, exercises, or searchable long-form learning text
**Answers**: what this module teaches, and what the learner should remember first

<div style="max-width: 900px; box-sizing: border-box; position: relative;">
  <style scoped>
    .card-edu { background: #eef2fb;  padding: 30px; font-family: 'Segoe UI', sans-serif; }
    .card-edu-kicker { margin: 0 0 8px; font-size: 11px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: #676f7e; }
    .card-edu-title { margin: 0 0 14px; font-size: 30px; font-weight: 700; }
    .card-edu-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    .card-edu-panel { padding: 18px; background: #eef2fb; border-top: 4px solid #2b66c4; }
    .card-edu-label { margin: 0 0 8px; font-size: 11px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #676f7e; }
    .card-edu-text { margin: 0; font-size: 14px; line-height: 1.6; color: #676f7e; }
  </style>
  <section class="card-edu">
    <p class="card-edu-kicker">Education Module · Reliability</p>
    <h1 class="card-edu-title">Why Queue-First Checkout Changes Failure Modes</h1>
    <div class="card-edu-grid">
      <div class="card-edu-panel"><p class="card-edu-label">Key Idea</p><p class="card-edu-text">Moving non-critical enrichment off the synchronous request path shortens customer wait time and isolates the peak-failure surface to a smaller write flow.</p></div>
      <div class="card-edu-panel"><p class="card-edu-label">Takeaway</p><p class="card-edu-text">Queue-first design does not remove operational complexity, but it changes where complexity sits and usually improves the customer-facing failure profile.</p></div>
    </div>
  </section>
</div>

## Data Shape

Use one learning objective plus 1–2 support panels that explain the concept and the takeaway.

## Key Options

| Option | Effect |
|---|---|
| Education-style split panels | Separates concept from takeaway |
| Clear teaching headline | Makes the card function like a learning module cover |
| Controlled explanatory text | Keeps the artifact readable rather than lecture-like |

## Pitfalls

- ❌ Treating the card as the full lesson → ✅ this is a module summary, not the whole teaching asset
- ❌ Mixing several unrelated concepts → ✅ each education card should teach one thing well
- ❌ Overusing metrics where explanation is the main need |

## Alternatives

| Variant | Use instead |
|---|---|
| Research summary | `research-abstract-card.md` |
| Executive summary | `executive-brief-summary.md` |
| Formal architecture overview | `layer-stack.md` |

<!-- source: HTML/CSS inventory notes + infocard education-module pattern -->