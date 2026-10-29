# Vivid theme

The same eight hues pushed to high chroma, on cool white surfaces. Four of the eight are light enough that they cannot carry text, so they are declared fill-only — a vivid slide should label its slices outside the slice anyway.

| | |
|---|---|
| scenario | presentations, slides, marketing pages, anything projected or glanced at |
| ground | `#ffffff` |

## Preview

The theme in use, as one whole figure rather than a fragment. Eight adjacent stack segments
so the ramp can be judged as a set; two levels of surface — the page (`surface-0`) and the
plot panel (`surface-1`) — each with its `line` border; `ink` and `muted` text; `line` on the
axes; and `target` / `negative` as the two dashed thresholds. Rendered by the theme gate like
every other block, so a theme with a wrong value cannot ship a plausible-looking preview. What
this figure does not reach — `surface-2`, the derived tints and shades, `warning` — is in the
two tables below.

```echarts
{
  "width": 640,
  "height": 360,
  "graphic": [
    {"type":"rect","left":0,"top":0,"z":-10,"shape":{"width":640,"height":360},"style":{"fill":"#f8fafc","stroke":"#556074","lineWidth":1}},
    {"type":"rect","left":42,"top":70,"z":-9,"shape":{"width":570,"height":228},"style":{"fill":"#eef2ff","stroke":"#556074","lineWidth":1}}
  ],
  "title": {
    "text": "Quarterly volume by channel",
    "subtext": "all eight categories, adjacent, on this theme’s own surface",
    "left": 14,
    "top": 10,
    "textStyle": {"color":"#111827","fontSize":15},
    "subtextStyle": {"color":"#5b6472","fontSize":11}
  },
  "color": ["#2563eb","#16a34a","#f59e0b","#dc2626","#7c3aed","#0d9488","#db2777","#92400e"],
  "legend": {"bottom":6,"itemWidth":10,"itemHeight":10,"textStyle":{"color":"#111827","fontSize":10}},
  "grid": {"left":52,"right":18,"top":76,"bottom":52},
  "xAxis": {
    "type": "category",
    "data": ["Q1","Q2","Q3","Q4"],
    "axisLine": {"lineStyle":{"color":"#556074"}},
    "axisTick": {"lineStyle":{"color":"#556074"}},
    "axisLabel": {"color":"#5b6472"}
  },
  "yAxis": {"type":"value","axisLine":{"show":false},"axisLabel":{"color":"#5b6472"},"splitLine":{"lineStyle":{"color":"#556074"}}},
  "series": [
    {"name":"Direct","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#2563eb"},"data":[18,31,18,31]},
    {"name":"Partner","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#16a34a"},"data":[25,38,25,38]},
    {"name":"Search","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#f59e0b"},"data":[32,19,32,19]},
    {"name":"Social","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#dc2626"},"data":[39,26,39,26]},
    {"name":"Email","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#7c3aed"},"data":[20,33,20,33]},
    {"name":"Referral","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#0d9488"},"data":[27,40,27,40]},
    {"name":"Events","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#db2777"},"data":[34,21,34,21]},
    {
      "name": "Other",
      "type": "bar",
      "stack": "total",
      "barWidth": "52%",
      "itemStyle": {"color":"#92400e"},
      "data": [41,28,41,28],
      "markLine": {
        "silent": true,
        "symbol": "none",
        "data": [
          {"yAxis":150,"lineStyle":{"type":"dashed","color":"#64748b"},"label":{"color":"#5b6472","formatter":"target"}},
          {"yAxis":185,"lineStyle":{"type":"dotted","color":"#dc2626"},"label":{"color":"#5b6472","formatter":"limit"}}
        ]
      }
    }
  ]
}
```

## Tokens

`text` / `line` / `fill` are the uses this theme grants the token; `sits on` is what a
text token may be placed on, `text on it` what may be placed on a fill. The widest use a
token may ever be granted is fixed by the contract in [`palette.md`](../palette.md) — a
theme narrows, it never widens.

