# Policy Memo Card (HTML/CSS)

**Best for**: a compact internal policy update where the reader needs the decision, scope, and required action on one page
**Avoid when**: the full policy text, clause-by-clause reasoning, or searchable export text is the primary requirement
**Answers**: what changed, who it affects, and what people need to do now

<div style="max-width: 860px; box-sizing: border-box; position: relative;">
  <style scoped>
    .card-policy { background: #eef2fb;  padding: 32px; font-family: Georgia, 'Times New Roman', serif; border: 1px solid rgba(0,0,0,0.08); }
    .card-policy-kicker { margin: 0 0 10px; font-size: 11px; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase;  }
    .card-policy-title { margin: 0 0 14px; font-size: 32px; line-height: 1.15;  }
    .card-policy-body { margin: 0 0 18px; font-size: 15px; line-height: 1.75;  }
    .card-policy-grid { display: grid; grid-template-columns: 0.95fr 1.05fr; gap: 14px; }
    .card-policy-panel { padding: 16px 18px; background: rgba(255,255,255,0.62); border-top: 4px solid #1f2937; }
    .card-policy-label { margin: 0 0 8px; font-size: 11px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase;  }
    .card-policy-text { margin: 0; font-size: 14px; line-height: 1.6;  }
  </style>
  <section class="card-policy">
    <p class="card-policy-kicker">Policy Memo · Internal Standard</p>
    <h1 class="card-policy-title">Credential Rotation Now Required Every 90 Days</h1>
    <p class="card-policy-body">This update standardizes credential hygiene across platform services. All production-facing service accounts must rotate keys on a 90-day maximum cycle, with rotation evidence recorded in the central audit workspace.</p>
    <div class="card-policy-grid">
      <div class="card-policy-panel"><p class="card-policy-label">Applies To</p><p class="card-policy-text">Production service accounts, CI/CD deploy identities, partner integration secrets, and database access credentials used outside ephemeral runtime issuance.</p></div>
      <div class="card-policy-panel"><p class="card-policy-label">Required Action</p><p class="card-policy-text">Service owners must register rotation dates, move unmanaged long-lived credentials into the approved secrets workflow, and close all existing exceptions before the next governance review.</p></div>
    </div>
  </section>
</div>

## Data Shape

This pattern fits one policy headline, one short summary paragraph, and 2–3 focused panels explaining scope and action.

## Key Options

| Option | Effect |
|---|---|
| Memo-style hierarchy | Keeps the policy statement dominant over implementation detail |
| Split explanatory panels | Separates scope from action so the reader can scan faster |
| Restrained editorial styling | Fits internal governance content better than dashboard treatment |

## Pitfalls

- ❌ Putting the full policy body into the card → ✅ keep this to the announcement and action summary
- ❌ Using many equal-weight panels → ✅ policy memos need a clear top-down reading order
- ❌ Hiding required action in prose only → ✅ the action should be a first-class panel

## Alternatives

| Variant | Use instead |
|---|---|
| Audit status summary | `compliance-audit-card.md` |
| Narrative executive change brief | `executive-brief-summary.md` |
| Full searchable policy text | Regular Markdown prose or a linked document |

<!-- source: HTML/CSS inventory notes + infocard policy-paper/policy-memo patterns -->