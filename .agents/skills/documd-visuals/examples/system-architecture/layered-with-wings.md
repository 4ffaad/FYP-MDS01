# Layered With Wings (HTML/CSS)

**Best for**: the default architecture figure — a layered core in the middle, with the things that serve
*every* layer in a column down each side. This is the most-used shape in the set, and the one to reach for
when nothing more specific is called for
**Avoid when**: the wings are not really system-wide → use `operations-overview.md` (one wing) or
`layer-stack.md` (no wings); a wing that only applies to one layer is a component of that layer, not a wing
**Answers**: what the layers are, what runs in each of them, and which systems wrap around all of them

<div style="max-width: 1140px; box-sizing: border-box; position: relative;">
  <style scoped>
    .arch-lw { background: #f8fafc; padding: 26px; font-family: 'Segoe UI', sans-serif; color: #1f2937; }
    .arch-lw-title { margin: 0 0 6px; text-align: center; font-size: 27px; font-weight: 700; }
    .arch-lw-sub { margin: 0 0 18px; text-align: center; font-size: 13px; color: #676f7e; }
    .arch-lw-body { display: grid; grid-template-columns: 208px 1fr 208px; gap: 12px; align-items: stretch; }
    .arch-lw-wing { display: flex; flex-direction: column; padding: 12px; border-radius: 6px; background: #dfe5fb; border: 2px solid #334155; }
    .arch-lw-wing-head { font-size: 11px; font-weight: 700; letter-spacing: 0.13em; text-transform: uppercase; text-align: center; padding-bottom: 8px; margin-bottom: 10px; border-bottom: 1px solid #5b6b8c; }
    .arch-lw-wing-items { display: grid; gap: 7px; flex: 1; align-content: start; }
    .arch-lw-wing-item { padding: 8px 9px; background: #ffffff; border: 1px solid #5b6b8c; border-radius: 3px; font-size: 12px; font-weight: 600; line-height: 1.25; text-align: center; }
    .arch-lw-wing-item small { display: block; font-size: 9px; font-weight: 400; color: #676f7e; margin-top: 2px; }
    .arch-lw-wing-foot { margin-top: 10px; padding-top: 8px; border-top: 1px solid #5b6b8c; font-size: 10px; color: #676f7e; text-align: center; line-height: 1.3; }
    .arch-lw-core { display: grid; gap: 8px; align-content: stretch; }
    .arch-lw-layer { padding: 10px 12px; border-radius: 5px; border: 1px solid #5b6b8c; }
    .arch-lw-layer.exp { background: #d9e3f4; }
    .arch-lw-layer.svc { background: #d4eded; }
    .arch-lw-layer.async { background: #e5defb; }
    .arch-lw-layer.data { background: #daeedd; }
    .arch-lw-layer.infra { background: #e7e1dc; }
    .arch-lw-layer-head { display: flex; align-items: baseline; gap: 8px; margin-bottom: 8px; }
    .arch-lw-layer-name { font-size: 11px; font-weight: 700; letter-spacing: 0.11em; text-transform: uppercase; }
    .arch-lw-layer-note { font-size: 10px; color: #676f7e; }
    .arch-lw-items { display: grid; gap: 6px; }
    .arch-lw-items.c3 { grid-template-columns: repeat(3, 1fr); }
    .arch-lw-items.c4 { grid-template-columns: repeat(4, 1fr); }
    .arch-lw-box { padding: 7px 8px; background: #ffffff; border: 1px solid #5b6b8c; border-radius: 3px; font-size: 11px; font-weight: 600; line-height: 1.25; text-align: center; }
    .arch-lw-box small { display: block; font-size: 9px; font-weight: 400; color: #676f7e; margin-top: 2px; }
    .arch-lw-box.entry { background: #ffffff; border: 2px solid #265aac; }
    .arch-lw-spans { margin-top: 12px; display: flex; align-items: center; gap: 10px; justify-content: center; font-size: 11px; color: #676f7e; }
    .arch-lw-spans i { display: block; flex: 0 0 90px; height: 0; border-top: 2px solid #334155; }
    .arch-lw-spans i.r { border-top-style: solid; }
  </style>
  <section class="arch-lw">
    <h1 class="arch-lw-title">Platform Architecture</h1>
    <p class="arch-lw-sub">five layers in the middle; the two columns apply to all five, which is why they span the full height</p>
    <div class="arch-lw-body">
      <aside class="arch-lw-wing">
        <div class="arch-lw-wing-head">Supporting<br>systems</div>
        <div class="arch-lw-wing-items">
          <div class="arch-lw-wing-item">Observability<small>metrics, logs, traces</small></div>
          <div class="arch-lw-wing-item">CI / CD<small>build, test, deploy</small></div>
          <div class="arch-lw-wing-item">Incident tooling<small>paging, runbooks</small></div>
          <div class="arch-lw-wing-item">Analytics<small>product and cost</small></div>
          <div class="arch-lw-wing-item">Feature flags<small>release control</small></div>
        </div>
        <div class="arch-lw-wing-foot">Owned by the platform team.<br>Nothing here is on the request path.</div>
      </aside>
      <div class="arch-lw-core">
        <div class="arch-lw-layer exp">
          <div class="arch-lw-layer-head"><span class="arch-lw-layer-name">Experience</span><span class="arch-lw-layer-note">what the customer touches</span></div>
          <div class="arch-lw-items c3">
            <div class="arch-lw-box">Web app</div>
            <div class="arch-lw-box">Mobile app</div>
            <div class="arch-lw-box">Partner portal</div>
          </div>
        </div>
        <div class="arch-lw-layer svc">
          <div class="arch-lw-layer-head"><span class="arch-lw-layer-name">Services</span><span class="arch-lw-layer-note">synchronous, request-scoped</span></div>
          <div class="arch-lw-items c4">
            <div class="arch-lw-box entry">API gateway<small>auth, routing</small></div>
            <div class="arch-lw-box">Orders</div>
            <div class="arch-lw-box">Payments</div>
            <div class="arch-lw-box">Identity</div>
          </div>
        </div>
        <div class="arch-lw-layer async">
          <div class="arch-lw-layer-head"><span class="arch-lw-layer-name">Async</span><span class="arch-lw-layer-note">queued, retried, out of band</span></div>
          <div class="arch-lw-items c3">
            <div class="arch-lw-box">Event bus</div>
            <div class="arch-lw-box">Workers</div>
            <div class="arch-lw-box">Scheduler</div>
          </div>
        </div>
        <div class="arch-lw-layer data">
          <div class="arch-lw-layer-head"><span class="arch-lw-layer-name">Data</span><span class="arch-lw-layer-note">state that outlives a request</span></div>
          <div class="arch-lw-items c4">
            <div class="arch-lw-box">Primary DB</div>
            <div class="arch-lw-box">Cache</div>
            <div class="arch-lw-box">Object store</div>
            <div class="arch-lw-box">Warehouse</div>
          </div>
        </div>
        <div class="arch-lw-layer infra">
          <div class="arch-lw-layer-head"><span class="arch-lw-layer-name">Infrastructure</span><span class="arch-lw-layer-note">what everything else runs on</span></div>
          <div class="arch-lw-items c4">
            <div class="arch-lw-box">Kubernetes</div>
            <div class="arch-lw-box">Networking</div>
            <div class="arch-lw-box">Secrets</div>
            <div class="arch-lw-box">Terraform</div>
          </div>
        </div>
      </div>
      <aside class="arch-lw-wing">
        <div class="arch-lw-wing-head">Cross-cutting<br>concerns</div>
        <div class="arch-lw-wing-items">
          <div class="arch-lw-wing-item">Identity &amp; access<small>who may do what</small></div>
          <div class="arch-lw-wing-item">Security policy<small>boundaries, keys</small></div>
          <div class="arch-lw-wing-item">Compliance<small>evidence, retention</small></div>
          <div class="arch-lw-wing-item">Cost governance<small>budgets, tagging</small></div>
          <div class="arch-lw-wing-item">Data classification<small>what may be stored</small></div>
        </div>
        <div class="arch-lw-wing-foot">Owned by security and finance.<br>Applied at every layer, enforced at the gateway.</div>
      </aside>
    </div>
    <div class="arch-lw-spans"><i></i><span>the wings span all five layers — they are not peers of the layers</span><i class="r"></i></div>
  </section>
</div>

## Data Shape

A three-column grid: wing, core, wing. The **core is a stack of layer bands**; each **wing is a single
panel that stretches to the core's full height**, because that stretch is the whole message — a concern
that spans every layer is drawn spanning every layer.

Layer names run top to bottom in dependency order: experience depends on services, services on async and
data, everything on infrastructure. The reader should be able to read one wing and get "this applies
throughout".

## Key Options

| Option | Effect |
|---|---|
| `align-items: stretch` on the three-column grid | The wings take the core's height for free; any other value and they float, which reads as "this applies to one layer" |
| A tint per layer band | Five layers need five distinguishable fills; the ramp exists for exactly this, and the tint keeps the band light enough for `ink` text |
| A `2px` border on the wings vs `1px` on the bands | The wings are a different *kind* of thing, and line weight says so without a legend |
| A footer line inside each wing | Says who owns it and whether it is on the request path — the two questions a wing always raises |
| A caption under the grid | Names the relationship explicitly; a reader who misses the full-height cue still gets it |
| A heavier border on the one entry point | Marks where traffic enters, which is usually the figure's real subject |

## Pitfalls

- ❌ Wings that only apply to one layer → ✅ that is a component of that layer; put it in the band, or the
  full-height stretch becomes a lie
- ❌ Letting the wings float to their content height → ✅ `align-items: stretch`, or the figure says the
  opposite of what it means
- ❌ More than six layers → ✅ the bands become unreadable and the wings stretch into thin strips; group
  layers or split the figure
- ❌ Putting supporting systems *inside* the infrastructure band → ✅ infrastructure is what the stack runs
  on, support systems are what runs alongside it; merging them is the most common mistake in this figure
- ❌ A different hue per component → ✅ hue encodes the layer, not the component; components inside a band
  are all `surface-1`
- ❌ Drawing the wings as arrows into the stack → ✅ a wing is a scope, not a call; arrows belong in
  `request-paths.md`

## Alternatives

| Variant | Use instead |
|---|---|
| One wing rather than two | `operations-overview.md` |
| No wings — the layers alone | `layer-stack.md` |
| The layers plus who calls whom | `request-paths.md` |
| The same layers placed across regions and zones | `nested-zones.md` |
| Six layers with every component named, and wings grouped by function | `complex-system-blueprint.md` |

<!-- source: recovered from the architecture skill's layouts/three-column.md + layer-layouts.md — the layered core with two full-height wings -->
