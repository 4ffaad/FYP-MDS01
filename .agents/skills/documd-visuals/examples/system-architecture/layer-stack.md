# Stacked Platform Overview (HTML/CSS)

**Best for**: a layered system overview where the reader needs to see the stack from experience layer down to infrastructure
**Avoid when**: the reader needs exact connection routing or deep node-level topology
**Answers**: what layers exist, what belongs in each layer, and how the platform is conceptually organised

<div style="max-width: 980px; box-sizing: border-box; position: relative;">
  <style scoped>
    .arch-overview { background: #f8fafc;  padding: 28px; font-family: 'Segoe UI', sans-serif; }
    .arch-overview-title { margin: 0 0 18px; text-align: center; font-size: 28px; font-weight: 700; }
    .arch-overview-layer { margin: 10px 0; padding: 16px 18px; border-radius: 6px; }
    .arch-overview-layer-title { margin: 0 0 10px; font-size: 12px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; }
    .arch-overview-grid { display: grid; gap: 8px; }
    .arch-overview-grid.cols-3 { grid-template-columns: repeat(3, 1fr); }
    .arch-overview-grid.cols-4 { grid-template-columns: repeat(4, 1fr); }
    .arch-overview-box { padding: 10px 12px; background: rgba(255,255,255,0.72); border: 1px solid rgba(15,23,42,0.12); text-align: center; font-size: 13px; line-height: 1.35; }
    .layer-experience { background: #eef2fb; }
    .layer-service { background: #eef2fb; }
    .layer-data { background: #eef2fb; }
    .layer-platform { background: #eef2fb; }
  </style>
  <section class="arch-overview">
    <h1 class="arch-overview-title">Platform Overview</h1>
    <div class="arch-overview-layer layer-experience">
      <p class="arch-overview-layer-title">Experience Layer</p>
      <div class="arch-overview-grid cols-4">
        <div class="arch-overview-box">Web App</div>
        <div class="arch-overview-box">Mobile App</div>
        <div class="arch-overview-box">Partner Portal</div>
        <div class="arch-overview-box">Admin Console</div>
      </div>
    </div>
    <div class="arch-overview-layer layer-service">
      <p class="arch-overview-layer-title">Service Layer</p>
      <div class="arch-overview-grid cols-4">
        <div class="arch-overview-box">Gateway</div>
        <div class="arch-overview-box">Identity</div>
        <div class="arch-overview-box">Orders</div>
        <div class="arch-overview-box">Billing</div>
      </div>
    </div>
    <div class="arch-overview-layer layer-data">
      <p class="arch-overview-layer-title">Data Layer</p>
      <div class="arch-overview-grid cols-3">
        <div class="arch-overview-box">PostgreSQL</div>
        <div class="arch-overview-box">Redis</div>
        <div class="arch-overview-box">Object Storage</div>
      </div>
    </div>
    <div class="arch-overview-layer layer-platform">
      <p class="arch-overview-layer-title">Platform Layer</p>
      <div class="arch-overview-grid cols-4">
        <div class="arch-overview-box">Kubernetes</div>
        <div class="arch-overview-box">Observability</div>
        <div class="arch-overview-box">CI/CD</div>
        <div class="arch-overview-box">Policy & Security</div>
      </div>
    </div>
  </section>
</div>

## Data Shape

Use one named layer per semantic band, and only a handful of boxes inside each. This pattern is about conceptual stacking, not detailed routing.

## Key Options

| Option | Effect |
|---|---|
| Full-width vertical layers | Makes the architectural stack legible at a glance |
| Color-coded semantic bands | Turns layer color into meaning instead of decoration |
| Small boxed cells | Gives each layer a consistent rhythm without needing icons |

## Pitfalls

- ❌ Treating layers like a network diagram → ✅ this is a stack, not a routing map
- ❌ Putting every subsystem in one layer → ✅ each layer should stay selective enough to scan quickly
- ❌ No semantic distinction between layers → ✅ layer titles and color families are part of the message

## Alternatives

| Variant | Use instead |
|---|---|
| Need explicit connection flow | PlantUML or graph examples |
| Need a governance column beside the core | `operations-overview.md` or `layered-with-wings.md` |
| Need one-page executive context | `executive-brief-summary.md` |

<!-- source: HTML/CSS inventory notes + architecture single-stack pattern -->