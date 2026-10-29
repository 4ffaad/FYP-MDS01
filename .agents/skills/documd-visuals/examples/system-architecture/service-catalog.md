# Service Catalog Grid (HTML/CSS)

**Best for**: an inventory of equal-weight services where the reader needs to scan for ownership, tier and health rather than follow a flow
**Avoid when**: the services have a hierarchy or a call order → `layer-stack.md` or `request-paths.md`; a flat grid throws that information away
**Answers**: what exists, who owns it, how critical it is, and which ones are not healthy

<div style="max-width: 1120px; box-sizing: border-box; position: relative;">
  <style scoped>
    .arch-cat { background: #f8fafc; padding: 26px; font-family: 'Segoe UI', sans-serif; color: #1f2937; }
    .arch-cat-title { margin: 0 0 6px; text-align: center; font-size: 26px; font-weight: 700; }
    .arch-cat-sub { margin: 0 0 18px; text-align: center; font-size: 13px; color: #676f7e; }
    .arch-cat-summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 16px; }
    .arch-cat-tile { padding: 10px; text-align: center; border-radius: 4px; background: #eef2fb; border: 1px solid #5b6b8c; }
    .arch-cat-tile b { display: block; font-size: 20px; font-weight: 700; }
    .arch-cat-tile span { font-size: 10px; letter-spacing: 0.08em; text-transform: uppercase; color: #676f7e; }
    .arch-cat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
    .arch-cat-card { padding: 11px 12px; border-radius: 5px; background: #ffffff; border: 1px solid #5b6b8c; border-left-width: 4px; }
    .arch-cat-card.t0 { border-left-color: #2b66c4; }
    .arch-cat-card.t1 { border-left-color: #0f9b9b; }
    .arch-cat-card.t2 { border-left-color: #6b7280; }
    .arch-cat-card.degraded { background: #fdeedc; }
    .arch-cat-card.retiring { background: #f8fafc; border-style: dashed; }
    .arch-cat-name { font-size: 13px; font-weight: 700; margin-bottom: 2px; }
    .arch-cat-owner { font-size: 10px; color: #676f7e; margin-bottom: 8px; }
    .arch-cat-facts { display: flex; flex-wrap: wrap; gap: 5px; }
    .arch-cat-fact { font-size: 10px; padding: 2px 7px; border-radius: 9px; background: #eef2fb; border: 1px solid #5b6b8c; }
    .arch-cat-fact.ok { background: #daeedd; border-color: #298b3c; color: #1f7a33; font-weight: 600; }
    .arch-cat-fact.warn { background: #fdeedc; border-color: #8a5a00; color: #8a5a00; font-weight: 600; }
    .arch-cat-fact.out { background: #f7d8da; border-color: #b82029; color: #b82029; font-weight: 600; }
    .arch-cat-legend { display: flex; gap: 16px; justify-content: center; margin-top: 16px; font-size: 11px; color: #676f7e; }
    .arch-cat-legend i { display: inline-block; width: 4px; height: 12px; border-left: 4px solid; border-radius: 1px; margin-right: 6px; vertical-align: -2px; }
  </style>
  <section class="arch-cat">
    <h1 class="arch-cat-title">Service Catalog</h1>
    <p class="arch-cat-sub">every service is one card — no card is more important than another, tier does that job</p>
    <div class="arch-cat-summary">
      <div class="arch-cat-tile"><b>16</b><span>services</span></div>
      <div class="arch-cat-tile"><b>6</b><span>owning teams</span></div>
      <div class="arch-cat-tile"><b>2</b><span>degraded</span></div>
      <div class="arch-cat-tile"><b>1</b><span>retiring</span></div>
    </div>
    <div class="arch-cat-grid">
      <div class="arch-cat-card t0"><div class="arch-cat-name">Identity</div><div class="arch-cat-owner">Platform</div><div class="arch-cat-facts"><span class="arch-cat-fact">tier 0</span><span class="arch-cat-fact ok">healthy</span></div></div>
      <div class="arch-cat-card t0"><div class="arch-cat-name">API gateway</div><div class="arch-cat-owner">Platform</div><div class="arch-cat-facts"><span class="arch-cat-fact">tier 0</span><span class="arch-cat-fact ok">healthy</span></div></div>
      <div class="arch-cat-card t0 degraded"><div class="arch-cat-name">Payments</div><div class="arch-cat-owner">Money</div><div class="arch-cat-facts"><span class="arch-cat-fact">tier 0</span><span class="arch-cat-fact warn">elevated p99</span></div></div>
      <div class="arch-cat-card t0"><div class="arch-cat-name">Orders</div><div class="arch-cat-owner">Money</div><div class="arch-cat-facts"><span class="arch-cat-fact">tier 0</span><span class="arch-cat-fact ok">healthy</span></div></div>
      <div class="arch-cat-card t1"><div class="arch-cat-name">Catalog</div><div class="arch-cat-owner">Merch</div><div class="arch-cat-facts"><span class="arch-cat-fact">tier 1</span><span class="arch-cat-fact ok">healthy</span></div></div>
      <div class="arch-cat-card t1"><div class="arch-cat-name">Pricing</div><div class="arch-cat-owner">Merch</div><div class="arch-cat-facts"><span class="arch-cat-fact">tier 1</span><span class="arch-cat-fact ok">healthy</span></div></div>
      <div class="arch-cat-card t1 degraded"><div class="arch-cat-name">Search</div><div class="arch-cat-owner">Discovery</div><div class="arch-cat-facts"><span class="arch-cat-fact">tier 1</span><span class="arch-cat-fact warn">index lag 12m</span></div></div>
      <div class="arch-cat-card t1"><div class="arch-cat-name">Notifications</div><div class="arch-cat-owner">Growth</div><div class="arch-cat-facts"><span class="arch-cat-fact">tier 1</span><span class="arch-cat-fact ok">healthy</span></div></div>
      <div class="arch-cat-card t2"><div class="arch-cat-name">Recommendations</div><div class="arch-cat-owner">Discovery</div><div class="arch-cat-facts"><span class="arch-cat-fact">tier 2</span><span class="arch-cat-fact ok">healthy</span></div></div>
      <div class="arch-cat-card t2"><div class="arch-cat-name">Reviews</div><div class="arch-cat-owner">Growth</div><div class="arch-cat-facts"><span class="arch-cat-fact">tier 2</span><span class="arch-cat-fact ok">healthy</span></div></div>
      <div class="arch-cat-card t2"><div class="arch-cat-name">Media</div><div class="arch-cat-owner">Merch</div><div class="arch-cat-facts"><span class="arch-cat-fact">tier 2</span><span class="arch-cat-fact ok">healthy</span></div></div>
      <div class="arch-cat-card t2"><div class="arch-cat-name">Reporting</div><div class="arch-cat-owner">Data</div><div class="arch-cat-facts"><span class="arch-cat-fact">tier 2</span><span class="arch-cat-fact ok">healthy</span></div></div>
      <div class="arch-cat-card t2"><div class="arch-cat-name">Audit</div><div class="arch-cat-owner">Platform</div><div class="arch-cat-facts"><span class="arch-cat-fact">tier 2</span><span class="arch-cat-fact ok">healthy</span></div></div>
      <div class="arch-cat-card t2"><div class="arch-cat-name">Feature flags</div><div class="arch-cat-owner">Platform</div><div class="arch-cat-facts"><span class="arch-cat-fact">tier 2</span><span class="arch-cat-fact ok">healthy</span></div></div>
      <div class="arch-cat-card t2"><div class="arch-cat-name">Exports</div><div class="arch-cat-owner">Data</div><div class="arch-cat-facts"><span class="arch-cat-fact">tier 2</span><span class="arch-cat-fact ok">healthy</span></div></div>
      <div class="arch-cat-card t2 retiring"><div class="arch-cat-name">Legacy cart</div><div class="arch-cat-owner">Money</div><div class="arch-cat-facts"><span class="arch-cat-fact">tier 2</span><span class="arch-cat-fact out">retiring Q3</span></div></div>
    </div>
    <div class="arch-cat-legend"><span><i style="border-left-color: #2b66c4;"></i>tier 0 — pages someone at night</span><span><i style="border-left-color: #0f9b9b;"></i>tier 1 — business hours</span><span><i style="border-left-color: #6b7280;"></i>tier 2 — best effort</span></div>
  </section>
</div>

## Data Shape

One card per service, all the same size, in a grid. The card carries four facts and nothing else: name,
owning team, tier, health. The tier is a coloured left edge; the health is a chip with words in it.

## Key Options

| Option | Effect |
|---|---|
| A fixed `repeat(4, 1fr)` grid with equal cards | Equal weight is the message; a card that is wider reads as more important |
| Tier as a `border-left` colour | Tier is ordinal, so it belongs on a continuous edge rather than in a chip |
| Health as a chip with words | Health is not ordinal — "elevated p99" and "index lag 12m" are different problems, and colour alone cannot say which |
| A tinted card background for degraded services | Redundant coding: the card is visibly different before any text is read |
| `border-style: dashed` for retiring services | A third state that is not a health state, so it must not reuse a health colour |
| A summary tile row above the grid | The count is the first question asked of a catalog |

## Pitfalls

- ❌ Ordering cards by importance → ✅ tier already encodes that, and any other order makes the grid
  impossible to scan for a missing service
- ❌ Colour-only health → ✅ the chip carries words; colour-blind readers and greyscale prints both need them
- ❌ Putting a fourth colour on the card for "team" → ✅ six teams cannot be told apart by hue at this size;
  the team is a label
- ❌ Letting the grid wrap unevenly at the end → ✅ a catalog with a ragged last row looks incomplete even
  when it is not; pad the row or pick a column count that divides the count
- ❌ More than about twenty services → ✅ past that it is a table, and a table sorts and filters

## Alternatives

| Variant | Use instead |
|---|---|
| The same services by layer and dependency | `layer-stack.md` |
| The call paths between the tier-0 services | `request-paths.md` |
| A sortable inventory rather than a figure | A table, or the `catalog` examples under `goal-and-status-reporting` |

<!-- source: recovered from the architecture skill's layouts/grid-catalog.md — equal-weight grid with per-card status -->
