# Editorial theme

Warm cream ground, desaturated hues, and a deeper ink. Quieter than the default theme and warmer than white — the palette equivalent of a well-set page of prose. Category colour is muted on purpose: in editorial layouts it marks, it does not shout.

| | |
|---|---|
| scenario | long-form reading, memos, policy documents, print-ready reports on cream stock |
| ground | `#fdfaf3` |

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
    {"type":"rect","left":0,"top":0,"z":-10,"shape":{"width":640,"height":360},"style":{"fill":"#fbf8f1","stroke":"#8a7f6d","lineWidth":1}},
    {"type":"rect","left":42,"top":70,"z":-9,"shape":{"width":570,"height":228},"style":{"fill":"#f5f0e4","stroke":"#8a7f6d","lineWidth":1}}
  ],
  "title": {
    "text": "Quarterly volume by channel",
    "subtext": "all eight categories, adjacent, on this theme’s own surface",
    "left": 14,
    "top": 10,
    "textStyle": {"color":"#2b2620","fontSize":15},
    "subtextStyle": {"color":"#6f6659","fontSize":11}
  },
  "color": ["#2f5d8a","#4f7a52","#c9a227","#a8433f","#6b5b95","#3f7d78","#a86b7d","#7a6248"],
  "legend": {"bottom":6,"itemWidth":10,"itemHeight":10,"textStyle":{"color":"#2b2620","fontSize":10}},
  "grid": {"left":52,"right":18,"top":76,"bottom":52},
  "xAxis": {
    "type": "category",
    "data": ["Q1","Q2","Q3","Q4"],
    "axisLine": {"lineStyle":{"color":"#8a7f6d"}},
    "axisTick": {"lineStyle":{"color":"#8a7f6d"}},
    "axisLabel": {"color":"#6f6659"}
  },
  "yAxis": {"type":"value","axisLine":{"show":false},"axisLabel":{"color":"#6f6659"},"splitLine":{"lineStyle":{"color":"#8a7f6d"}}},
  "series": [
    {"name":"Direct","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#2f5d8a"},"data":[18,31,18,31]},
    {"name":"Partner","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#4f7a52"},"data":[25,38,25,38]},
    {"name":"Search","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#c9a227"},"data":[32,19,32,19]},
    {"name":"Social","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#a8433f"},"data":[39,26,39,26]},
    {"name":"Email","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#6b5b95"},"data":[20,33,20,33]},
    {"name":"Referral","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#3f7d78"},"data":[27,40,27,40]},
    {"name":"Events","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#a86b7d"},"data":[34,21,34,21]},
    {
      "name": "Other",
      "type": "bar",
      "stack": "total",
      "barWidth": "52%",
      "itemStyle": {"color":"#7a6248"},
      "data": [41,28,41,28],
      "markLine": {
        "silent": true,
        "symbol": "none",
        "data": [
          {"yAxis":150,"lineStyle":{"type":"dashed","color":"#8a7f6d"},"label":{"color":"#6f6659","formatter":"target"}},
          {"yAxis":185,"lineStyle":{"type":"dotted","color":"#a8433f"},"label":{"color":"#6f6659","formatter":"limit"}}
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
| `ink` | `#2b2620` | ✓ | – | – | – | `surface-*, tint-*` | body text inside fills, headings, node labels |
| `ink-soft` | `#554d42` | ✓ | – | – | – | `page` | secondary body text on an unfilled background |
| `muted` | `#6f6659` | ✓ | – | – | – | `page` | captions, axes tick labels, metadata — never inside a tinted fill |
| `line` | `#8a7f6d` | – | ✓ | – | – | – | borders, edges, arrows, axes, rules |
| `line-strong` | `#5b5245` | – | ✓ | – | – | – | emphasis border, connector on a tinted fill |
| `surface-0` | `#fbf8f1` | – | – | ✓ | `#2b2620` | – | quietest container fill |
| `surface-1` | `#f5f0e4` | – | – | ✓ | `#2b2620` | – | default shape / card fill |
| `surface-2` | `#ebe4d4` | – | – | ✓ | `#2b2620` | – | nested or selected container fill |
| `cat-1` | `#2f5d8a` | ✓ | ✓ | ✓ | `#ffffff` | – | category 1 — also the accent colour |
| `cat-2` | `#4f7a52` | – | ✓ | ✓ | – | – | category 2 — marks and lines only |
| `cat-3` | `#c9a227` | – | – | ✓ | – | – | category 3 — fill only; the family is too light for text or lines in any theme |
| `cat-4` | `#a8433f` | ✓ | ✓ | ✓ | `#ffffff` | – | category 4 |
| `cat-5` | `#6b5b95` | ✓ | ✓ | ✓ | `#ffffff` | – | category 5 |
| `cat-6` | `#3f7d78` | – | ✓ | ✓ | – | – | category 6 — marks and lines only |
| `cat-7` | `#a86b7d` | – | ✓ | ✓ | – | – | category 7 — marks and lines only |
| `cat-8` | `#7a6248` | ✓ | ✓ | ✓ | `#ffffff` | – | category 8 |
| `positive` | `#4f7a52` | – | ✓ | ✓ | – | – | gains, passes, healthy state |
| `positive-ink` | `#3d6340` | ✓ | ✓ | – | – | `page` | positive text and deltas |
| `negative` | `#a8433f` | ✓ | ✓ | ✓ | `#ffffff` | – | failures, regressions |
| `negative-ink` | `#943b37` | ✓ | ✓ | – | – | `page` | negative text and deltas — the family shade, granted the text role so a red chip can carry red words |
| `warning` | `#c9a227` | – | – | ✓ | – | – | warning fill / band |
| `warning-ink` | `#8a6b12` | ✓ | ✓ | – | – | `page` | warning text and threshold lines |
| `target` | `#8a7f6d` | – | ✓ | – | – | – | dashed reference lines / goal markers |

## Derived colours

Computed from the token values, never hand-picked: `tint` = mix(`#fdfaf3`, family, 18 %),
`shade` = darken the family by 12 % (HSL lightness). The mix base is the theme's
**ground**, not a surface: mixing into a tinted near-white drags every hue towards the same
grey and the tints stop being tellable apart. A family has a shade only when this theme lets
it be a line — a family too light to be a line is too light to border its own fill, so it
takes the neutral `line` border instead.

| family | value | tint | shade | ink on tint |
|---|---|---|---|---|
| `cat-1` | `#2f5d8a` | `#d8dee0` | `#295279` | `#2b2620` |
| `cat-2` | `#4f7a52` | `#dee3d6` | `#466b48` | `#2b2620` |
| `cat-3` | `#c9a227` | `#f4eace` | – | `#2b2620` |
| `cat-4` | `#a8433f` | `#eed9d3` | `#943b37` | `#2b2620` |
| `cat-5` | `#6b5b95` | `#e3dde2` | `#5e5083` | `#2b2620` |
| `cat-6` | `#3f7d78` | `#dbe4dd` | `#376e6a` | `#2b2620` |
| `cat-7` | `#a86b7d` | `#eee0de` | `#945e6e` | `#2b2620` |
| `cat-8` | `#7a6248` | `#e5dfd4` | `#6b563f` | `#2b2620` |
| `positive` | `#4f7a52` | `#dee3d6` | `#466b48` | `#2b2620` |
| `negative` | `#a8433f` | `#eed9d3` | `#943b37` | `#2b2620` |
| `warning` | `#c9a227` | `#f4eace` | – | `#2b2620` |

## Blocks

Copy-paste blocks for this theme. Use exactly one block per figure; mixing blocks, or
adding a hex of your own on top, gives up the consistency the theme exists for.
Every value is literal — no alias layer, here or in any other theme.

### plantuml · structure

_structure, class, component, deployment._ One block per diagram. This is the UML family — `@startmindmap`, `@startgantt`, `@startpacketdiag` and `@startwbs` ignore `skinparam` entirely (measured: byte-identical output with and without it). `Package` carries two lines rather than three: `PackageFontColor` is a measured no-op.

```plantuml
skinparam RectangleBackgroundColor #f5f0e4
skinparam RectangleBorderColor #8a7f6d
skinparam RectangleFontColor #2b2620
skinparam ComponentBackgroundColor #f5f0e4
skinparam ComponentBorderColor #8a7f6d
skinparam ComponentFontColor #2b2620
skinparam ClassBackgroundColor #f5f0e4
skinparam ClassBorderColor #8a7f6d
skinparam ClassFontColor #2b2620
skinparam UsecaseBackgroundColor #f5f0e4
skinparam UsecaseBorderColor #8a7f6d
skinparam UsecaseFontColor #2b2620
skinparam DatabaseBackgroundColor #f5f0e4
skinparam DatabaseBorderColor #8a7f6d
skinparam DatabaseFontColor #2b2620
skinparam NodeBackgroundColor #f5f0e4
skinparam NodeBorderColor #8a7f6d
skinparam NodeFontColor #2b2620
skinparam ActorBackgroundColor #f5f0e4
skinparam ActorBorderColor #8a7f6d
skinparam ActorFontColor #2b2620
skinparam StateBackgroundColor #f5f0e4
skinparam StateBorderColor #8a7f6d
skinparam StateFontColor #2b2620
skinparam ArtifactBackgroundColor #f5f0e4
skinparam ArtifactBorderColor #8a7f6d
skinparam ArtifactFontColor #2b2620
skinparam CloudBackgroundColor #f5f0e4
skinparam CloudBorderColor #8a7f6d
skinparam CloudFontColor #2b2620
skinparam FolderBackgroundColor #f5f0e4
skinparam FolderBorderColor #8a7f6d
skinparam FolderFontColor #2b2620
skinparam PackageBackgroundColor #f5f0e4
skinparam PackageBorderColor #8a7f6d
skinparam DefaultFontColor #2b2620
skinparam ArrowColor #8a7f6d
skinparam ArrowFontColor #2b2620
skinparam NoteBackgroundColor #ebe4d4
skinparam NoteBorderColor #8a7f6d
skinparam NoteFontColor #2b2620
skinparam stereotypeABackgroundColor #d8dee0
skinparam stereotypeABorderColor #8a7f6d
skinparam stereotypeCBackgroundColor #d8dee0
skinparam stereotypeCBorderColor #8a7f6d
skinparam stereotypeEBackgroundColor #d8dee0
skinparam stereotypeEBorderColor #8a7f6d
skinparam stereotypeIBackgroundColor #d8dee0
skinparam stereotypeIBorderColor #8a7f6d
```

### plantuml · sequence

_sequence._ Sequence diagrams take their own participant and lifeline keys; `ArrowColor` is shared with the structure block.

```plantuml
skinparam DefaultFontColor #2b2620
skinparam ArrowColor #8a7f6d
skinparam ArrowFontColor #2b2620
skinparam ParticipantBackgroundColor #f5f0e4
skinparam ParticipantBorderColor #8a7f6d
skinparam ParticipantFontColor #2b2620
skinparam SequenceLifeLineBorderColor #8a7f6d
skinparam NoteBackgroundColor #ebe4d4
skinparam NoteBorderColor #8a7f6d
skinparam NoteFontColor #2b2620
```

### plantuml · activity

_activity._ Activity steps take their own keys; the diamond is the decision node. A step can also be coloured on its own with `:step; <<#fill>>` — see the element block.

```plantuml
skinparam DefaultFontColor #2b2620
skinparam ArrowColor #8a7f6d
skinparam ArrowFontColor #2b2620
skinparam ActivityBackgroundColor #f5f0e4
skinparam ActivityBorderColor #8a7f6d
skinparam ActivityDiamondBackgroundColor #ebe4d4
```

### plantuml · element

_per-element colour._ When a block is not enough, colour one element. Use the **semicolon** form on every shape: `#fill;line:border`, with **no `#`** on the inner value. The `##` form is legal on the `class` family only — on a `rectangle`, official PlantUML does not error, it appends the suffix to the element name and falls back to an unparsed-colour fill, which is worse than a syntax error.

```plantuml
rectangle "Order service" as svc #d8dee0;line:295279
rectangle "Failed batch" as fail #eed9d3;line:943b37
```

### infographic · theme

_theme block._ Paste directly after the `infographic <template>` line, before `data`. `palette` must be a **list** — one `- #hex` per line; the space-separated form is a syntax error. Multi-colour templates read the ramp in order; single-colour templates ignore it and derive everything from `colorPrimary`, which is why one block serves all 113 templates.

```infographic
theme
  colorPrimary #2f5d8a
  palette
    - #2f5d8a
    - #4f7a52
    - #c9a227
    - #a8433f
    - #6b5b95
    - #3f7d78
    - #a86b7d
    - #7a6248
```

### echarts · color

_colour ramp._ One line at the top level of every spec. Multi-series charts take one colour per series; a single series with coloured items (pie, sunburst, treemap, radar) takes one per data item; a plain single-series chart uses only the first. `itemStyle.color` on a series overrides this ramp.

```echarts
"color": ["#2f5d8a", "#4f7a52", "#c9a227", "#a8433f", "#6b5b95", "#3f7d78", "#a86b7d", "#7a6248"]
```

### vega-lite · config

_config (Vega-Lite)._ Add as the first key of the spec. This sets the categorical range for every scale that does not declare its own.

```vega-lite
"config": { "range": { "category": ["#2f5d8a", "#4f7a52", "#c9a227", "#a8433f", "#6b5b95", "#3f7d78", "#a86b7d", "#7a6248"] } }
```

### vega · scale

_ordinal colour scale (Vega)._ Rewrite the `range` of the ordinal colour scale the marks reference. Replace the `<dataset>` / `<category field>` placeholders with the real names. An explicit `scale.range` beats `config.range.category`, so a Vega spec must carry the ramp here.

```vega
{ "name": "color", "type": "ordinal", "domain": { "data": "<dataset>", "field": "<category field>" }, "range": ["#2f5d8a", "#4f7a52", "#c9a227", "#a8433f", "#6b5b95", "#3f7d78", "#a86b7d", "#7a6248"] }
```

### html-css · card

_card._ Bare HTML card, coloured from the theme. The values are literal on purpose: documd-visuals does not follow the host document, so a card looks the same wherever it is pasted.

```css
.card {
  background: #f5f0e4;
  border-left: 4px solid #2f5d8a;
  color: #2b2620;
}
.card .kicker { color: #2f5d8a; }
```

### html-css · badge

_badge._ A small status chip: the tint carries the fill, the shade the border, and `ink` the label.

```css
.badge {
  background: #d8dee0;
  color: #2b2620;
  border: 1px solid #295279;
}
```

## Verification

Every block above is rendered by the theme gate, which requires the declared values to land
and the engine defaults to be gone. The contrast gate recomputes every ratio in the token
table against this theme's ground. Both run per theme; see
[`../palette.md`](../palette.md) for the contract, and for the per-engine mechanism
[`../../engines/plantuml.md`](../../engines/plantuml.md) · [`../../engines/echarts.md`](../../engines/echarts.md) · [`../../engines/vega.md`](../../engines/vega.md) · [`../../engines/infographic.md`](../../engines/infographic.md) · [`../../engines/html-css.md`](../../engines/html-css.md).
