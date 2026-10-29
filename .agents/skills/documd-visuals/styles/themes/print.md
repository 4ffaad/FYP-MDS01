# Print theme

One achromatic ladder. Categories are told apart by luminance alone, so the ramp has five genuinely separable steps — a mono theme cannot offer eight. Semantic colour collapses too: positive and negative differ only by weight, so a figure that depends on red-versus-green must carry a label or a sign instead.

| | |
|---|---|
| scenario | black-and-white printing, photocopies, low-ink handouts, fax-grade pipelines |
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
    {"type":"rect","left":0,"top":0,"z":-10,"shape":{"width":640,"height":360},"style":{"fill":"#f9fafb","stroke":"#4b5563","lineWidth":1}},
    {"type":"rect","left":42,"top":70,"z":-9,"shape":{"width":570,"height":228},"style":{"fill":"#f3f4f6","stroke":"#4b5563","lineWidth":1}}
  ],
  "title": {
    "text": "Quarterly volume by channel",
    "subtext": "all eight categories, adjacent, on this theme’s own surface",
    "left": 14,
    "top": 10,
    "textStyle": {"color":"#111827","fontSize":15},
    "subtextStyle": {"color":"#6b7280","fontSize":11}
  },
  "color": ["#111827","#2b3440","#4b5563","#5f6771","#6b7280","#868f9b","#a3abb6","#c6ccd4"],
  "legend": {"bottom":6,"itemWidth":10,"itemHeight":10,"textStyle":{"color":"#111827","fontSize":10}},
  "grid": {"left":52,"right":18,"top":76,"bottom":52},
  "xAxis": {
    "type": "category",
    "data": ["Q1","Q2","Q3","Q4"],
    "axisLine": {"lineStyle":{"color":"#4b5563"}},
    "axisTick": {"lineStyle":{"color":"#4b5563"}},
    "axisLabel": {"color":"#6b7280"}
  },
  "yAxis": {"type":"value","axisLine":{"show":false},"axisLabel":{"color":"#6b7280"},"splitLine":{"lineStyle":{"color":"#4b5563"}}},
  "series": [
    {"name":"Direct","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#111827"},"data":[18,31,18,31]},
    {"name":"Partner","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#2b3440"},"data":[25,38,25,38]},
    {"name":"Search","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#4b5563"},"data":[32,19,32,19]},
    {"name":"Social","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#5f6771"},"data":[39,26,39,26]},
    {"name":"Email","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#6b7280"},"data":[20,33,20,33]},
    {"name":"Referral","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#868f9b"},"data":[27,40,27,40]},
    {"name":"Events","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#a3abb6"},"data":[34,21,34,21]},
    {
      "name": "Other",
      "type": "bar",
      "stack": "total",
      "barWidth": "52%",
      "itemStyle": {"color":"#c6ccd4"},
      "data": [41,28,41,28],
      "markLine": {
        "silent": true,
        "symbol": "none",
        "data": [
          {"yAxis":150,"lineStyle":{"type":"dashed","color":"#6b7280"},"label":{"color":"#6b7280","formatter":"target"}},
          {"yAxis":185,"lineStyle":{"type":"dotted","color":"#111827"},"label":{"color":"#6b7280","formatter":"limit"}}
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
| `muted` | `#6b7280` | ✓ | – | – | – | `page` | captions, axes tick labels, metadata — never inside a tinted fill |
| `line` | `#4b5563` | – | ✓ | – | – | – | borders, edges, arrows, axes, rules |
| `line-strong` | `#1f2937` | – | ✓ | – | – | – | emphasis border, connector on a tinted fill |
| `surface-0` | `#f9fafb` | – | – | ✓ | `#111827` | – | quietest container fill |
| `surface-1` | `#f3f4f6` | – | – | ✓ | `#111827` | – | default shape / card fill |
| `surface-2` | `#e5e7eb` | – | – | ✓ | `#111827` | – | nested or selected container fill |
| `cat-1` | `#111827` | ✓ | ✓ | ✓ | `#ffffff` | – | category 1 — also the accent colour |
| `cat-2` | `#2b3440` | – | ✓ | ✓ | – | – | category 2 — marks and lines only |
| `cat-3` | `#4b5563` | – | – | ✓ | – | – | category 3 — fill only; the family is too light for text or lines in any theme |
| `cat-4` | `#5f6771` | ✓ | ✓ | ✓ | `#ffffff` | – | category 4 |
| `cat-5` | `#6b7280` | ✓ | ✓ | ✓ | `#ffffff` | – | category 5 |
| `cat-6` | `#868f9b` | – | ✓ | ✓ | – | – | category 6 — marks and lines only |
| `cat-7` | `#a3abb6` | – | – | ✓ | – | – | category 7 — marks and lines only |
| `cat-8` | `#c6ccd4` | – | – | ✓ | – | – | category 8 |
| `positive` | `#4b5563` | – | ✓ | ✓ | – | – | gains, passes, healthy state |
| `positive-ink` | `#374151` | ✓ | ✓ | – | – | `page` | positive text and deltas |
| `negative` | `#111827` | ✓ | ✓ | ✓ | `#ffffff` | – | failures, regressions |
| `negative-ink` | `#0f1522` | ✓ | ✓ | – | – | `page` | negative text and deltas — the family shade, granted the text role so a red chip can carry red words |
| `warning` | `#a3abb6` | – | – | ✓ | – | – | warning fill / band |
| `warning-ink` | `#4b5563` | ✓ | ✓ | – | – | `page` | warning text and threshold lines |
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
| `cat-1` | `#111827` | `#d4d5d8` | `#0f1522` | `#111827` |
| `cat-2` | `#2b3440` | `#d9dadd` | `#262e38` | `#111827` |
| `cat-3` | `#4b5563` | `#dfe0e3` | – | `#111827` |
| `cat-4` | `#5f6771` | `#e2e4e5` | `#545b63` | `#111827` |
| `cat-5` | `#6b7280` | `#e4e6e8` | `#5e6471` | `#111827` |
| `cat-6` | `#868f9b` | `#e9ebed` | `#767e88` | `#111827` |
| `cat-7` | `#a3abb6` | `#eef0f2` | – | `#111827` |
| `cat-8` | `#c6ccd4` | `#f5f6f7` | – | `#111827` |
| `positive` | `#4b5563` | `#dfe0e3` | `#424b57` | `#111827` |
| `negative` | `#111827` | `#d4d5d8` | `#0f1522` | `#111827` |
| `warning` | `#a3abb6` | `#eef0f2` | – | `#111827` |

## Blocks

Copy-paste blocks for this theme. Use exactly one block per figure; mixing blocks, or
adding a hex of your own on top, gives up the consistency the theme exists for.
Every value is literal — no alias layer, here or in any other theme.

### plantuml · structure

_structure, class, component, deployment._ One block per diagram. This is the UML family — `@startmindmap`, `@startgantt`, `@startpacketdiag` and `@startwbs` ignore `skinparam` entirely (measured: byte-identical output with and without it). `Package` carries two lines rather than three: `PackageFontColor` is a measured no-op.

```plantuml
skinparam RectangleBackgroundColor #f3f4f6
skinparam RectangleBorderColor #4b5563
skinparam RectangleFontColor #111827
skinparam ComponentBackgroundColor #f3f4f6
skinparam ComponentBorderColor #4b5563
skinparam ComponentFontColor #111827
skinparam ClassBackgroundColor #f3f4f6
skinparam ClassBorderColor #4b5563
skinparam ClassFontColor #111827
skinparam UsecaseBackgroundColor #f3f4f6
skinparam UsecaseBorderColor #4b5563
skinparam UsecaseFontColor #111827
skinparam DatabaseBackgroundColor #f3f4f6
skinparam DatabaseBorderColor #4b5563
skinparam DatabaseFontColor #111827
skinparam NodeBackgroundColor #f3f4f6
skinparam NodeBorderColor #4b5563
skinparam NodeFontColor #111827
skinparam ActorBackgroundColor #f3f4f6
skinparam ActorBorderColor #4b5563
skinparam ActorFontColor #111827
skinparam StateBackgroundColor #f3f4f6
skinparam StateBorderColor #4b5563
skinparam StateFontColor #111827
skinparam ArtifactBackgroundColor #f3f4f6
skinparam ArtifactBorderColor #4b5563
skinparam ArtifactFontColor #111827
skinparam CloudBackgroundColor #f3f4f6
skinparam CloudBorderColor #4b5563
skinparam CloudFontColor #111827
skinparam FolderBackgroundColor #f3f4f6
skinparam FolderBorderColor #4b5563
skinparam FolderFontColor #111827
skinparam PackageBackgroundColor #f3f4f6
skinparam PackageBorderColor #4b5563
skinparam DefaultFontColor #111827
skinparam ArrowColor #4b5563
skinparam ArrowFontColor #111827
skinparam NoteBackgroundColor #e5e7eb
skinparam NoteBorderColor #4b5563
skinparam NoteFontColor #111827
skinparam stereotypeABackgroundColor #d4d5d8
skinparam stereotypeABorderColor #4b5563
skinparam stereotypeCBackgroundColor #d4d5d8
skinparam stereotypeCBorderColor #4b5563
skinparam stereotypeEBackgroundColor #d4d5d8
skinparam stereotypeEBorderColor #4b5563
skinparam stereotypeIBackgroundColor #d4d5d8
skinparam stereotypeIBorderColor #4b5563
```

### plantuml · sequence

_sequence._ Sequence diagrams take their own participant and lifeline keys; `ArrowColor` is shared with the structure block.

```plantuml
skinparam DefaultFontColor #111827
skinparam ArrowColor #4b5563
skinparam ArrowFontColor #111827
skinparam ParticipantBackgroundColor #f3f4f6
skinparam ParticipantBorderColor #4b5563
skinparam ParticipantFontColor #111827
skinparam SequenceLifeLineBorderColor #4b5563
skinparam NoteBackgroundColor #e5e7eb
skinparam NoteBorderColor #4b5563
skinparam NoteFontColor #111827
```

### plantuml · activity

_activity._ Activity steps take their own keys; the diamond is the decision node. A step can also be coloured on its own with `:step; <<#fill>>` — see the element block.

```plantuml
skinparam DefaultFontColor #111827
skinparam ArrowColor #4b5563
skinparam ArrowFontColor #111827
skinparam ActivityBackgroundColor #f3f4f6
skinparam ActivityBorderColor #4b5563
skinparam ActivityDiamondBackgroundColor #e5e7eb
```

### plantuml · element

_per-element colour._ When a block is not enough, colour one element. Use the **semicolon** form on every shape: `#fill;line:border`, with **no `#`** on the inner value. The `##` form is legal on the `class` family only — on a `rectangle`, official PlantUML does not error, it appends the suffix to the element name and falls back to an unparsed-colour fill, which is worse than a syntax error.

```plantuml
rectangle "Order service" as svc #d4d5d8;line:0f1522
rectangle "Failed batch" as fail #e2e4e5;line:545b63
```

### infographic · theme

_theme block._ Paste directly after the `infographic <template>` line, before `data`. `palette` must be a **list** — one `- #hex` per line; the space-separated form is a syntax error. Multi-colour templates read the ramp in order; single-colour templates ignore it and derive everything from `colorPrimary`, which is why one block serves all 113 templates.

```infographic
theme
  colorPrimary #111827
  palette
    - #111827
    - #2b3440
    - #4b5563
    - #5f6771
    - #6b7280
    - #868f9b
    - #a3abb6
    - #c6ccd4
```

### echarts · color

_colour ramp._ One line at the top level of every spec. Multi-series charts take one colour per series; a single series with coloured items (pie, sunburst, treemap, radar) takes one per data item; a plain single-series chart uses only the first. `itemStyle.color` on a series overrides this ramp.

```echarts
"color": ["#111827", "#2b3440", "#4b5563", "#5f6771", "#6b7280", "#868f9b", "#a3abb6", "#c6ccd4"]
```

### vega-lite · config

_config (Vega-Lite)._ Add as the first key of the spec. This sets the categorical range for every scale that does not declare its own.

```vega-lite
"config": { "range": { "category": ["#111827", "#2b3440", "#4b5563", "#5f6771", "#6b7280", "#868f9b", "#a3abb6", "#c6ccd4"] } }
```

### vega · scale

_ordinal colour scale (Vega)._ Rewrite the `range` of the ordinal colour scale the marks reference. Replace the `<dataset>` / `<category field>` placeholders with the real names. An explicit `scale.range` beats `config.range.category`, so a Vega spec must carry the ramp here.

```vega
{ "name": "color", "type": "ordinal", "domain": { "data": "<dataset>", "field": "<category field>" }, "range": ["#111827", "#2b3440", "#4b5563", "#5f6771", "#6b7280", "#868f9b", "#a3abb6", "#c6ccd4"] }
```

### html-css · card

_card._ Bare HTML card, coloured from the theme. The values are literal on purpose: documd-visuals does not follow the host document, so a card looks the same wherever it is pasted.

```css
.card {
  background: #f3f4f6;
  border-left: 4px solid #111827;
  color: #111827;
}
.card .kicker { color: #111827; }
```

### html-css · badge

_badge._ A small status chip: the tint carries the fill, the shade the border, and `ink` the label.

```css
.badge {
  background: #d4d5d8;
  color: #111827;
  border: 1px solid #0f1522;
}
```

## Verification

Every block above is rendered by the theme gate, which requires the declared values to land
and the engine defaults to be gone. The contrast gate recomputes every ratio in the token
table against this theme's ground. Both run per theme; see
[`../palette.md`](../palette.md) for the contract, and for the per-engine mechanism
[`../../engines/plantuml.md`](../../engines/plantuml.md) · [`../../engines/echarts.md`](../../engines/echarts.md) · [`../../engines/vega.md`](../../engines/vega.md) · [`../../engines/infographic.md`](../../engines/infographic.md) · [`../../engines/html-css.md`](../../engines/html-css.md).
