# Sidebar Architecture Overview (HTML/CSS)

**Best for**: a system overview where one contextual or support column should stay visually separate from the main architecture stack
**Avoid when**: the page needs many equal-weight columns or explicit edge routing between many nodes
**Answers**: what the core architecture is, and what supporting systems or governance context sits beside it

<div style="max-width: 980px; box-sizing: border-box; position: relative;">
  <style scoped>
    .arch-sidebar { background: #f8fafc;  padding: 26px; font-family: 'Segoe UI', sans-serif; }
    .arch-sidebar-title { margin: 0 0 16px; font-size: 28px; font-weight: 700; }
    .arch-sidebar-grid { display: grid; grid-template-columns: 0.85fr 1.4fr; gap: 14px; }
    .arch-sidebar-side { padding: 16px; background: #eef2fb; }
    .arch-sidebar-main { padding: 16px; background: #eef2fb; }
    .arch-sidebar-head { margin: 0 0 10px; font-size: 12px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; }
    .arch-sidebar-stack { display: grid; gap: 8px; }
    .arch-sidebar-box { padding: 10px 12px; background: rgba(255,255,255,0.82); border: 1px solid rgba(15,23,42,0.12); font-size: 13px; line-height: 1.35; text-align: center; }
  </style>
  <section class="arch-sidebar">
    <h1 class="arch-sidebar-title">Sidebar Architecture Overview</h1>
    <div class="arch-sidebar-grid">
      <aside class="arch-sidebar-side">
        <p class="arch-sidebar-head">Support Context</p>
        <div class="arch-sidebar-stack">
          <div class="arch-sidebar-box">Observability</div>
          <div class="arch-sidebar-box">Analytics</div>
          <div class="arch-sidebar-box">Runbooks</div>
          <div class="arch-sidebar-box">Security Review</div>
        </div>
      </aside>
      <main class="arch-sidebar-main">
        <p class="arch-sidebar-head">Core Stack</p>
        <div class="arch-sidebar-stack">
          <div class="arch-sidebar-box">Experience Layer</div>
          <div class="arch-sidebar-box">Gateway / API Layer</div>
          <div class="arch-sidebar-box">Workflow & Service Layer</div>
          <div class="arch-sidebar-box">Data & Storage Layer</div>
          <div class="arch-sidebar-box">Platform & Infrastructure Layer</div>
        </div>
      </main>
    </div>
  </section>
</div>

## Data Shape

Use one narrow sidebar for context/support topics and one wide main column for the core stack or core narrative.

## Key Options

| Option | Effect |
|---|---|
| Unequal two-column split | Keeps the main architecture central while preserving support context |
| Stacked boxes per column | Makes both the sidebar and the main column easy to scan |
| Distinct background families | Signals role separation between support context and core architecture |

## Pitfalls

- ❌ Treating the sidebar as a second main column → ✅ the sidebar should stay auxiliary, not equal-weight
- ❌ Overloading the main stack with every subsystem name → ✅ keep the architecture at the layer/domain level
- ❌ Using this for dense network routing | ✅ move to diagram engines when edge topology becomes important

## Alternatives

| Variant | Use instead |
|---|---|
| Fully stacked vertical architecture | `layer-stack.md` |
| The layered core with both wings | `layered-with-wings.md` |
| One-page memo with architecture context | `executive-brief-summary.md` |

<!-- source: HTML/CSS inventory notes + architecture left/right-sidebar patterns -->