| token | value | text | line | fill | text on it | sits on | role |
|---|---|---|---|---|---|---|---|
| `ink` | `#111827` | ✓ | – | – | – | `surface-*, tint-*` | body text inside fills, headings, node labels |
| `ink-soft` | `#374151` | ✓ | – | – | – | `page` | secondary body text on an unfilled background |
| `muted` | `#5b6472` | ✓ | – | – | – | `page` | captions, axes tick labels, metadata — never inside a tinted fill |
| `line` | `#556074` | – | ✓ | – | – | – | borders, edges, arrows, axes, rules |
| `line-strong` | `#374151` | – | ✓ | – | – | – | emphasis border, connector on a tinted fill |
| `surface-0` | `#f8fafc` | – | – | ✓ | `#111827` | – | quietest container fill |
| `surface-1` | `#eef2ff` | – | – | ✓ | `#111827` | – | default shape / card fill |
| `surface-2` | `#e0e7ff` | – | – | ✓ | `#111827` | – | nested or selected container fill |
| `cat-1` | `#2563eb` | ✓ | ✓ | ✓ | `#ffffff` | – | category 1 — also the accent colour |
| `cat-2` | `#16a34a` | – | ✓ | ✓ | – | – | category 2 — marks and lines only |
| `cat-3` | `#f59e0b` | – | – | ✓ | – | – | category 3 — fill only; the family is too light for text or lines in any theme |
| `cat-4` | `#dc2626` | ✓ | ✓ | ✓ | `#ffffff` | – | category 4 |
| `cat-5` | `#7c3aed` | ✓ | ✓ | ✓ | `#ffffff` | – | category 5 |
| `cat-6` | `#0d9488` | – | ✓ | ✓ | – | – | category 6 — marks and lines only |
| `cat-7` | `#db2777` | – | ✓ | ✓ | – | – | category 7 — marks and lines only |
| `cat-8` | `#92400e` | ✓ | ✓ | ✓ | `#ffffff` | – | category 8 |
| `positive` | `#16a34a` | – | ✓ | ✓ | – | – | gains, passes, healthy state |
| `positive-ink` | `#15803d` | ✓ | ✓ | – | – | `page` | positive text and deltas |
| `negative` | `#dc2626` | ✓ | ✓ | ✓ | `#ffffff` | – | failures, regressions |
| `negative-ink` | `#c22121` | ✓ | ✓ | – | – | `page` | negative text and deltas — the family shade, granted the text role so a red chip can carry red words |
| `warning` | `#f59e0b` | – | – | ✓ | – | – | warning fill / band |
| `warning-ink` | `#b45309` | ✓ | ✓ | – | – | `page` | warning text and threshold lines |
| `target` | `#64748b` | – | ✓ | – | – | – | dashed reference lines / goal markers |

## Derived colours

Computed from the token values, never hand-picked: `tint` = mix(`#ffffff`, family, 18 %),
`shade` = darken the family by 12 % (HSL lightness). The mix base is the theme's
**ground**, not a surface: mixing into a tinted near-white drags every hue towards the same
grey and the tints stop being tellable apart. A family has a shade only when this theme lets
it be a line — a family too light to be a line is too light to border its own fill, so it
takes the neutral `line` border instead.

| family | value | tint | shade | ink on tint |
|---|---|---|---|---|
| `cat-1` | `#2563eb` | `#d8e3fb` | `#2157cf` | `#111827` |
| `cat-2` | `#16a34a` | `#d5eede` | `#138f41` | `#111827` |
| `cat-3` | `#f59e0b` | `#fdeed3` | – | `#111827` |
| `cat-4` | `#dc2626` | `#f9d8d8` | `#c22121` | `#111827` |
| `cat-5` | `#7c3aed` | `#e7dcfc` | `#661aea` | `#111827` |
| `cat-6` | `#0d9488` | `#d3ecea` | `#0b8278` | `#111827` |
| `cat-7` | `#db2777` | `#f9d8e7` | `#c12269` | `#111827` |
| `cat-8` | `#92400e` | `#ebddd4` | `#80380c` | `#111827` |
| `positive` | `#16a34a` | `#d5eede` | `#138f41` | `#111827` |
| `negative` | `#dc2626` | `#f9d8d8` | `#c22121` | `#111827` |
| `warning` | `#f59e0b` | `#fdeed3` | – | `#111827` |

