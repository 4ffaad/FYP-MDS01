# Nested Zones (HTML/CSS)

**Best for**: a deployment where containment *is* the message — which instances sit in which zone, which zones make up a region, and what spans all of them
**Avoid when**: the reader needs call paths between services → use `request-paths.md`; or there is only one environment → a flat `layer-stack.md` reads faster
**Answers**: what runs where, what fails together when a zone fails, and what is deliberately outside every boundary

<div style="max-width: 1120px; box-sizing: border-box; position: relative;">
  <style scoped>
    .arch-zone-doc { background: #f8fafc; padding: 26px; font-family: 'Segoe UI', sans-serif; color: #1f2937; }
    .arch-zone-doc-title { margin: 0 0 6px; text-align: center; font-size: 26px; font-weight: 700; }
    .arch-zone-doc-sub { margin: 0 0 20px; text-align: center; font-size: 13px; color: #676f7e; }
    .arch-global { padding: 12px; border-radius: 6px; background: #dfe5fb; border: 1px solid #265aac; margin-bottom: 12px; }
    .arch-global-head { font-size: 11px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 8px; }
    .arch-global-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
    .arch-region { padding: 12px; border-radius: 6px; background: #eef2fb; border: 1px solid #5b6b8c; margin-bottom: 12px; }
    .arch-region-head { display: flex; align-items: baseline; gap: 8px; margin-bottom: 10px; }
    .arch-region-name { font-size: 12px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; }
    .arch-region-meta { font-size: 11px; color: #676f7e; }
    .arch-region-flag { margin-left: auto; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 10px; background: #daeedd; color: #1f7a33; }
    .arch-region-flag.dr { background: #fdeedc; color: #8a5a00; }
    .arch-zones { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
    .arch-zone { padding: 10px; border-radius: 4px; background: #ffffff; border: 1px dashed #5b6b8c; }
    .arch-zone-head { font-size: 10px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #676f7e; margin-bottom: 8px; text-align: center; }
    .arch-inst { display: grid; gap: 5px; }
    .arch-node { padding: 6px 8px; font-size: 11px; line-height: 1.25; background: #eef2fb; border: 1px solid #5b6b8c; border-radius: 3px; text-align: center; }
    .arch-node.primary { background: #d9e3f4; border-color: #265aac; font-weight: 600; }
    .arch-node small { display: block; font-size: 9px; color: #676f7e; font-weight: 400; }
    .arch-outside { padding: 12px; border-radius: 6px; background: #ffffff; border: 1px dashed #5b6b8c; }
    .arch-outside-head { font-size: 11px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #676f7e; margin-bottom: 8px; }
    .arch-outside-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
    .arch-chip { padding: 7px 9px; font-size: 11px; text-align: center; background: #f8fafc; border: 1px solid #5b6b8c; border-radius: 3px; }
    .arch-zone-doc-note { margin: 12px 0 0; font-size: 11px; color: #676f7e; text-align: center; }
  </style>
  <section class="arch-zone-doc">
    <h1 class="arch-zone-doc-title">Regional Deployment</h1>
    <p class="arch-zone-doc-sub">two regions, three zones each, one shared control plane outside both</p>
    <div class="arch-global">
      <div class="arch-global-head">Global — outside every region</div>
      <div class="arch-global-grid">
        <div class="arch-chip">DNS + traffic policy</div>
        <div class="arch-chip">Identity provider</div>
        <div class="arch-chip">Terraform state</div>
        <div class="arch-chip">Audit log sink</div>
      </div>
    </div>
    <div class="arch-region">
      <div class="arch-region-head"><span class="arch-region-name">Region eu-west</span><span class="arch-region-meta">primary · 3 zones</span><span class="arch-region-flag">active</span></div>
      <div class="arch-zones">
        <div class="arch-zone">
          <div class="arch-zone-head">Zone a</div>
          <div class="arch-inst"><div class="arch-node primary">API ×4<small>behind the LB</small></div><div class="arch-node">Worker ×2</div></div>
        </div>
        <div class="arch-zone">
          <div class="arch-zone-head">Zone b</div>
          <div class="arch-inst"><div class="arch-node primary">API ×4<small>behind the LB</small></div><div class="arch-node">Worker ×2</div></div>
        </div>
        <div class="arch-zone">
          <div class="arch-zone-head">Zone c</div>
          <div class="arch-inst"><div class="arch-node">API ×2<small>warm standby</small></div><div class="arch-node">Scheduler</div></div>
        </div>
      </div>
    </div>
    <div class="arch-region">
      <div class="arch-region-head"><span class="arch-region-name">Region us-east</span><span class="arch-region-meta">read replica · 3 zones</span><span class="arch-region-flag dr">failover</span></div>
      <div class="arch-zones">
        <div class="arch-zone">
          <div class="arch-zone-head">Zone a</div>
          <div class="arch-inst"><div class="arch-node">API ×2</div><div class="arch-node">Replica</div></div>
        </div>
        <div class="arch-zone">
          <div class="arch-zone-head">Zone b</div>
          <div class="arch-inst"><div class="arch-node">API ×2</div><div class="arch-node">Replica</div></div>
        </div>
        <div class="arch-zone">
          <div class="arch-zone-head">Zone c</div>
          <div class="arch-inst"><div class="arch-node">Analytics only</div></div>
        </div>
      </div>
    </div>
    <div class="arch-outside">
      <div class="arch-outside-head">Managed — no zone of ours</div>
      <div class="arch-outside-grid">
        <div class="arch-chip">Object storage</div>
        <div class="arch-chip">Managed queue</div>
        <div class="arch-chip">CDN</div>
        <div class="arch-chip">Third-party payments</div>
        <div class="arch-chip">Status page</div>
      </div>
    </div>
    <p class="arch-zone-doc-note">Solid border = our boundary. Dashed = something else owns it.</p>
  </section>
</div>

## Data Shape

A tree of three levels — global, region, zone — with the leaf boxes being what actually runs. The
nesting is the information: two instances in the same dashed box fail together, two in different boxes
do not.

## Key Options

| Option | Effect |
|---|---|
| `border-style` to separate boundaries from things inside them | Every level of containment is a real boundary; a solid border claims ownership, a dashed one disclaims it |
| A status chip in the region heading | Answers "is this the live one" without the reader counting instances |
| Instance counts in the leaf text (`API ×4`) | A topology diagram that does not say how many is a sketch |
| A separate band for managed services | The most common misreading of a deployment diagram is that everything shown is operated by the team |
| Three zones per region, drawn as a fixed grid | Zone symmetry is a design property worth showing; a ragged grid hides an unbalanced region |

## Pitfalls

- ❌ Nesting more than three levels → ✅ global/region/zone is already at the limit of what a page can show;
  the fourth level belongs in a table
- ❌ Putting managed services inside a zone → ✅ they are not in your failure domain, and drawing them there
  teaches the reader something false
- ❌ Using a different hue per region → ✅ regions differ by label and status, not by colour; hue is for
  categories, and these are not categories
- ❌ Omitting instance counts → ✅ the reader will ask, and a diagram that cannot answer sends them elsewhere
- ❌ Drawing this with connectors as well → ✅ containment already encodes reachability; arrows on top of
  nesting is two diagrams fighting

## Alternatives

| Variant | Use instead |
|---|---|
| Call paths between the services in these zones | `request-paths.md` |
| The layers alone, with no geography | `layer-stack.md` |
| The layers plus what wraps them, still no geography | `layered-with-wings.md` |

<!-- source: recovered from the architecture skill's layouts/nested-containers.md — region/zone nesting with dashed external boundaries -->
