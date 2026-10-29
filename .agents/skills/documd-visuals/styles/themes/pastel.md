# Pastel theme

Catppuccin’s light flavour as a document palette: a soft blue-grey page, low-contrast neutrals, and accents that stay quiet even at full chroma. Warmer and rounder than the default theme — for a figure that has to sit inside prose which is trying not to alarm anyone.

| | |
|---|---|
| scenario | onboarding, education, HR and internal comms, anything that should feel gentle |
| ground | `#eff1f5` |

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
    {"type":"rect","left":0,"top":0,"z":-10,"shape":{"width":640,"height":360},"style":{"fill":"#f6f7fa","stroke":"#797c95","lineWidth":1}},
    {"type":"rect","left":42,"top":70,"z":-9,"shape":{"width":570,"height":228},"style":{"fill":"#e6e9ef","stroke":"#797c95","lineWidth":1}}
  ],
  "title": {
    "text": "Quarterly volume by channel",
    "subtext": "all eight categories, adjacent, on this theme’s own surface",
    "left": 14,
    "top": 10,
    "textStyle": {"color":"#3b3d4a","fontSize":15},
    "subtextStyle": {"color":"#5d6077","fontSize":11}
  },
  "color": ["#1e66f5","#40a02b","#8a6a00","#d20f39","#8839ef","#179299","#ea76cb","#c04a1a"],
  "legend": {"bottom":6,"itemWidth":10,"itemHeight":10,"textStyle":{"color":"#3b3d4a","fontSize":10}},
  "grid": {"left":52,"right":18,"top":76,"bottom":52},
  "xAxis": {
    "type": "category",
    "data": ["Q1","Q2","Q3","Q4"],
    "axisLine": {"lineStyle":{"color":"#797c95"}},
    "axisTick": {"lineStyle":{"color":"#797c95"}},
    "axisLabel": {"color":"#5d6077"}
  },
  "yAxis": {"type":"value","axisLine":{"show":false},"axisLabel":{"color":"#5d6077"},"splitLine":{"lineStyle":{"color":"#797c95"}}},
  "series": [
    {"name":"Direct","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#1e66f5"},"data":[18,31,18,31]},
    {"name":"Partner","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#40a02b"},"data":[25,38,25,38]},
    {"name":"Search","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#8a6a00"},"data":[32,19,32,19]},
    {"name":"Social","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#d20f39"},"data":[39,26,39,26]},
    {"name":"Email","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#8839ef"},"data":[20,33,20,33]},
    {"name":"Referral","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#179299"},"data":[27,40,27,40]},
    {"name":"Events","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#ea76cb"},"data":[34,21,34,21]},
    {
      "name": "Other",
      "type": "bar",
      "stack": "total",
      "barWidth": "52%",
      "itemStyle": {"color":"#c04a1a"},
      "data": [41,28,41,28],
      "markLine": {
        "silent": true,
        "symbol": "none",
        "data": [
          {"yAxis":150,"lineStyle":{"type":"dashed","color":"#5d6077"},"label":{"color":"#5d6077","formatter":"target"}},
          {"yAxis":185,"lineStyle":{"type":"dotted","color":"#d20f39"},"label":{"color":"#5d6077","formatter":"limit"}}
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
| `ink` | `#3b3d4a` | ✓ | – | – | – | `surface-*, tint-*` | body text inside fills, headings, node labels |
| `ink-soft` | `#4c4e60` | ✓ | – | – | – | `page` | secondary body text on an unfilled background |
| `muted` | `#5d6077` | ✓ | – | – | – | `page` | captions, axes tick labels, metadata — never inside a tinted fill |
| `line` | `#797c95` | – | ✓ | – | – | – | borders, edges, arrows, axes, rules |
| `line-strong` | `#525468` | – | ✓ | – | – | – | emphasis border, connector on a tinted fill |
| `surface-0` | `#f6f7fa` | – | – | ✓ | `#3b3d4a` | – | quietest container fill |
| `surface-1` | `#e6e9ef` | – | – | ✓ | `#3b3d4a` | – | default shape / card fill |
| `surface-2` | `#dce0e8` | – | – | ✓ | `#3b3d4a` | – | nested or selected container fill |
| `cat-1` | `#1e66f5` | – | ✓ | ✓ | – | – | category 1 — also the accent colour |
| `cat-2` | `#40a02b` | – | – | ✓ | – | – | category 2 — marks and lines only |
| `cat-3` | `#8a6a00` | – | ✓ | ✓ | – | – | category 3 — fill only; the family is too light for text or lines in any theme |
| `cat-4` | `#d20f39` | ✓ | ✓ | ✓ | `#ffffff` | – | category 4 |
| `cat-5` | `#8839ef` | ✓ | ✓ | ✓ | `#ffffff` | – | category 5 |
| `cat-6` | `#179299` | – | ✓ | ✓ | – | – | category 6 — marks and lines only |
| `cat-7` | `#ea76cb` | – | – | ✓ | – | – | category 7 — marks and lines only |
| `cat-8` | `#c04a1a` | – | ✓ | ✓ | – | – | category 8 |
| `positive` | `#40a02b` | – | – | ✓ | – | – | gains, passes, healthy state |
| `positive-ink` | `#347c1f` | ✓ | ✓ | – | – | `page` | positive text and deltas |
| `negative` | `#d20f39` | ✓ | ✓ | ✓ | `#ffffff` | – | failures, regressions |
| `negative-ink` | `#b90d32` | ✓ | ✓ | – | – | `page` | negative text and deltas — the family shade, granted the text role so a red chip can carry red words |
| `warning` | `#8a6a00` | – | – | ✓ | – | – | warning fill / band |
| `warning-ink` | `#876800` | ✓ | ✓ | – | – | `page` | warning text and threshold lines |
| `target` | `#5d6077` | – | ✓ | – | – | – | dashed reference lines / goal markers |

## Derived colours

Computed from the token values, never hand-picked: `tint` = mix(`#eff1f5`, family, 18 %),
`shade` = darken the family by 12 % (HSL lightness). The mix base is the theme's
**ground**, not a surface: mixing into a tinted near-white drags every hue towards the same
grey and the tints stop being tellable apart. A family has a shade only when this theme lets
it be a line — a family too light to be a line is too light to border its own fill, so it
takes the neutral `line` border instead.

| family | value | tint | shade | ink on tint |
|---|---|---|---|---|
| `cat-1` | `#1e66f5` | `#c9d8f5` | `#1a5ad8` | `#3b3d4a` |
| `cat-2` | `#40a02b` | `#d0e2d1` | – | `#3b3d4a` |
| `cat-3` | `#8a6a00` | `#ddd9c9` | `#795d00` | `#3b3d4a` |
| `cat-4` | `#d20f39` | `#eac8d3` | `#b90d32` | `#3b3d4a` |
| `cat-5` | `#8839ef` | `#dcd0f4` | `#7418ec` | `#3b3d4a` |
| `cat-6` | `#179299` | `#c8e0e4` | `#148087` | `#3b3d4a` |
| `cat-7` | `#ea76cb` | `#eedbed` | – | `#3b3d4a` |
| `cat-8` | `#c04a1a` | `#e7d3ce` | `#a94117` | `#3b3d4a` |
| `positive` | `#40a02b` | `#d0e2d1` | – | `#3b3d4a` |
| `negative` | `#d20f39` | `#eac8d3` | `#b90d32` | `#3b3d4a` |
| `warning` | `#8a6a00` | `#ddd9c9` | – | `#3b3d4a` |

## Blocks

Copy-paste blocks for this theme. Use exactly one block per figure; mixing blocks, or
adding a hex of your own on top, gives up the consistency the theme exists for.
Every value is literal — no alias layer, here or in any other theme.

### plantuml · structure

_structure, class, component, deployment._ One block per diagram. This is the UML family — `@startmindmap`, `@startgantt`, `@startpacketdiag` and `@startwbs` ignore `skinparam` entirely (measured: byte-identical output with and without it). `Package` carries two lines rather than three: `PackageFontColor` is a measured no-op.

```plantuml
skinparam RectangleBackgroundColor #e6e9ef
skinparam RectangleBorderColor #797c95
skinparam RectangleFontColor #3b3d4a
skinparam ComponentBackgroundColor #e6e9ef
skinparam ComponentBorderColor #797c95
skinparam ComponentFontColor #3b3d4a
skinparam ClassBackgroundColor #e6e9ef
skinparam ClassBorderColor #797c95
skinparam ClassFontColor #3b3d4a
skinparam UsecaseBackgroundColor #e6e9ef
skinparam UsecaseBorderColor #797c95
skinparam UsecaseFontColor #3b3d4a
skinparam DatabaseBackgroundColor #e6e9ef
skinparam DatabaseBorderColor #797c95
skinparam DatabaseFontColor #3b3d4a
skinparam NodeBackgroundColor #e6e9ef
skinparam NodeBorderColor #797c95
skinparam NodeFontColor #3b3d4a
skinparam ActorBackgroundColor #e6e9ef
skinparam ActorBorderColor #797c95
skinparam ActorFontColor #3b3d4a
skinparam StateBackgroundColor #e6e9ef
skinparam StateBorderColor #797c95
skinparam StateFontColor #3b3d4a
skinparam ArtifactBackgroundColor #e6e9ef
skinparam ArtifactBorderColor #797c95
skinparam ArtifactFontColor #3b3d4a
skinparam CloudBackgroundColor #e6e9ef
skinparam CloudBorderColor #797c95
skinparam CloudFontColor #3b3d4a
skinparam FolderBackgroundColor #e6e9ef
skinparam FolderBorderColor #797c95
skinparam FolderFontColor #3b3d4a
skinparam PackageBackgroundColor #e6e9ef
skinparam PackageBorderColor #797c95
skinparam DefaultFontColor #3b3d4a
skinparam ArrowColor #797c95
skinparam ArrowFontColor #3b3d4a
skinparam NoteBackgroundColor #dce0e8
skinparam NoteBorderColor #797c95
skinparam NoteFontColor #3b3d4a
skinparam stereotypeABackgroundColor #c9d8f5
skinparam stereotypeABorderColor #797c95
skinparam stereotypeCBackgroundColor #c9d8f5
skinparam stereotypeCBorderColor #797c95
skinparam stereotypeEBackgroundColor #c9d8f5
skinparam stereotypeEBorderColor #797c95
skinparam stereotypeIBackgroundColor #c9d8f5
skinparam stereotypeIBorderColor #797c95
```

### plantuml · sequence

_sequence._ Sequence diagrams take their own participant and lifeline keys; `ArrowColor` is shared with the structure block.

```plantuml
skinparam DefaultFontColor #3b3d4a
skinparam ArrowColor #797c95
skinparam ArrowFontColor #3b3d4a
skinparam ParticipantBackgroundColor #e6e9ef
skinparam ParticipantBorderColor #797c95
skinparam ParticipantFontColor #3b3d4a
skinparam SequenceLifeLineBorderColor #797c95
skinparam NoteBackgroundColor #dce0e8
skinparam NoteBorderColor #797c95
skinparam NoteFontColor #3b3d4a
```

### plantuml · activity

_activity._ Activity steps take their own keys; the diamond is the decision node. A step can also be coloured on its own with `:step; <<#fill>>` — see the element block.

```plantuml
skinparam DefaultFontColor #3b3d4a
skinparam ArrowColor #797c95
skinparam ArrowFontColor #3b3d4a
skinparam ActivityBackgroundColor #e6e9ef
skinparam ActivityBorderColor #797c95
skinparam ActivityDiamondBackgroundColor #dce0e8
```

### plantuml · element

_per-element colour._ When a block is not enough, colour one element. Use the **semicolon** form on every shape: `#fill;line:border`, with **no `#`** on the inner value. The `##` form is legal on the `class` family only — on a `rectangle`, official PlantUML does not error, it appends the suffix to the element name and falls back to an unparsed-colour fill, which is worse than a syntax error.

```plantuml
rectangle "Order service" as svc #c9d8f5;line:1a5ad8
rectangle "Failed batch" as fail #eac8d3;line:b90d32
```

### infographic · theme

_theme block._ Paste directly after the `infographic <template>` line, before `data`. `palette` must be a **list** — one `- #hex` per line; the space-separated form is a syntax error. Multi-colour templates read the ramp in order; single-colour templates ignore it and derive everything from `colorPrimary`, which is why one block serves all 113 templates.

```infographic
theme
  colorPrimary #1e66f5
  palette
    - #1e66f5
    - #40a02b
    - #8a6a00
    - #d20f39
    - #8839ef
    - #179299
    - #ea76cb
    - #c04a1a
```

### echarts · color

_colour ramp._ One line at the top level of every spec. Multi-series charts take one colour per series; a single series with coloured items (pie, sunburst, treemap, radar) takes one per data item; a plain single-series chart uses only the first. `itemStyle.color` on a series overrides this ramp.

```echarts
"color": ["#1e66f5", "#40a02b", "#8a6a00", "#d20f39", "#8839ef", "#179299", "#ea76cb", "#c04a1a"]
```

### vega-lite · config

_config (Vega-Lite)._ Add as the first key of the spec. This sets the categorical range for every scale that does not declare its own.

```vega-lite
"config": { "range": { "category": ["#1e66f5", "#40a02b", "#8a6a00", "#d20f39", "#8839ef", "#179299", "#ea76cb", "#c04a1a"] } }
```

### vega · scale

_ordinal colour scale (Vega)._ Rewrite the `range` of the ordinal colour scale the marks reference. Replace the `<dataset>` / `<category field>` placeholders with the real names. An explicit `scale.range` beats `config.range.category`, so a Vega spec must carry the ramp here.

```vega
{ "name": "color", "type": "ordinal", "domain": { "data": "<dataset>", "field": "<category field>" }, "range": ["#1e66f5", "#40a02b", "#8a6a00", "#d20f39", "#8839ef", "#179299", "#ea76cb", "#c04a1a"] }
```

### html-css · card

_card._ Bare HTML card, coloured from the theme. The values are literal on purpose: documd-visuals does not follow the host document, so a card looks the same wherever it is pasted.

```css
.card {
  background: #e6e9ef;
  border-left: 4px solid #1e66f5;
  color: #3b3d4a;
}
.card .kicker { color: #1e66f5; }
```

### html-css · badge

_badge._ A small status chip: the tint carries the fill, the shade the border, and `ink` the label.

```css
.badge {
  background: #c9d8f5;
  color: #3b3d4a;
  border: 1px solid #1a5ad8;
}
```

## Verification

Every block above is rendered by the theme gate, which requires the declared values to land
and the engine defaults to be gone. The contrast gate recomputes every ratio in the token
table against this theme's ground. Both run per theme; see
[`../palette.md`](../palette.md) for the contract, and for the per-engine mechanism
[`../../engines/plantuml.md`](../../engines/plantuml.md) · [`../../engines/echarts.md`](../../engines/echarts.md) · [`../../engines/vega.md`](../../engines/vega.md) · [`../../engines/infographic.md`](../../engines/infographic.md) · [`../../engines/html-css.md`](../../engines/html-css.md).