## Blocks

Copy-paste blocks for this theme. Use exactly one block per figure; mixing blocks, or
adding a hex of your own on top, gives up the consistency the theme exists for.
Every value is literal — no alias layer, here or in any other theme.

### plantuml · structure

_structure, class, component, deployment._ One block per diagram. This is the UML family — `@startmindmap`, `@startgantt`, `@startpacketdiag` and `@startwbs` ignore `skinparam` entirely (measured: byte-identical output with and without it). `Package` carries two lines rather than three: `PackageFontColor` is a measured no-op.

```plantuml
skinparam RectangleBackgroundColor #eef2ff
skinparam RectangleBorderColor #556074
skinparam RectangleFontColor #111827
skinparam ComponentBackgroundColor #eef2ff
skinparam ComponentBorderColor #556074
skinparam ComponentFontColor #111827
skinparam ClassBackgroundColor #eef2ff
skinparam ClassBorderColor #556074
skinparam ClassFontColor #111827
skinparam UsecaseBackgroundColor #eef2ff
skinparam UsecaseBorderColor #556074
skinparam UsecaseFontColor #111827
skinparam DatabaseBackgroundColor #eef2ff
skinparam DatabaseBorderColor #556074
skinparam DatabaseFontColor #111827
skinparam NodeBackgroundColor #eef2ff
skinparam NodeBorderColor #556074
skinparam NodeFontColor #111827
skinparam ActorBackgroundColor #eef2ff
skinparam ActorBorderColor #556074
skinparam ActorFontColor #111827
skinparam StateBackgroundColor #eef2ff
skinparam StateBorderColor #556074
skinparam StateFontColor #111827
skinparam ArtifactBackgroundColor #eef2ff
skinparam ArtifactBorderColor #556074
skinparam ArtifactFontColor #111827
skinparam CloudBackgroundColor #eef2ff
skinparam CloudBorderColor #556074
skinparam CloudFontColor #111827
skinparam FolderBackgroundColor #eef2ff
skinparam FolderBorderColor #556074
skinparam FolderFontColor #111827
skinparam PackageBackgroundColor #eef2ff
skinparam PackageBorderColor #556074
skinparam DefaultFontColor #111827
skinparam ArrowColor #556074
skinparam ArrowFontColor #111827
skinparam NoteBackgroundColor #e0e7ff
skinparam NoteBorderColor #556074
skinparam NoteFontColor #111827
skinparam stereotypeABackgroundColor #d8e3fb
skinparam stereotypeABorderColor #556074
skinparam stereotypeCBackgroundColor #d8e3fb
skinparam stereotypeCBorderColor #556074
skinparam stereotypeEBackgroundColor #d8e3fb
skinparam stereotypeEBorderColor #556074
skinparam stereotypeIBackgroundColor #d8e3fb
skinparam stereotypeIBorderColor #556074
```

### plantuml · sequence

_sequence._ Sequence diagrams take their own participant and lifeline keys; `ArrowColor` is shared with the structure block.

```plantuml
skinparam DefaultFontColor #111827
skinparam ArrowColor #556074
skinparam ArrowFontColor #111827
skinparam ParticipantBackgroundColor #eef2ff
skinparam ParticipantBorderColor #556074
skinparam ParticipantFontColor #111827
skinparam SequenceLifeLineBorderColor #556074
skinparam NoteBackgroundColor #e0e7ff
skinparam NoteBorderColor #556074
skinparam NoteFontColor #111827
```

