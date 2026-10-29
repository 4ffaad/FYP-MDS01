# Slate theme

The IBM Carbon Gray 10 theme read as a figure palette: a neutral grey page, grey-scale layering for containers, and one blue that carries the accent. Category colour is used in the Carbon register — enough to separate series, never enough to decorate.

| | |
|---|---|
| scenario | technical documentation, dashboards, API and infra references, internal wikis |
| ground | `#f4f4f4` |

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
    {"type":"rect","left":0,"top":0,"z":-10,"shape":{"width":640,"height":360},"style":{"fill":"#fbfbfb","stroke":"#787878","lineWidth":1}},
    {"type":"rect","left":42,"top":70,"z":-9,"shape":{"width":570,"height":228},"style":{"fill":"#ffffff","stroke":"#787878","lineWidth":1}}
  ],
  "title": {
    "text": "Quarterly volume by channel",
    "subtext": "all eight categories, adjacent, on this theme’s own surface",
    "left": 14,
    "top": 10,
    "textStyle": {"color":"#1e1e1e","fontSize":15},
    "subtextStyle": {"color":"#565656","fontSize":11}
  },
  "color": ["#0043ce","#0e6027","#750e13","#6929c4","#004f4f","#9f1853","#525252","#8e6a00"],
  "legend": {"bottom":6,"itemWidth":10,"itemHeight":10,"textStyle":{"color":"#1e1e1e","fontSize":10}},
  "grid": {"left":52,"right":18,"top":76,"bottom":52},
  "xAxis": {
    "type": "category",
    "data": ["Q1","Q2","Q3","Q4"],
    "axisLine": {"lineStyle":{"color":"#787878"}},
    "axisTick": {"lineStyle":{"color":"#787878"}},
    "axisLabel": {"color":"#565656"}
  },
  "yAxis": {"type":"value","axisLine":{"show":false},"axisLabel":{"color":"#565656"},"splitLine":{"lineStyle":{"color":"#787878"}}},
  "series": [
    {"name":"Direct","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#0043ce"},"data":[18,31,18,31]},
    {"name":"Partner","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#0e6027"},"data":[25,38,25,38]},
    {"name":"Search","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#750e13"},"data":[32,19,32,19]},
    {"name":"Social","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#6929c4"},"data":[39,26,39,26]},
    {"name":"Email","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#004f4f"},"data":[20,33,20,33]},
    {"name":"Referral","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#9f1853"},"data":[27,40,27,40]},
    {"name":"Events","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#525252"},"data":[34,21,34,21]},
    {
      "name": "Other",
      "type": "bar",
      "stack": "total",
      "barWidth": "52%",
      "itemStyle": {"color":"#8e6a00"},
      "data": [41,28,41,28],
      "markLine": {
        "silent": true,
        "symbol": "none",
        "data": [
          {"yAxis":150,"lineStyle":{"type":"dashed","color":"#565656"},"label":{"color":"#565656","formatter":"target"}},
          {"yAxis":185,"lineStyle":{"type":"dotted","color":"#750e13"},"label":{"color":"#565656","formatter":"limit"}}
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
| `ink` | `#1e1e1e` | ✓ | – | – | – | `surface-*, tint-*` | body text inside fills, headings, node labels |
| `ink-soft` | `#3f3f3f` | ✓ | – | – | – | `page` | secondary body text on an unfilled background |
| `muted` | `#565656` | ✓ | – | – | – | `page` | captions, axes tick labels, metadata — never inside a tinted fill |
| `line` | `#787878` | – | ✓ | – | – | – | borders, edges, arrows, axes, rules |
| `line-strong` | `#4a4a4a` | – | ✓ | – | – | – | emphasis border, connector on a tinted fill |
| `surface-0` | `#fbfbfb` | – | – | ✓ | `#1e1e1e` | – | quietest container fill |
| `surface-1` | `#ffffff` | – | – | ✓ | `#1e1e1e` | – | default shape / card fill |
| `surface-2` | `#e8e8e8` | – | – | ✓ | `#1e1e1e` | – | nested or selected container fill |
| `cat-1` | `#0043ce` | ✓ | ✓ | ✓ | `#ffffff` | – | category 1 — also the accent colour |
| `cat-2` | `#0e6027` | ✓ | ✓ | ✓ | `#ffffff` | – | category 2 — marks and lines only |
| `cat-3` | `#750e13` | ✓ | ✓ | ✓ | `#ffffff` | – | category 3 — fill only; the family is too light for text or lines in any theme |
| `cat-4` | `#6929c4` | ✓ | ✓ | ✓ | `#ffffff` | – | category 4 |
| `cat-5` | `#004f4f` | ✓ | ✓ | ✓ | `#ffffff` | – | category 5 |
| `cat-6` | `#9f1853` | ✓ | ✓ | ✓ | `#ffffff` | – | category 6 — marks and lines only |
| `cat-7` | `#525252` | ✓ | ✓ | ✓ | `#ffffff` | – | category 7 — marks and lines only |
| `cat-8` | `#8e6a00` | ✓ | ✓ | ✓ | `#ffffff` | – | category 8 |
| `positive` | `#0e6027` | ✓ | ✓ | ✓ | `#ffffff` | – | gains, passes, healthy state |
| `positive-ink` | `#0e6027` | ✓ | ✓ | – | – | `page` | positive text and deltas |
| `negative` | `#750e13` | ✓ | ✓ | ✓ | `#ffffff` | – | failures, regressions |
| `negative-ink` | `#670c11` | ✓ | ✓ | – | – | `page` | negative text and deltas — the family shade, granted the text role so a red chip can carry red words |
| `warning` | `#8e6a00` | – | – | ✓ | – | – | warning fill / band |
| `warning-ink` | `#8e6a00` | ✓ | ✓ | – | – | `page` | warning text and threshold lines |
| `target` | `#565656` | – | ✓ | – | – | – | dashed reference lines / goal markers |

## Derived colours

Computed from the token values, never hand-picked: `tint` = mix(`#f4f4f4`, family, 18 %),
`shade` = darken the family by 12 % (HSL lightness). The mix base is the theme's
**ground**, not a surface: mixing into a tinted near-white drags every hue towards the same
grey and the tints stop being tellable apart. A family has a shade only when this theme lets
it be a line — a family too light to be a line is too light to border its own fill, so it
takes the neutral `line` border instead.

| family | value | tint | shade | ink on tint |
|---|---|---|---|---|
| `cat-1` | `#0043ce` | `#c8d4ed` | `#003bb5` | `#1e1e1e` |
| `cat-2` | `#0e6027` | `#cbd9cf` | `#0c5422` | `#1e1e1e` |
| `cat-3` | `#750e13` | `#ddcbcc` | `#670c11` | `#1e1e1e` |
| `cat-4` | `#6929c4` | `#dbcfeb` | `#5c24ac` | `#1e1e1e` |
| `cat-5` | `#004f4f` | `#c8d6d6` | `#004646` | `#1e1e1e` |
| `cat-6` | `#9f1853` | `#e5ccd7` | `#8c1549` | `#1e1e1e` |
| `cat-7` | `#525252` | `#d7d7d7` | `#484848` | `#1e1e1e` |
| `cat-8` | `#8e6a00` | `#e2dbc8` | `#7d5d00` | `#1e1e1e` |
| `positive` | `#0e6027` | `#cbd9cf` | `#0c5422` | `#1e1e1e` |
| `negative` | `#750e13` | `#ddcbcc` | `#670c11` | `#1e1e1e` |
| `warning` | `#8e6a00` | `#e2dbc8` | – | `#1e1e1e` |

## Blocks

Copy-paste blocks for this theme. Use exactly one block per figure; mixing blocks, or
adding a hex of your own on top, gives up the consistency the theme exists for.
Every value is literal — no alias layer, here or in any other theme.

### plantuml · structure

_structure, class, component, deployment._ One block per diagram. This is the UML family — `@startmindmap`, `@startgantt`, `@startpacketdiag` and `@startwbs` ignore `skinparam` entirely (measured: byte-identical output with and without it). `Package` carries two lines rather than three: `PackageFontColor` is a measured no-op.

```plantuml
skinparam RectangleBackgroundColor #ffffff
skinparam RectangleBorderColor #787878
skinparam RectangleFontColor #1e1e1e
skinparam ComponentBackgroundColor #ffffff
skinparam ComponentBorderColor #787878
skinparam ComponentFontColor #1e1e1e
skinparam ClassBackgroundColor #ffffff
skinparam ClassBorderColor #787878
skinparam ClassFontColor #1e1e1e
skinparam UsecaseBackgroundColor #ffffff
skinparam UsecaseBorderColor #787878
skinparam UsecaseFontColor #1e1e1e
skinparam DatabaseBackgroundColor #ffffff
skinparam DatabaseBorderColor #787878
skinparam DatabaseFontColor #1e1e1e
skinparam NodeBackgroundColor #ffffff
skinparam NodeBorderColor #787878
skinparam NodeFontColor #1e1e1e
skinparam ActorBackgroundColor #ffffff
skinparam ActorBorderColor #787878
skinparam ActorFontColor #1e1e1e
skinparam StateBackgroundColor #ffffff
skinparam StateBorderColor #787878
skinparam StateFontColor #1e1e1e
skinparam ArtifactBackgroundColor #ffffff
skinparam ArtifactBorderColor #787878
skinparam ArtifactFontColor #1e1e1e
skinparam CloudBackgroundColor #ffffff
skinparam CloudBorderColor #787878
skinparam CloudFontColor #1e1e1e
skinparam FolderBackgroundColor #ffffff
skinparam FolderBorderColor #787878
skinparam FolderFontColor #1e1e1e
skinparam PackageBackgroundColor #ffffff
skinparam PackageBorderColor #787878
skinparam DefaultFontColor #1e1e1e
skinparam ArrowColor #787878
skinparam ArrowFontColor #1e1e1e
skinparam NoteBackgroundColor #e8e8e8
skinparam NoteBorderColor #787878
skinparam NoteFontColor #1e1e1e
skinparam stereotypeABackgroundColor #c8d4ed
skinparam stereotypeABorderColor #787878
skinparam stereotypeCBackgroundColor #c8d4ed
skinparam stereotypeCBorderColor #787878
skinparam stereotypeEBackgroundColor #c8d4ed
skinparam stereotypeEBorderColor #787878
skinparam stereotypeIBackgroundColor #c8d4ed
skinparam stereotypeIBorderColor #787878
```

### plantuml · sequence

_sequence._ Sequence diagrams take their own participant and lifeline keys; `ArrowColor` is shared with the structure block.

```plantuml
skinparam DefaultFontColor #1e1e1e
skinparam ArrowColor #787878
skinparam ArrowFontColor #1e1e1e
skinparam ParticipantBackgroundColor #ffffff
skinparam ParticipantBorderColor #787878
skinparam ParticipantFontColor #1e1e1e
skinparam SequenceLifeLineBorderColor #787878
skinparam NoteBackgroundColor #e8e8e8
skinparam NoteBorderColor #787878
skinparam NoteFontColor #1e1e1e
```

### plantuml · activity

_activity._ Activity steps take their own keys; the diamond is the decision node. A step can also be coloured on its own with `:step; <<#fill>>` — see the element block.

```plantuml
skinparam DefaultFontColor #1e1e1e
skinparam ArrowColor #787878
skinparam ArrowFontColor #1e1e1e
skinparam ActivityBackgroundColor #ffffff
skinparam ActivityBorderColor #787878
skinparam ActivityDiamondBackgroundColor #e8e8e8
```

### plantuml · element

_per-element colour._ When a block is not enough, colour one element. Use the **semicolon** form on every shape: `#fill;line:border`, with **no `#`** on the inner value. The `##` form is legal on the `class` family only — on a `rectangle`, official PlantUML does not error, it appends the suffix to the element name and falls back to an unparsed-colour fill, which is worse than a syntax error.

```plantuml
rectangle "Order service" as svc #c8d4ed;line:003bb5
rectangle "Failed batch" as fail #dbcfeb;line:5c24ac
```

### infographic · theme

_theme block._ Paste directly after the `infographic <template>` line, before `data`. `palette` must be a **list** — one `- #hex` per line; the space-separated form is a syntax error. Multi-colour templates read the ramp in order; single-colour templates ignore it and derive everything from `colorPrimary`, which is why one block serves all 113 templates.

```infographic
theme
  colorPrimary #0043ce
  palette
    - #0043ce
    - #0e6027
    - #750e13
    - #6929c4
    - #004f4f
    - #9f1853
    - #525252
    - #8e6a00
```

### echarts · color

_colour ramp._ One line at the top level of every spec. Multi-series charts take one colour per series; a single series with coloured items (pie, sunburst, treemap, radar) takes one per data item; a plain single-series chart uses only the first. `itemStyle.color` on a series overrides this ramp.

```echarts
"color": ["#0043ce", "#0e6027", "#750e13", "#6929c4", "#004f4f", "#9f1853", "#525252", "#8e6a00"]
```

### vega-lite · config

_config (Vega-Lite)._ Add as the first key of the spec. This sets the categorical range for every scale that does not declare its own.

```vega-lite
"config": { "range": { "category": ["#0043ce", "#0e6027", "#750e13", "#6929c4", "#004f4f", "#9f1853", "#525252", "#8e6a00"] } }
```

### vega · scale

_ordinal colour scale (Vega)._ Rewrite the `range` of the ordinal colour scale the marks reference. Replace the `<dataset>` / `<category field>` placeholders with the real names. An explicit `scale.range` beats `config.range.category`, so a Vega spec must carry the ramp here.

```vega
{ "name": "color", "type": "ordinal", "domain": { "data": "<dataset>", "field": "<category field>" }, "range": ["#0043ce", "#0e6027", "#750e13", "#6929c4", "#004f4f", "#9f1853", "#525252", "#8e6a00"] }
```

### html-css · card

_card._ Bare HTML card, coloured from the theme. The values are literal on purpose: documd-visuals does not follow the host document, so a card looks the same wherever it is pasted.

```css
.card {
  background: #ffffff;
  border-left: 4px solid #0043ce;
  color: #1e1e1e;
}
.card .kicker { color: #0043ce; }
```

### html-css · badge

_badge._ A small status chip: the tint carries the fill, the shade the border, and `ink` the label.

```css
.badge {
  background: #c8d4ed;
  color: #1e1e1e;
  border: 1px solid #003bb5;
}
```

## Verification

Every block above is rendered by the theme gate, which requires the declared values to land
and the engine defaults to be gone. The contrast gate recomputes every ratio in the token
table against this theme's ground. Both run per theme; see
[`../palette.md`](../palette.md) for the contract, and for the per-engine mechanism
[`../../engines/plantuml.md`](../../engines/plantuml.md) · [`../../engines/echarts.md`](../../engines/echarts.md) · [`../../engines/vega.md`](../../engines/vega.md) · [`../../engines/infographic.md`](../../engines/infographic.md) · [`../../engines/html-css.md`](../../engines/html-css.md).
