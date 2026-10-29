# Pipeline Stages (HTML/CSS)

**Best for**: a left-to-right flow where each stage has its own components and the reader needs to see the order — ingest, transform, serve, and what fails where
**Avoid when**: the stages are really layers of one system → use `layer-stack.md`; or the relationships are many-to-many → use `request-paths.md`
**Answers**: what happens in what order, which stage owns which component, and where the flow can back up

<div style="max-width: 1120px; box-sizing: border-box; position: relative;">
  <style scoped>
    .arch-pipe { background: #f8fafc; padding: 26px; font-family: 'Segoe UI', sans-serif; color: #1f2937; }
    .arch-pipe-title { margin: 0 0 6px; text-align: center; font-size: 26px; font-weight: 700; }
    .arch-pipe-sub { margin: 0 0 20px; text-align: center; font-size: 13px; color: #676f7e; }
    .arch-pipe-io { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 14px; }
    .arch-pipe-source { padding: 9px 10px; text-align: center; font-size: 12px; font-weight: 600; background: #ffffff; border: 1px dashed #5b6b8c; border-radius: 4px; }
    .arch-pipe-row { display: flex; align-items: stretch; gap: 0; }
    .arch-pipe-stage { flex: 1; padding: 12px; border-radius: 6px; background: #eef2fb; border: 1px solid #5b6b8c; }
    .arch-pipe-stage.landing { background: #d9e3f4; border-color: #265aac; }
    .arch-pipe-stage.serve { background: #dfe5fb; border-color: #265aac; }
    .arch-pipe-num { display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; border-radius: 50%; background: #2b66c4; color: #ffffff; font-size: 11px; font-weight: 700; margin-right: 7px; }
    .arch-pipe-head { font-size: 11px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #1f2937; margin-bottom: 10px; }
    .arch-pipe-item { padding: 7px 9px; margin-bottom: 6px; background: #ffffff; border: 1px solid #5b6b8c; border-radius: 3px; font-size: 12px; line-height: 1.3; }
    .arch-pipe-item:last-child { margin-bottom: 0; }
    .arch-pipe-item small { display: block; font-size: 10px; color: #676f7e; margin-top: 2px; }
    .arch-pipe-item.dead { border-style: dashed; color: #676f7e; }
    .arch-pipe-arrow { display: flex; align-items: center; justify-content: center; width: 34px; flex-shrink: 0; font-size: 20px; color: #676f7e; }
    .arch-pipe-sla { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 14px; }
    .arch-pipe-kpi { padding: 10px; text-align: center; background: #ffffff; border: 1px solid #5b6b8c; border-radius: 4px; }
    .arch-pipe-kpi b { display: block; font-size: 19px; font-weight: 700; }
    .arch-pipe-kpi span { font-size: 10px; color: #676f7e; text-transform: uppercase; letter-spacing: 0.08em; }
    .arch-pipe-kpi.warn b { color: #8a5a00; }
    .arch-pipe-note { margin-top: 12px; font-size: 11px; color: #676f7e; text-align: center; }
  </style>
  <section class="arch-pipe">
    <h1 class="arch-pipe-title">Event Pipeline</h1>
    <p class="arch-pipe-sub">four stages, one direction, and the two places it is allowed to stop</p>
    <div class="arch-pipe-io">
      <div class="arch-pipe-source">Product events</div>
      <div class="arch-pipe-source">Billing events</div>
      <div class="arch-pipe-source">Partner feed</div>
      <div class="arch-pipe-source">Manual import</div>
    </div>
    <div class="arch-pipe-row">
      <div class="arch-pipe-stage landing">
        <div class="arch-pipe-head"><span class="arch-pipe-num">1</span>Landing</div>
        <div class="arch-pipe-item">Ingest API<small>validates the envelope only</small></div>
        <div class="arch-pipe-item">Raw store<small>append-only, 30 days</small></div>
        <div class="arch-pipe-item dead">Reject queue<small>malformed envelope</small></div>
      </div>
      <div class="arch-pipe-arrow">→</div>
      <div class="arch-pipe-stage">
        <div class="arch-pipe-head"><span class="arch-pipe-num">2</span>Normalise</div>
        <div class="arch-pipe-item">Schema map<small>per-source contracts</small></div>
        <div class="arch-pipe-item">Deduplicate<small>idempotency key</small></div>
        <div class="arch-pipe-item dead">Quarantine<small>contract drift</small></div>
      </div>
      <div class="arch-pipe-arrow">→</div>
      <div class="arch-pipe-stage">
        <div class="arch-pipe-head"><span class="arch-pipe-num">3</span>Enrich</div>
        <div class="arch-pipe-item">Identity join<small>account and tenant</small></div>
        <div class="arch-pipe-item">Geo and device<small>derived attributes</small></div>
        <div class="arch-pipe-item">Feature rollup<small>hourly windows</small></div>
      </div>
      <div class="arch-pipe-arrow">→</div>
      <div class="arch-pipe-stage serve">
        <div class="arch-pipe-head"><span class="arch-pipe-num">4</span>Serve</div>
        <div class="arch-pipe-item">Warehouse<small>analyst-facing</small></div>
        <div class="arch-pipe-item">Stream<small>operational dashboards</small></div>
        <div class="arch-pipe-item">Reverse ETL<small>back to the CRM</small></div>
      </div>
    </div>
    <div class="arch-pipe-sla">
      <div class="arch-pipe-kpi"><b>18s</b><span>p50 end to end</span></div>
      <div class="arch-pipe-kpi warn"><b>4m</b><span>p99 end to end</span></div>
      <div class="arch-pipe-kpi"><b>99.2%</b><span>accepted at landing</span></div>
      <div class="arch-pipe-kpi"><b>0.4%</b><span>quarantined</span></div>
    </div>
    <p class="arch-pipe-note">Dashed boxes are exits, not stages — nothing comes back through them.</p>
  </section>
</div>

## Data Shape

One column per stage, in order, and one row per component inside it. The reader should be able to read
the top line left to right and get the whole flow; the boxes underneath are detail, not the message.

## Key Options

| Option | Effect |
|---|---|
| A `flex` row of stage panels with a glyph between them | The flow is the layout, so order survives a copy-paste or a narrow column |
| A leading `1 · 2 · 3 · 4` badge on each stage heading | Numbering is redundant coding — the order is readable without the arrows |
| A separate top row for sources | Keeps inputs from being mistaken for stages |
| `border-style: dashed` for exits | Distinguishes "the flow stops here" from "the flow continues" without a legend |
| A KPI row under the pipeline | Answers the follow-up question ("how fast, how often does it fail") in the same figure |

## Pitfalls

- ❌ Putting the exit paths (reject, quarantine) in the arrow chain → ✅ they are exits; a dashed box inside
  the stage says so, an arrow out of the row implies a fifth stage
- ❌ More than five or six stages → ✅ group them; a pipeline diagram is about the shape of the flow, and
  every extra column makes each panel too narrow to read
- ❌ Using colour alone to mark the slow stage → ✅ the KPI row carries the number, and the box carries a word
- ❌ Drawing this as a layer stack because the columns are stacked vertically on a narrow screen → ✅ the
  flex row wraps as a whole; if it must stack, that is `layer-stack.md`

## Alternatives

| Variant | Use instead |
|---|---|
| The same system by layer rather than by stage | `layer-stack.md` |
| Stage-to-stage relationships, including back-edges | `request-paths.md` |
| A CI/CD pipeline rather than a data pipeline | `pipeline-stages.md` with stages renamed, or `basic-activity-flow.md` |

<!-- source: recovered from the architecture skill's layouts/pipeline.md — stage flow with inline arrows -->
