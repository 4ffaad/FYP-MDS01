# Contrast theme

Everything raised. Ink is black, every line clears 4.5 where other themes settle for 3.0, and all eight categories are dark enough to serve as text as well as marks. Built to the APCA use-case ranges rather than the WCAG floor — the theme for a reader who is not going to lean in.

| | |
|---|---|
| scenario | large-print handouts, low vision, projection in a bright room, twice-photocopied handouts |
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
    {"type":"rect","left":0,"top":0,"z":-10,"shape":{"width":640,"height":360},"style":{"fill":"#f7f7f7","stroke":"#636363","lineWidth":1}},
    {"type":"rect","left":42,"top":70,"z":-9,"shape":{"width":570,"height":228},"style":{"fill":"#ededed","stroke":"#636363","lineWidth":1}}
  ],
  "title": {
    "text": "Quarterly volume by channel",
    "subtext": "all eight categories, adjacent, on this theme’s own surface",
    "left": 14,
    "top": 10,
    "textStyle": {"color":"#000000","fontSize":15},
    "subtextStyle": {"color":"#424242","fontSize":11}
  },
  "color": ["#0b4fa8","#7a3400","#006b4f","#8c0e18","#5b2d9e","#0a6a6e","#a6105e","#4a4a4a"],
  "legend": {"bottom":6,"itemWidth":10,"itemHeight":10,"textStyle":{"color":"#000000","fontSize":10}},
  "grid": {"left":52,"right":18,"top":76,"bottom":52},
  "xAxis": {
    "type": "category",
    "data": ["Q1","Q2","Q3","Q4"],
    "axisLine": {"lineStyle":{"color":"#636363"}},
    "axisTick": {"lineStyle":{"color":"#636363"}},
    "axisLabel": {"color":"#424242"}
  },
  "yAxis": {"type":"value","axisLine":{"show":false},"axisLabel":{"color":"#424242"},"splitLine":{"lineStyle":{"color":"#636363"}}},
  "series": [
    {"name":"Direct","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#0b4fa8"},"data":[18,31,18,31]},
    {"name":"Partner","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#7a3400"},"data":[25,38,25,38]},
    {"name":"Search","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#006b4f"},"data":[32,19,32,19]},
    {"name":"Social","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#8c0e18"},"data":[39,26,39,26]},
    {"name":"Email","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#5b2d9e"},"data":[20,33,20,33]},
    {"name":"Referral","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#0a6a6e"},"data":[27,40,27,40]},
    {"name":"Events","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#a6105e"},"data":[34,21,34,21]},
    {
      "name": "Other",
      "type": "bar",
      "stack": "total",
      "barWidth": "52%",
      "itemStyle": {"color":"#4a4a4a"},
      "data": [41,28,41,28],
      "markLine": {
        "silent": true,
        "symbol": "none",
        "data": [
          {"yAxis":150,"lineStyle":{"type":"dashed","color":"#424242"},"label":{"color":"#424242","formatter":"target"}},
          {"yAxis":185,"lineStyle":{"type":"dotted","color":"#8c0e18"},"label":{"color":"#424242","formatter":"limit"}}
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
| `ink` | `#000000` | ✓ | – | – | – | `surface-*, tint-*` | body text inside fills, headings, node labels |
| `ink-soft` | `#313131` | ✓ | – | – | – | `page` | secondary body text on an unfilled background |
| `muted` | `#424242` | ✓ | – | – | – | `page` | captions, axes tick labels, metadata — never inside a tinted fill |
| `line` | `#636363` | – | ✓ | – | – | – | borders, edges, arrows, axes, rules |
| `line-strong` | `#313131` | – | ✓ | – | – | – | emphasis border, connector on a tinted fill |
| `surface-0` | `#f7f7f7` | – | – | ✓ | `#000000` | – | quietest container fill |
| `surface-1` | `#ededed` | – | – | ✓ | `#000000` | – | default shape / card fill |
| `surface-2` | `#dedede` | – | – | ✓ | `#000000` | – | nested or selected container fill |
| `cat-1` | `#0b4fa8` | ✓ | ✓ | ✓ | `#ffffff` | – | category 1 — also the accent colour |
| `cat-2` | `#7a3400` | ✓ | ✓ | ✓ | `#ffffff` | – | category 2 — marks and lines only |
| `cat-3` | `#006b4f` | ✓ | ✓ | ✓ | `#ffffff` | – | category 3 — fill only; the family is too light for text or lines in any theme |
| `cat-4` | `#8c0e18` | ✓ | ✓ | ✓ | `#ffffff` | – | category 4 |
| `cat-5` | `#5b2d9e` | ✓ | ✓ | ✓ | `#ffffff` | – | category 5 |
| `cat-6` | `#0a6a6e` | ✓ | ✓ | ✓ | `#ffffff` | – | category 6 — marks and lines only |
| `cat-7` | `#a6105e` | ✓ | ✓ | ✓ | `#ffffff` | – | category 7 — marks and lines only |
| `cat-8` | `#4a4a4a` | ✓ | ✓ | ✓ | `#ffffff` | – | category 8 |
| `positive` | `#006b4f` | ✓ | ✓ | ✓ | `#ffffff` | – | gains, passes, healthy state |
| `positive-ink` | `#006b4f` | ✓ | ✓ | – | – | `page` | positive text and deltas |
| `negative` | `#8c0e18` | ✓ | ✓ | ✓ | `#ffffff` | – | failures, regressions |
| `negative-ink` | `#7b0c15` | ✓ | ✓ | – | – | `page` | negative text and deltas — the family shade, granted the text role so a red chip can carry red words |
| `warning` | `#7a3400` | – | – | ✓ | – | – | warning fill / band |
| `warning-ink` | `#7a3400` | ✓ | ✓ | – | – | `page` | warning text and threshold lines |
| `target` | `#424242` | – | ✓ | – | – | – | dashed reference lines / goal markers |

## Derived colours

Computed from the token values, never hand-picked: `tint` = mix(`#ffffff`, family, 18 %),
`shade` = darken the family by 12 % (HSL lightness). The mix base is the theme's
**ground**, not a surface: mixing into a tinted near-white drags every hue towards the same
grey and the tints stop being tellable apart. A family has a shade only when this theme lets
it be a line — a family too light to be a line is too light to border its own fill, so it
takes the neutral `line` border instead.

| family | value | tint | shade | ink on tint |
|---|---|---|---|---|
| `cat-1` | `#0b4fa8` | `#d3dfef` | `#0a4694` | `#000000` |
| `cat-2` | `#7a3400` | `#e7dad1` | `#6b2e00` | `#000000` |
| `cat-3` | `#006b4f` | `#d1e4df` | `#005e46` | `#000000` |
| `cat-4` | `#8c0e18` | `#ead4d5` | `#7b0c15` | `#000000` |
| `cat-5` | `#5b2d9e` | `#e1d9ee` | `#50288b` | `#000000` |
| `cat-6` | `#0a6a6e` | `#d3e4e5` | `#095d61` | `#000000` |
| `cat-7` | `#a6105e` | `#efd4e2` | `#920e53` | `#000000` |
| `cat-8` | `#4a4a4a` | `#dedede` | `#414141` | `#000000` |
| `positive` | `#006b4f` | `#d1e4df` | `#005e46` | `#000000` |
| `negative` | `#8c0e18` | `#ead4d5` | `#7b0c15` | `#000000` |
| `warning` | `#7a3400` | `#e7dad1` | – | `#000000` |

## Blocks

Copy-paste blocks for this theme. Use exactly one block per figure; mixing blocks, or
adding a hex of your own on top, gives up the consistency the theme exists for.
Every value is literal — no alias layer, here or in any other theme.

### plantuml · structure

_structure, class, component, deployment._ One block per diagram. This is the UML family — `@startmindmap`, `@startgantt`, `@startpacketdiag` and `@startwbs` ignore `skinparam` entirely (measured: byte-identical output with and without it). `Package` carries two lines rather than three: `PackageFontColor` is a measured no-op.

```plantuml
skinparam RectangleBackgroundColor #ededed
skinparam RectangleBorderColor #636363
skinparam RectangleFontColor #000000
skinparam ComponentBackgroundColor #ededed
skinparam ComponentBorderColor #636363
skinparam ComponentFontColor #000000
skinparam ClassBackgroundColor #ededed
skinparam ClassBorderColor #636363
skinparam ClassFontColor #000000
skinparam UsecaseBackgroundColor #ededed
skinparam UsecaseBorderColor #636363
skinparam UsecaseFontColor #000000
skinparam DatabaseBackgroundColor #ededed
skinparam DatabaseBorderColor #636363
skinparam DatabaseFontColor #000000
skinparam NodeBackgroundColor #ededed
skinparam NodeBorderColor #636363
skinparam NodeFontColor #000000
skinparam ActorBackgroundColor #ededed
skinparam ActorBorderColor #636363
skinparam ActorFontColor #000000
skinparam StateBackgroundColor #ededed
skinparam StateBorderColor #636363
skinparam StateFontColor #000000
skinparam ArtifactBackgroundColor #ededed
skinparam ArtifactBorderColor #636363
skinparam ArtifactFontColor #000000
skinparam CloudBackgroundColor #ededed
skinparam CloudBorderColor #636363
skinparam CloudFontColor #000000
skinparam FolderBackgroundColor #ededed
skinparam FolderBorderColor #636363
skinparam FolderFontColor #000000
skinparam PackageBackgroundColor #ededed
skinparam PackageBorderColor #636363
skinparam DefaultFontColor #000000
skinparam ArrowColor #636363
skinparam ArrowFontColor #000000
skinparam NoteBackgroundColor #dedede
skinparam NoteBorderColor #636363
skinparam NoteFontColor #000000
skinparam stereotypeABackgroundColor #d3dfef
skinparam stereotypeABorderColor #636363
skinparam stereotypeCBackgroundColor #d3dfef
skinparam stereotypeCBorderColor #636363
skinparam stereotypeEBackgroundColor #d3dfef
skinparam stereotypeEBorderColor #636363
skinparam stereotypeIBackgroundColor #d3dfef
skinparam stereotypeIBorderColor #636363
```

### plantuml · sequence

_sequence._ Sequence diagrams take their own participant and lifeline keys; `ArrowColor` is shared with the structure block.

```plantuml
skinparam DefaultFontColor #000000
skinparam ArrowColor #636363
skinparam ArrowFontColor #000000
skinparam ParticipantBackgroundColor #ededed
skinparam ParticipantBorderColor #636363
skinparam ParticipantFontColor #000000
skinparam SequenceLifeLineBorderColor #636363
skinparam NoteBackgroundColor #dedede
skinparam NoteBorderColor #636363
skinparam NoteFontColor #000000
```

### plantuml · activity

_activity._ Activity steps take their own keys; the diamond is the decision node. A step can also be coloured on its own with `:step; <<#fill>>` — see the element block.

```plantuml
skinparam DefaultFontColor #000000
skinparam ArrowColor #636363
skinparam ArrowFontColor #000000
skinparam ActivityBackgroundColor #ededed
skinparam ActivityBorderColor #636363
skinparam ActivityDiamondBackgroundColor #dedede
```

### plantuml · element

_per-element colour._ When a block is not enough, colour one element. Use the **semicolon** form on every shape: `#fill;line:border`, with **no `#`** on the inner value. The `##` form is legal on the `class` family only — on a `rectangle`, official PlantUML does not error, it appends the suffix to the element name and falls back to an unparsed-colour fill, which is worse than a syntax error.

```plantuml
rectangle "Order service" as svc #d3dfef;line:0a4694
rectangle "Failed batch" as fail #ead4d5;line:7b0c15
```

### infographic · theme

_theme block._ Paste directly after the `infographic <template>` line, before `data`. `palette` must be a **list** — one `- #hex` per line; the space-separated form is a syntax error. Multi-colour templates read the ramp in order; single-colour templates ignore it and derive everything from `colorPrimary`, which is why one block serves all 113 templates.

```infographic
theme
  colorPrimary #0b4fa8
  palette
    - #0b4fa8
    - #7a3400
    - #006b4f
    - #8c0e18
    - #5b2d9e
    - #0a6a6e
    - #a6105e
    - #4a4a4a
```

### echarts · color

_colour ramp._ One line at the top level of every spec. Multi-series charts take one colour per series; a single series with coloured items (pie, sunburst, treemap, radar) takes one per data item; a plain single-series chart uses only the first. `itemStyle.color` on a series overrides this ramp.

```echarts
"color": ["#0b4fa8", "#7a3400", "#006b4f", "#8c0e18", "#5b2d9e", "#0a6a6e", "#a6105e", "#4a4a4a"]
```

### vega-lite · config

_config (Vega-Lite)._ Add as the first key of the spec. This sets the categorical range for every scale that does not declare its own.

```vega-lite
"config": { "range": { "category": ["#0b4fa8", "#7a3400", "#006b4f", "#8c0e18", "#5b2d9e", "#0a6a6e", "#a6105e", "#4a4a4a"] } }
```

### vega · scale

_ordinal colour scale (Vega)._ Rewrite the `range` of the ordinal colour scale the marks reference. Replace the `<dataset>` / `<category field>` placeholders with the real names. An explicit `scale.range` beats `config.range.category`, so a Vega spec must carry the ramp here.

```vega
{ "name": "color", "type": "ordinal", "domain": { "data": "<dataset>", "field": "<category field>" }, "range": ["#0b4fa8", "#7a3400", "#006b4f", "#8c0e18", "#5b2d9e", "#0a6a6e", "#a6105e", "#4a4a4a"] }
```

### html-css · card

_card._ Bare HTML card, coloured from the theme. The values are literal on purpose: documd-visuals does not follow the host document, so a card looks the same wherever it is pasted.

```css
.card {
  background: #ededed;
  border-left: 4px solid #0b4fa8;
  color: #000000;
}
.card .kicker { color: #0b4fa8; }
```

### html-css · badge

_badge._ A small status chip: the tint carries the fill, the shade the border, and `ink` the label.

```css
.badge {
  background: #d3dfef;
  color: #000000;
  border: 1px solid #0a4694;
}
```

## Verification

Every block above is rendered by the theme gate, which requires the declared values to land
and the engine defaults to be gone. The contrast gate recomputes every ratio in the token
table against this theme's ground. Both run per theme; see
[`../palette.md`](../palette.md) for the contract, and for the per-engine mechanism
[`../../engines/plantuml.md`](../../engines/plantuml.md) · [`../../engines/echarts.md`](../../engines/echarts.md) · [`../../engines/vega.md`](../../engines/vega.md) · [`../../engines/infographic.md`](../../engines/infographic.md) · [`../../engines/html-css.md`](../../engines/html-css.md).