### plantuml · activity

_activity._ Activity steps take their own keys; the diamond is the decision node. A step can also be coloured on its own with `:step; <<#fill>>` — see the element block.

```plantuml
skinparam DefaultFontColor #111827
skinparam ArrowColor #556074
skinparam ArrowFontColor #111827
skinparam ActivityBackgroundColor #eef2ff
skinparam ActivityBorderColor #556074
skinparam ActivityDiamondBackgroundColor #e0e7ff
```

### plantuml · element

_per-element colour._ When a block is not enough, colour one element. Use the **semicolon** form on every shape: `#fill;line:border`, with **no `#`** on the inner value. The `##` form is legal on the `class` family only — on a `rectangle`, official PlantUML does not error, it appends the suffix to the element name and falls back to an unparsed-colour fill, which is worse than a syntax error.

```plantuml
rectangle "Order service" as svc #d8e3fb;line:2157cf
rectangle "Failed batch" as fail #f9d8d8;line:c22121
```

### infographic · theme

_theme block._ Paste directly after the `infographic <template>` line, before `data`. `palette` must be a **list** — one `- #hex` per line; the space-separated form is a syntax error. Multi-colour templates read the ramp in order; single-colour templates ignore it and derive everything from `colorPrimary`, which is why one block serves all 113 templates.

```infographic
theme
  colorPrimary #2563eb
  palette
    - #2563eb
    - #16a34a
    - #f59e0b
    - #dc2626
    - #7c3aed
    - #0d9488
    - #db2777
    - #92400e
```

### echarts · color

_colour ramp._ One line at the top level of every spec. Multi-series charts take one colour per series; a single series with coloured items (pie, sunburst, treemap, radar) takes one per data item; a plain single-series chart uses only the first. `itemStyle.color` on a series overrides this ramp.

```echarts
"color": ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed", "#0d9488", "#db2777", "#92400e"]
```

### vega-lite · config

_config (Vega-Lite)._ Add as the first key of the spec. This sets the categorical range for every scale that does not declare its own.

```vega-lite
"config": { "range": { "category": ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed", "#0d9488", "#db2777", "#92400e"] } }
```

### vega · scale

_ordinal colour scale (Vega)._ Rewrite the `range` of the ordinal colour scale the marks reference. Replace the `<dataset>` / `<category field>` placeholders with the real names. An explicit `scale.range` beats `config.range.category`, so a Vega spec must carry the ramp here.

```vega
{ "name": "color", "type": "ordinal", "domain": { "data": "<dataset>", "field": "<category field>" }, "range": ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed", "#0d9488", "#db2777", "#92400e"] }
```

### html-css · card

_card._ Bare HTML card, coloured from the theme. The values are literal on purpose: documd-visuals does not follow the host document, so a card looks the same wherever it is pasted.

```css
.card {
  background: #eef2ff;
  border-left: 4px solid #2563eb;
  color: #111827;
}
.card .kicker { color: #2563eb; }
```

### html-css · badge

_badge._ A small status chip: the tint carries the fill, the shade the border, and `ink` the label.

```css
.badge {
  background: #d8e3fb;
  color: #111827;
  border: 1px solid #2157cf;
}
```

## Verification

Every block above is rendered by the theme gate, which requires the declared values to land
and the engine defaults to be gone. The contrast gate recomputes every ratio in the token
table against this theme's ground. Both run per theme; see
[`../palette.md`](../palette.md) for the contract, and for the per-engine mechanism
[`../../engines/plantuml.md`](../../engines/plantuml.md) · [`../../engines/echarts.md`](../../engines/echarts.md) · [`../../engines/vega.md`](../../engines/vega.md) · [`../../engines/infographic.md`](../../engines/infographic.md) · [`../../engines/html-css.md`](../../engines/html-css.md).
