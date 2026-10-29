# Default theme

The reference theme: a deep neutral blue accent over cool near-white surfaces. Calm enough for a report, structured enough for a dashboard. Every other theme is a deliberate departure from it.

| | |
|---|---|
| scenario | documents, reports, dashboards, anything that lives on a white page |
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
    {"type":"rect","left":0,"top":0,"z":-10,"shape":{"width":640,"height":360},"style":{"fill":"#f8fafc","stroke":"#5b6b8c","lineWidth":1}},
    {"type":"rect","left":42,"top":70,"z":-9,"shape":{"width":570,"height":228},"style":{"fill":"#eef2fb","stroke":"#5b6b8c","lineWidth":1}}
  ],
  "title": {
    "text": "Quarterly volume by channel",
    "subtext": "all eight categories, adjacent, on this theme’s own surface",
    "left": 14,
    "top": 10,
    "textStyle": {"color":"#1f2937","fontSize":15},
    "subtextStyle": {"color":"#676f7e","fontSize":11}
  },
  "color": ["#2b66c4","#2f9e44","#f3a33c","#d1242f","#7048e8","#0f9b9b","#c16f8a","#7c5a3d"],
  "legend": {"bottom":6,"itemWidth":10,"itemHeight":10,"textStyle":{"color":"#1f2937","fontSize":10}},
  "grid": {"left":52,"right":18,"top":76,"bottom":52},
  "xAxis": {
    "type": "category",
    "data": ["Q1","Q2","Q3","Q4"],
    "axisLine": {"lineStyle":{"color":"#5b6b8c"}},
    "axisTick": {"lineStyle":{"color":"#5b6b8c"}},
    "axisLabel": {"color":"#676f7e"}
  },
  "yAxis": {"type":"value","axisLine":{"show":false},"axisLabel":{"color":"#676f7e"},"splitLine":{"lineStyle":{"color":"#5b6b8c"}}},
  "series": [
    {"name":"Direct","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#2b66c4"},"data":[18,31,18,31]},
    {"name":"Partner","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#2f9e44"},"data":[25,38,25,38]},
    {"name":"Search","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#f3a33c"},"data":[32,19,32,19]},
    {"name":"Social","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#d1242f"},"data":[39,26,39,26]},
    {"name":"Email","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#7048e8"},"data":[20,33,20,33]},
    {"name":"Referral","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#0f9b9b"},"data":[27,40,27,40]},
    {"name":"Events","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#c16f8a"},"data":[34,21,34,21]},
    {
      "name": "Other",
      "type": "bar",
      "stack": "total",
      "barWidth": "52%",
      "itemStyle": {"color":"#7c5a3d"},
      "data": [41,28,41,28],
      "markLine": {
        "silent": true,
        "symbol": "none",
        "data": [
          {"yAxis":150,"lineStyle":{"type":"dashed","color":"#6b7280"},"label":{"color":"#676f7e","formatter":"target"}},
          {"yAxis":185,"lineStyle":{"type":"dotted","color":"#d1242f"},"label":{"color":"#676f7e","formatter":"limit"}}
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
| `ink` | `#1f2937` | ✓ | – | – | – | `surface-*, tint-*` | body text inside fills, headings, node labels |
| `ink-soft` | `#4b5563` | ✓ | – | – | – | `page` | secondary body text on an unfilled background |
| `muted` | `#676f7e` | ✓ | – | – | – | `page` | captions, axes tick labels, metadata — never inside a tinted fill |
| `line` | `#5b6b8c` | – | ✓ | – | – | – | borders, edges, arrows, axes, rules |
| `line-strong` | `#334155` | – | ✓ | – | – | – | emphasis border, connector on a tinted fill |
| `surface-0` | `#f8fafc` | – | – | ✓ | `#1f2937` | – | quietest container fill |
| `surface-1` | `#eef2fb` | – | – | ✓ | `#1f2937` | – | default shape / card fill |
| `surface-2` | `#dfe5fb` | – | – | ✓ | `#1f2937` | – | nested or selected container fill |
| `cat-1` | `#2b66c4` | ✓ | ✓ | ✓ | `#ffffff` | – | category 1 — also the accent colour |
| `cat-2` | `#2f9e44` | – | ✓ | ✓ | – | – | category 2 — marks and lines only |
| `cat-3` | `#f3a33c` | – | – | ✓ | – | – | category 3 — fill only; the family is too light for text or lines in any theme |
| `cat-4` | `#d1242f` | ✓ | ✓ | ✓ | `#ffffff` | – | category 4 |
| `cat-5` | `#7048e8` | ✓ | ✓ | ✓ | `#ffffff` | – | category 5 |
| `cat-6` | `#0f9b9b` | – | ✓ | ✓ | – | – | category 6 — marks and lines only |
| `cat-7` | `#c16f8a` | – | ✓ | ✓ | – | – | category 7 — marks and lines only |
| `cat-8` | `#7c5a3d` | ✓ | ✓ | ✓ | `#ffffff` | – | category 8 |
| `positive` | `#2f9e44` | – | ✓ | ✓ | – | – | gains, passes, healthy state |
| `positive-ink` | `#1f7a33` | ✓ | ✓ | – | – | `page` | positive text and deltas |
| `negative` | `#d1242f` | ✓ | ✓ | ✓ | `#ffffff` | – | failures, regressions |
| `negative-ink` | `#b82029` | ✓ | ✓ | – | – | `page` | negative text and deltas — the family shade, granted the text role so a red chip can carry red words |
| `warning` | `#f3a33c` | – | – | ✓ | – | – | warning fill / band |
| `warning-ink` | `#8a5a00` | ✓ | ✓ | – | – | `page` | warning text and threshold lines |
| `target` | `#6b7280` | – | ✓ | – | – | – | dashed reference lines / goal markers |

## Derived colours

Computed from the token values, never hand-picked: `tint` = mix(`#ffffff`, family, 18 %),
`shade` = darken the family by 12 % (HSL lightness). The mix base is the theme's
**ground**, not a surface: mixing into a tinted near-white drags every hue towards the same
grey and the tints stop being tellable apart. A family has a shade only when this theme lets
it be a line — a family too light to be a line is too light to border its own fill, so it
takes the neutral `line` border instead.

| family | value | tint | shade | ink on tint |
|---|---|---|---|---|
| `cat-1` | `#2b66c4` | `#d9e3f4` | `#265aac` | `#1f2937` |
| `cat-2` | `#2f9e44` | `#daeedd` | `#298b3c` | `#1f2937` |
| `cat-3` | `#f3a33c` | `#fdeedc` | – | `#1f2937` |
| `cat-4` | `#d1242f` | `#f7d8da` | `#b82029` | `#1f2937` |
| `cat-5` | `#7048e8` | `#e5defb` | `#5728e4` | `#1f2937` |
| `cat-6` | `#0f9b9b` | `#d4eded` | `#0d8888` | `#1f2937` |
| `cat-7` | `#c16f8a` | `#f4e5ea` | `#b65575` | `#1f2937` |
| `cat-8` | `#7c5a3d` | `#e7e1dc` | `#6d4f36` | `#1f2937` |
| `positive` | `#2f9e44` | `#daeedd` | `#298b3c` | `#1f2937` |
| `negative` | `#d1242f` | `#f7d8da` | `#b82029` | `#1f2937` |
| `warning` | `#f3a33c` | `#fdeedc` | – | `#1f2937` |

## Blocks

Copy-paste blocks for this theme. Use exactly one block per figure; mixing blocks, or
adding a hex of your own on top, gives up the consistency the theme exists for.
Every value is literal — no alias layer, here or in any other theme.

### plantuml · structure

_structure, class, component, deployment._ One block per diagram. This is the UML family — `@startmindmap`, `@startgantt`, `@startpacketdiag` and `@startwbs` ignore `skinparam` entirely (measured: byte-identical output with and without it). `Package` carries two lines rather than three: `PackageFontColor` is a measured no-op.

```plantuml
skinparam RectangleBackgroundColor #eef2fb
skinparam RectangleBorderColor #5b6b8c
skinparam RectangleFontColor #1f2937
skinparam ComponentBackgroundColor #eef2fb
skinparam ComponentBorderColor #5b6b8c
skinparam ComponentFontColor #1f2937
skinparam ClassBackgroundColor #eef2fb
skinparam ClassBorderColor #5b6b8c
skinparam ClassFontColor #1f2937
skinparam UsecaseBackgroundColor #eef2fb
skinparam UsecaseBorderColor #5b6b8c
skinparam UsecaseFontColor #1f2937
skinparam DatabaseBackgroundColor #eef2fb
skinparam DatabaseBorderColor #5b6b8c
skinparam DatabaseFontColor #1f2937
skinparam NodeBackgroundColor #eef2fb
skinparam NodeBorderColor #5b6b8c
skinparam NodeFontColor #1f2937
skinparam ActorBackgroundColor #eef2fb
skinparam ActorBorderColor #5b6b8c
skinparam ActorFontColor #1f2937
skinparam StateBackgroundColor #eef2fb
skinparam StateBorderColor #5b6b8c
skinparam StateFontColor #1f2937
skinparam ArtifactBackgroundColor #eef2fb
skinparam ArtifactBorderColor #5b6b8c
skinparam ArtifactFontColor #1f2937
skinparam CloudBackgroundColor #eef2fb
skinparam CloudBorderColor #5b6b8c
skinparam CloudFontColor #1f2937
skinparam FolderBackgroundColor #eef2fb
skinparam FolderBorderColor #5b6b8c
skinparam FolderFontColor #1f2937
skinparam PackageBackgroundColor #eef2fb
skinparam PackageBorderColor #5b6b8c
skinparam DefaultFontColor #1f2937
skinparam ArrowColor #5b6b8c
skinparam ArrowFontColor #1f2937
skinparam NoteBackgroundColor #dfe5fb
skinparam NoteBorderColor #5b6b8c
skinparam NoteFontColor #1f2937
skinparam stereotypeABackgroundColor #d9e3f4
skinparam stereotypeABorderColor #5b6b8c
skinparam stereotypeCBackgroundColor #d9e3f4
skinparam stereotypeCBorderColor #5b6b8c
skinparam stereotypeEBackgroundColor #d9e3f4
skinparam stereotypeEBorderColor #5b6b8c
skinparam stereotypeIBackgroundColor #d9e3f4
skinparam stereotypeIBorderColor #5b6b8c
```

### plantuml · sequence

_sequence._ Sequence diagrams take their own participant and lifeline keys; `ArrowColor` is shared with the structure block.

```plantuml
skinparam DefaultFontColor #1f2937
skinparam ArrowColor #5b6b8c
skinparam ArrowFontColor #1f2937
skinparam ParticipantBackgroundColor #eef2fb
skinparam ParticipantBorderColor #5b6b8c
skinparam ParticipantFontColor #1f2937
skinparam SequenceLifeLineBorderColor #5b6b8c
skinparam NoteBackgroundColor #dfe5fb
skinparam NoteBorderColor #5b6b8c
skinparam NoteFontColor #1f2937
```

### plantuml · activity

_activity._ Activity steps take their own keys; the diamond is the decision node. A step can also be coloured on its own with `:step; <<#fill>>` — see the element block.

```plantuml
skinparam DefaultFontColor #1f2937
skinparam ArrowColor #5b6b8c
skinparam ArrowFontColor #1f2937
skinparam ActivityBackgroundColor #eef2fb
skinparam ActivityBorderColor #5b6b8c
skinparam ActivityDiamondBackgroundColor #dfe5fb
```

### plantuml · element

_per-element colour._ When a block is not enough, colour one element. Use the **semicolon** form on every shape: `#fill;line:border`, with **no `#`** on the inner value. The `##` form is legal on the `class` family only — on a `rectangle`, official PlantUML does not error, it appends the suffix to the element name and falls back to an unparsed-colour fill, which is worse than a syntax error.

```plantuml
rectangle "Order service" as svc #d9e3f4;line:265aac
rectangle "Failed batch" as fail #f7d8da;line:b82029
```

### infographic · theme

_theme block._ Paste directly after the `infographic <template>` line, before `data`. `palette` must be a **list** — one `- #hex` per line; the space-separated form is a syntax error. Multi-colour templates read the ramp in order; single-colour templates ignore it and derive everything from `colorPrimary`, which is why one block serves all 113 templates.

```infographic
theme
  colorPrimary #2b66c4
  palette
    - #2b66c4
    - #2f9e44
    - #f3a33c
    - #d1242f
    - #7048e8
    - #0f9b9b
    - #c16f8a
    - #7c5a3d
```

### echarts · color

_colour ramp._ One line at the top level of every spec. Multi-series charts take one colour per series; a single series with coloured items (pie, sunburst, treemap, radar) takes one per data item; a plain single-series chart uses only the first. `itemStyle.color` on a series overrides this ramp.

```echarts
"color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"]
```

### vega-lite · config

_config (Vega-Lite)._ Add as the first key of the spec. This sets the categorical range for every scale that does not declare its own.

```vega-lite
"config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } }
```

### vega · scale

_ordinal colour scale (Vega)._ Rewrite the `range` of the ordinal colour scale the marks reference. Replace the `<dataset>` / `<category field>` placeholders with the real names. An explicit `scale.range` beats `config.range.category`, so a Vega spec must carry the ramp here.

```vega
{ "name": "color", "type": "ordinal", "domain": { "data": "<dataset>", "field": "<category field>" }, "range": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] }
```

### html-css · card

_card._ Bare HTML card, coloured from the theme. The values are literal on purpose: documd-visuals does not follow the host document, so a card looks the same wherever it is pasted.

```css
.card {
  background: #eef2fb;
  border-left: 4px solid #2b66c4;
  color: #1f2937;
}
.card .kicker { color: #2b66c4; }
```

### html-css · badge

_badge._ A small status chip: the tint carries the fill, the shade the border, and `ink` the label.

```css
.badge {
  background: #d9e3f4;
  color: #1f2937;
  border: 1px solid #265aac;
}
```

## Verification

Every block above is rendered by the theme gate, which requires the declared values to land
and the engine defaults to be gone. The contrast gate recomputes every ratio in the token
table against this theme's ground. Both run per theme; see
[`../palette.md`](../palette.md) for the contract, and for the per-engine mechanism
[`../../engines/plantuml.md`](../../engines/plantuml.md) · [`../../engines/echarts.md`](../../engines/echarts.md) · [`../../engines/vega.md`](../../engines/vega.md) · [`../../engines/infographic.md`](../../engines/infographic.md) · [`../../engines/html-css.md`](../../engines/html-css.md).
