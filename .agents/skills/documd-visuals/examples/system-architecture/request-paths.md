# Connector Overlay (HTML/CSS)

**Best for**: showing how components actually reach each other — sync calls, async events, and the one
dependency that is only allowed to go one way
**Avoid when**: containment is the point and nothing calls anything → `nested-zones.md` already encodes
reachability by nesting, and arrows on top of it would be a second, contradicting diagram
**Answers**: which component talks to which, in which direction, and where the fan-in is

<div style="max-width: 1080px; box-sizing: border-box; position: relative;">
  <style scoped>
    .arch-conn-doc { background: #f8fafc; padding: 24px; font-family: 'Segoe UI', sans-serif; color: #1f2937; }
    .arch-conn-title { margin: 0 0 6px; text-align: center; font-size: 25px; font-weight: 700; }
    .arch-conn-sub { margin: 0 0 16px; text-align: center; font-size: 12px; color: #676f7e; }
    .arch-canvas { position: relative; width: 1000px; height: 436px; margin: 0 auto; }
    .arch-band { position: absolute; left: 20px; width: 960px; height: 88px; border-radius: 6px; background: #eef2fb; border: 1px solid #5b6b8c; }
    .arch-band.b1 { top: 8px; }
    .arch-band.b2 { top: 168px; }
    .arch-band.b3 { top: 328px; background: #dfe5fb; border-color: #265aac; }
    .arch-band-label { position: absolute; left: 12px; top: 8px; font-size: 10px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #676f7e; }
    .arch-node-abs { position: absolute; height: 44px; padding: 6px 10px; box-sizing: border-box; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; line-height: 1.2; background: #ffffff; border: 1px solid #5b6b8c; border-radius: 4px; text-align: center; }
    .arch-node-abs small { font-size: 9px; font-weight: 400; color: #676f7e; }
    .arch-node-abs.entry { background: #d9e3f4; border-color: #265aac; }
    .arch-node-abs.external { border-style: dashed; color: #676f7e; }
    .arch-overlay { position: absolute; top: 0; left: 0; width: 1000px; height: 436px; pointer-events: none; }
    .arch-link { stroke: #5b6b8c; stroke-width: 1.5; fill: none; }
    .arch-link-dashed { stroke: #5b6b8c; stroke-width: 1.5; fill: none; stroke-dasharray: 6 4; }
    .arch-link-label { font-size: 9px; fill: #676f7e; font-family: sans-serif; }
    .arch-conn-legend { margin: 10px auto 0; display: flex; gap: 18px; justify-content: center; font-size: 11px; color: #676f7e; }
    .arch-conn-legend span { display: inline-flex; align-items: center; gap: 6px; }
    .arch-conn-legend i { display: inline-block; width: 26px; height: 0; border-top: 2px solid #5b6b8c; }
    .arch-conn-legend i.dash { border-top-style: dashed; }
  </style>
  <section class="arch-conn-doc">
    <h1 class="arch-conn-title">Request Paths</h1>
    <p class="arch-conn-sub">orthogonal connectors only — every line is horizontal or vertical, no diagonals</p>
    <div class="arch-canvas">
      <div class="arch-band b1"><span class="arch-band-label">Clients</span></div>
      <div class="arch-band b2"><span class="arch-band-label">Services</span></div>
      <div class="arch-band b3"><span class="arch-band-label">State</span></div>
      <div class="arch-node-abs" style="left: 40px; top: 40px; width: 240px;">Web app<small>browser</small></div>
      <div class="arch-node-abs entry" style="left: 380px; top: 40px; width: 240px;">API gateway<small>auth + routing</small></div>
      <div class="arch-node-abs external" style="left: 720px; top: 40px; width: 240px;">Partner API<small>third party</small></div>
      <div class="arch-node-abs" style="left: 40px; top: 200px; width: 240px;">Orders<small>core service</small></div>
      <div class="arch-node-abs" style="left: 380px; top: 200px; width: 240px;">Payments<small>core service</small></div>
      <div class="arch-node-abs entry" style="left: 720px; top: 200px; width: 240px;">Reporting<small>read-only</small></div>
      <div class="arch-node-abs" style="left: 140px; top: 360px; width: 280px;">Primary database<small>PostgreSQL</small></div>
      <div class="arch-node-abs" style="left: 580px; top: 360px; width: 280px;">Event log<small>append-only</small></div>
      <svg class="arch-overlay" viewBox="0 0 1000 436">
        <defs>
          <marker id="arch-arrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6" fill="none" stroke="#5b6b8c" stroke-width="1"/></marker>
          <marker id="arch-arrow-open" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6" fill="none" stroke="#6b7280" stroke-width="1"/></marker>
        </defs>
        <path class="arch-link" d="M 160,84 L 160,200" marker-end="url(#arch-arrow)"/>
        <path class="arch-link" d="M 500,84 L 500,140 L 840,140 L 840,200" marker-end="url(#arch-arrow)"/>
        <path class="arch-link-dashed" d="M 840,84 L 840,120 L 500,120 L 500,200" marker-end="url(#arch-arrow-open)"/>
        <path class="arch-link" d="M 160,244 L 160,302 L 280,302 L 280,360" marker-end="url(#arch-arrow)"/>
        <path class="arch-link-dashed" d="M 500,244 L 500,326 L 720,326 L 720,360" marker-end="url(#arch-arrow-open)"/>
        <path class="arch-link" d="M 840,244 L 840,302 L 720,302 L 720,360" marker-end="url(#arch-arrow)"/>
        <text class="arch-link-label" x="166" y="150">https</text>
        <text class="arch-link-label" x="508" y="134">oauth token</text>
        <text class="arch-link-label" x="620" y="114">webhook (inbound)</text>
        <text class="arch-link-label" x="166" y="296">read / write</text>
        <text class="arch-link-label" x="508" y="320">publish</text>
        <text class="arch-link-label" x="760" y="296">read only</text>
      </svg>
    </div>
    <div class="arch-conn-legend"><span><i></i>sync call</span><span><i class="dash"></i>async / event</span></div>
  </section>
</div>

## Data Shape

Components are absolutely positioned at known coordinates inside a `position: relative` canvas, and one
absolutely positioned `<svg>` sits over them with `pointer-events: none`. Each component gets an `id`, and
each connector is a `<path>` whose `d` is a chain of `M` and `L` between those components' edges.

**The one rule that matters**: connectors are orthogonal — strictly horizontal and vertical segments, no
diagonals and no curves. `<line>`, Bézier `C`/`S`/`Q` commands and diagonal paths all look hand-drawn next
to right angles, and a diagram of right angles reads as a system rather than a sketch.

## Key Options

| Option | Effect |
|---|---|
| `viewBox="0 0 w h"` matching the canvas | The SVG scales with the figure instead of drifting out of alignment |
| `pointer-events: none` on the overlay | Links never intercept a selection or a link inside a box |
| Two markers, open and filled | Open reads as "eventually"; filled reads as "and it must succeed" |
| `stroke-dasharray` for async links | Line style is a second channel, so the diagram still reads in greyscale |
| Labels on the *horizontal* run of a path | Vertical runs are too narrow to hold text without colliding with the line |
| A legend strip under the canvas | Two line styles do not need to be decoded from context |

## Pitfalls

- ❌ Diagonal or curved connectors → ✅ right angles only; this is the single most recognisable tell of a
  hand-made HTML architecture diagram
- ❌ Omitting the canvas height → ✅ absolute children collapse the parent, the SVG ends up zero-height, and
  every connector disappears while the boxes still look fine
- ❌ Forgetting `pointer-events: none` → ✅ the overlay silently swallows clicks over the whole figure
- ❌ Connector labels placed on a vertical run → ✅ put them on the horizontal run, and offset the path's
  mid-segment so two links do not share it
- ❌ Drawing both containment bands and a full set of arrows → ✅ pick one; nesting already means reachability
- ❌ More than about eight connectors → ✅ at that density the crossings carry more information than the
  links do; split the figure

## Alternatives

| Variant | Use instead |
|---|---|
| Containment rather than calls | `nested-zones.md` |
| Stage order rather than pairwise calls | `pipeline-stages.md` |
| Dependencies a diagram engine can lay out for you | PlantUML examples in `dependencies-and-relations` |

<!-- source: recovered from the architecture skill's layouts/connectors.md — absolutely-positioned SVG overlay, orthogonal M/L paths, two arrow markers -->
