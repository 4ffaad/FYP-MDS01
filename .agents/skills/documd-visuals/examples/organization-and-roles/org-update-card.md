# Org Update Card (HTML/CSS)

**Best for**: a concise internal team or organization update where the reader needs the structural change and the rationale quickly
**Avoid when**: the announcement includes full role descriptions, staffing tables, or sensitive HR detail
**Answers**: what changed in the organization, and how responsibilities are now grouped

<div style="max-width: 900px; box-sizing: border-box; position: relative;">
  <style scoped>
    .card-org { background: #eef2fb;  padding: 28px; font-family: 'Segoe UI', sans-serif; }
    .card-org-title { margin: 0 0 14px; font-size: 30px; font-weight: 700; }
    .card-org-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
    .card-org-panel { padding: 16px; background: #eef2fb; border-top: 4px solid #4b5563; }
    .card-org-label { margin: 0 0 8px; font-size: 11px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #6b7280; }
    .card-org-text { margin: 0; font-size: 13px; line-height: 1.55; color: #4b5563; }
  </style>
  <section class="card-org">
    <h1 class="card-org-title">Organization Update</h1>
    <div class="card-org-grid">
      <section class="card-org-panel"><p class="card-org-label">Platform</p><p class="card-org-text">Core infrastructure, identity, and shared runtime services now sit in one platform group.</p></section>
      <section class="card-org-panel"><p class="card-org-label">Product Delivery</p><p class="card-org-text">Checkout, billing, and partner-facing flows remain embedded with delivery-oriented teams.</p></section>
      <section class="card-org-panel"><p class="card-org-label">Reliability</p><p class="card-org-text">SRE and security operations now share one operating review cycle and incident cadence.</p></section>
    </div>
  </section>
</div>

## Data Shape

Use 3–4 structural update blocks, each representing a team, function, or responsibility grouping.

## Key Options

| Option | Effect |
|---|---|
| Equal update blocks | Gives each org area one compact explanation |
| Structure-first labels | Keeps the announcement focused on the organizational change |
| Neutral palette | Fits internal update communications |

## Pitfalls

- ❌ Including full job architecture in one card → ✅ this is for the update message, not the entire org design reference
- ❌ Mixing too many personnel details → ✅ keep the view at team or function level |
- ❌ Using this instead of an actual hierarchy view when reporting lines matter | ✅ switch to hierarchy examples when structure is the story |

## Alternatives

| Variant | Use instead |
|---|---|
| Hierarchical org tree | `platform-org-structure.md` or `team-reporting-tree.md` |
| Policy change summary | `policy-memo-card.md` |
| Executive team brief | `executive-brief-summary.md` |

<!-- source: HTML/CSS inventory notes + infocard org-update pattern -->