# Complex System Blueprint (HTML/CSS)

**Best for**: a whole system that is too large for one component per layer — six bands with every
component named, and wings that group the concerns serving all of them into labelled functions. Use it
when the reader has to *place* a component rather than just see the shape
**Avoid when**: five bands and a flat wing list will do → use `layered-with-wings.md`; the extra density
costs legibility and has to buy something
**Answers**: what the layers are, what specifically runs in each one, and which groups of concerns wrap
around all of them

<div style="max-width: 1140px; box-sizing: border-box; position: relative;">
  <style scoped>
    .arch-cs { background: #f8fafc; padding: 26px; color: #1f2937; }
    .arch-cs-title { margin: 0 0 6px; text-align: center; font-size: 27px; font-weight: 700; }
    .arch-cs-sub { margin: 0 0 18px; text-align: center; font-size: 13px; color: #676f7e; }
    .arch-cs-body { display: grid; grid-template-columns: 212px 1fr 212px; gap: 12px; align-items: stretch; }
    .arch-cs-wing { display: flex; flex-direction: column; gap: 9px; padding: 12px; border-radius: 6px; background: #dfe5fb; border: 2px solid #334155; }
    .arch-cs-wing-head { font-size: 11px; font-weight: 700; letter-spacing: 0.13em; text-transform: uppercase; text-align: center; padding-bottom: 8px; border-bottom: 1px solid #5b6b8c; }
    .arch-cs-group { padding: 8px; background: #f8fafc; border: 1px solid #5b6b8c; border-radius: 4px; }
    .arch-cs-group-title { font-size: 11px; font-weight: 700; text-align: center; margin-bottom: 6px; }
    .arch-cs-group-items { display: grid; gap: 4px; }
    .arch-cs-group-item { padding: 4px 5px; background: #eef2fb; border: 1px solid #5b6b8c; border-radius: 3px; font-size: 10px; line-height: 1.25; text-align: center; }
    .arch-cs-core { display: grid; gap: 8px; align-content: stretch; }
    .arch-cs-layer { padding: 9px 11px; border-radius: 5px; border: 1px solid #5b6b8c; }
    .arch-cs-layer.channels { background: #d9e3f4; }
    .arch-cs-layer.edge { background: #fdeedc; }
    .arch-cs-layer.services { background: #d4eded; }
    .arch-cs-layer.async { background: #e5defb; }
    .arch-cs-layer.data { background: #daeedd; }
    .arch-cs-layer.platform { background: #e7e1dc; }
    .arch-cs-layer-head { display: flex; align-items: baseline; gap: 8px; margin-bottom: 7px; }
    .arch-cs-layer-name { font-size: 11px; font-weight: 700; letter-spacing: 0.11em; text-transform: uppercase; }
    .arch-cs-layer-note { font-size: 10px; }
    .arch-cs-items { display: grid; gap: 5px; }
    .arch-cs-items.c4 { grid-template-columns: repeat(4, 1fr); }
    .arch-cs-items.c5 { grid-template-columns: repeat(5, 1fr); }
    .arch-cs-box { padding: 6px 7px; background: #f8fafc; border: 1px solid #5b6b8c; border-radius: 3px; font-size: 10px; font-weight: 600; line-height: 1.25; text-align: center; }
    .arch-cs-box small { display: block; font-size: 9px; font-weight: 400; margin-top: 2px; }
    .arch-cs-box.entry { border: 2px solid #265aac; }
    .arch-cs-foot { margin: 12px 0 0; padding-top: 9px; border-top: 1px solid #5b6b8c; font-size: 11px; color: #676f7e; text-align: center; line-height: 1.4; }
  </style>
  <section class="arch-cs">
    <h1 class="arch-cs-title">Payments Platform Architecture</h1>
    <p class="arch-cs-sub">six layers, every component named — the two wings group the concerns that apply to all six</p>
    <div class="arch-cs-body">
      <aside class="arch-cs-wing">
        <div class="arch-cs-wing-head">Supporting<br>systems</div>
        <div class="arch-cs-group"><div class="arch-cs-group-title">Observability</div><div class="arch-cs-group-items"><div class="arch-cs-group-item">Metrics</div><div class="arch-cs-group-item">Logs</div><div class="arch-cs-group-item">Traces</div><div class="arch-cs-group-item">Alerting</div></div></div>
        <div class="arch-cs-group"><div class="arch-cs-group-title">Delivery</div><div class="arch-cs-group-items"><div class="arch-cs-group-item">Build &amp; test</div><div class="arch-cs-group-item">Release pipeline</div><div class="arch-cs-group-item">Configuration</div><div class="arch-cs-group-item">Feature flags</div></div></div>
        <div class="arch-cs-group"><div class="arch-cs-group-title">Operations</div><div class="arch-cs-group-items"><div class="arch-cs-group-item">On-call</div><div class="arch-cs-group-item">Runbooks</div><div class="arch-cs-group-item">Incident review</div><div class="arch-cs-group-item">Capacity</div></div></div>
      </aside>
      <div class="arch-cs-core">
        <div class="arch-cs-layer channels">
          <div class="arch-cs-layer-head"><span class="arch-cs-layer-name">Channels</span><span class="arch-cs-layer-note">who starts a request</span></div>
          <div class="arch-cs-items c4"><div class="arch-cs-box">Web app<small>browser client</small></div><div class="arch-cs-box">Mobile app<small>iOS, Android</small></div><div class="arch-cs-box">Partner API<small>server to server</small></div><div class="arch-cs-box">Operator console<small>internal staff</small></div></div>
        </div>
        <div class="arch-cs-layer edge">
          <div class="arch-cs-layer-head"><span class="arch-cs-layer-name">Edge</span><span class="arch-cs-layer-note">every request enters here</span></div>
          <div class="arch-cs-items c4"><div class="arch-cs-box">CDN<small>static, cached</small></div><div class="arch-cs-box">WAF<small>rate, rules</small></div><div class="arch-cs-box entry">API gateway<small>auth, routing</small></div><div class="arch-cs-box">BFF<small>per-channel shaping</small></div></div>
        </div>
        <div class="arch-cs-layer services">
          <div class="arch-cs-layer-head"><span class="arch-cs-layer-name">Domain services</span><span class="arch-cs-layer-note">synchronous, request-scoped</span></div>
          <div class="arch-cs-items c5"><div class="arch-cs-box">Accounts<small>identity, profile</small></div><div class="arch-cs-box">Payments<small>authorise, capture</small></div><div class="arch-cs-box">Ledger<small>double entry</small></div><div class="arch-cs-box">Notifications<small>email, push</small></div><div class="arch-cs-box">Reporting<small>queries, exports</small></div></div>
        </div>
        <div class="arch-cs-layer async">
          <div class="arch-cs-layer-head"><span class="arch-cs-layer-name">Integration &amp; async</span><span class="arch-cs-layer-note">queued, retried, out of band</span></div>
          <div class="arch-cs-items c4"><div class="arch-cs-box">Event bus<small>publish, subscribe</small></div><div class="arch-cs-box">Workers<small>retries, dead letters</small></div><div class="arch-cs-box">Scheduler<small>periodic jobs</small></div><div class="arch-cs-box">Connectors<small>partner and vendor APIs</small></div></div>
        </div>
        <div class="arch-cs-layer data">
          <div class="arch-cs-layer-head"><span class="arch-cs-layer-name">Data</span><span class="arch-cs-layer-note">state that outlives a request</span></div>
          <div class="arch-cs-items c5"><div class="arch-cs-box">Primary store<small>transactional</small></div><div class="arch-cs-box">Cache<small>hot reads</small></div><div class="arch-cs-box">Search index<small>query, facets</small></div><div class="arch-cs-box">Object store<small>documents, media</small></div><div class="arch-cs-box">Warehouse<small>analytics, history</small></div></div>
        </div>
        <div class="arch-cs-layer platform">
          <div class="arch-cs-layer-head"><span class="arch-cs-layer-name">Platform</span><span class="arch-cs-layer-note">what everything else runs on</span></div>
          <div class="arch-cs-items c5"><div class="arch-cs-box">Runtime<small>containers, scheduling</small></div><div class="arch-cs-box">Networking<small>ingress, service mesh</small></div><div class="arch-cs-box">Secrets<small>keys, rotation</small></div><div class="arch-cs-box">Provisioning<small>infrastructure as code</small></div><div class="arch-cs-box">Registry<small>images, artefacts</small></div></div>
        </div>
      </div>
      <aside class="arch-cs-wing">
        <div class="arch-cs-wing-head">Cross-cutting<br>concerns</div>
        <div class="arch-cs-group"><div class="arch-cs-group-title">Identity &amp; access</div><div class="arch-cs-group-items"><div class="arch-cs-group-item">Authentication</div><div class="arch-cs-group-item">Authorization</div><div class="arch-cs-group-item">Key management</div><div class="arch-cs-group-item">Audit trail</div></div></div>
        <div class="arch-cs-group"><div class="arch-cs-group-title">Data governance</div><div class="arch-cs-group-items"><div class="arch-cs-group-item">Classification</div><div class="arch-cs-group-item">Retention</div><div class="arch-cs-group-item">Residency</div><div class="arch-cs-group-item">Evidence</div></div></div>
        <div class="arch-cs-group"><div class="arch-cs-group-title">Resilience</div><div class="arch-cs-group-items"><div class="arch-cs-group-item">Backup</div><div class="arch-cs-group-item">Disaster recovery</div><div class="arch-cs-group-item">Failover</div><div class="arch-cs-group-item">Rate limiting</div></div></div>
      </aside>
    </div>
    <p class="arch-cs-foot">The wings span all six layers — supporting systems run beside the stack, cross-cutting concerns are enforced inside it, at the gateway.</p>
  </section>
</div>

## Data Shape

A three-column grid — wing, core, wing. The **core is six layer bands**, each a grid of named components
with the job that component does underneath. Each **wing is a stack of group panels**, so a wing reads as
several labelled functions rather than one long list; both wings stretch to the core's height, because
that stretch is the message — a concern that spans every layer is drawn spanning every layer.

Six bands is the ceiling. At five components a band's boxes are already about 120 px wide; a seventh band
pushes each one under a readable width. Layer order runs top to bottom in dependency order: channels call
the edge, the edge calls services, services reach async and data, and all of them run on platform.

## Key Options

| Option | Effect |
|---|---|
| `212px` wings rather than a single-panel wing's `208px` | A grouped wing carries group headings *and* items; the extra width keeps four items per group on one line |
| Group panels inside the wing | Turns one list into labelled functions — the difference between "what supports the stack" and "who does what" |
| A sub-label on every component | Names the job, which is what lets a dense band be read without a legend |
| `align-items: stretch` on the three-column grid | The wings take the core's height for free; any other value and they float, which reads as "this applies to one layer" |
| A tint per layer band | Six bands need six distinguishable fills; the ramp exists for this and keeps every band light enough for `ink` |
| `ink` rather than `muted` inside a band | The tint already lowers contrast, and the palette contract allows `muted` only on the page |
| A `2px` border on the wings vs `1px` on the bands | The wings are a different *kind* of thing, and line weight says so without a legend |
| A heavier border on the one entry box | Marks where traffic enters, which is usually the figure's real subject |

## Pitfalls

- ❌ Reaching for this when five bands and a flat wing list will do → ✅ `layered-with-wings.md`; the extra
  density costs legibility and has to buy something
- ❌ Sub-labels that restate the component name → ✅ the sub-label says what the component *does*
  (`Ledger` / `double entry`, not `Ledger` / `the ledger`)
- ❌ A sixth component in a band → ✅ five columns is the ceiling; a sixth box wraps or squeezes the row
  under 110 px
- ❌ A seventh layer band → ✅ group the layers or split the figure; the bands stop being readable
- ❌ A wing group that applies to one layer only → ✅ that is a component of the layer, not a wing
- ❌ Letting the wings float to their own content height → ✅ `align-items: stretch`, or the figure says
  the opposite of what it means
- ❌ A different hue per component → ✅ hue encodes the layer; every component inside a band is `surface-0`
- ❌ `muted` or `ink-soft` text inside a tinted band → ✅ `ink`; both are page-only tokens in the contract

## Alternatives

| Variant | Use instead |
|---|---|
| Five layers, one panel per wing | `layered-with-wings.md` |
| No wings — the layers alone | `layer-stack.md` |
| One rail rather than two | `operations-overview.md` |
| The layers plus who calls whom | `request-paths.md` |
| Equal-weight inventory with no layers | `service-catalog.md` |
| The same system placed across regions and zones | `nested-zones.md` |

<!-- source: recovered from the architecture skill's styles/frost-clean.md — grouped multi-panel wings around a six-band core, for systems too large for one component per layer -->
