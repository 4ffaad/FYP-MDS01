# Accessible theme

The Okabe–Ito Colour Universal Design set, ordered warm/cool alternating as the CUD guidance prescribes, with the darker blue and orange it recommends for thin marks. Red-versus-green is never the only difference between two categories. Members too light to clear 3.0 on white are declared fill-only, exactly as the CUD page advises — label outside the fill rather than thin the colour into a line.

| | |
|---|---|
| scenario | colour-critical figures, charts read by colour-blind readers, screen-and-print pairs |
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
    {"type":"rect","left":0,"top":0,"z":-10,"shape":{"width":640,"height":360},"style":{"fill":"#fbfcfe","stroke":"#737a8a","lineWidth":1}},
    {"type":"rect","left":42,"top":70,"z":-9,"shape":{"width":570,"height":228},"style":{"fill":"#f4f6fa","stroke":"#737a8a","lineWidth":1}}
  ],
  "title": {
    "text": "Quarterly volume by channel",
    "subtext": "all eight categories, adjacent, on this theme’s own surface",
    "left": 14,
    "top": 10,
    "textStyle": {"color":"#292c31","fontSize":15},
    "subtextStyle": {"color":"#575d69","fontSize":11}
  },
  "color": ["#0072b2","#e69f00","#009e73","#d55e00","#56b4e9","#f0e442","#cc79a7","#6e6e6e"],
  "legend": {"bottom":6,"itemWidth":10,"itemHeight":10,"textStyle":{"color":"#292c31","fontSize":10}},
  "grid": {"left":52,"right":18,"top":76,"bottom":52},
  "xAxis": {
    "type": "category",
    "data": ["Q1","Q2","Q3","Q4"],
    "axisLine": {"lineStyle":{"color":"#737a8a"}},
    "axisTick": {"lineStyle":{"color":"#737a8a"}},
    "axisLabel": {"color":"#575d69"}
  },
  "yAxis": {"type":"value","axisLine":{"show":false},"axisLabel":{"color":"#575d69"},"splitLine":{"lineStyle":{"color":"#737a8a"}}},
  "series": [
    {"name":"Direct","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#0072b2"},"data":[18,31,18,31]},
    {"name":"Partner","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#e69f00"},"data":[25,38,25,38]},
    {"name":"Search","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#009e73"},"data":[32,19,32,19]},
    {"name":"Social","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#d55e00"},"data":[39,26,39,26]},
    {"name":"Email","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#56b4e9"},"data":[20,33,20,33]},
    {"name":"Referral","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#f0e442"},"data":[27,40,27,40]},
    {"name":"Events","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#cc79a7"},"data":[34,21,34,21]},
    {
      "name": "Other",
      "type": "bar",
      "stack": "total",
      "barWidth": "52%",
      "itemStyle": {"color":"#6e6e6e"},
      "data": [41,28,41,28],
      "markLine": {
        "silent": true,
        "symbol": "none",
        "data": [
          {"yAxis":150,"lineStyle":{"type":"dashed","color":"#575d69"},"label":{"color":"#575d69","formatter":"target"}},
          {"yAxis":185,"lineStyle":{"type":"dotted","color":"#d55e00"},"label":{"color":"#575d69","formatter":"limit"}}
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
| `ink` | `#292c31` | ✓ | – | – | – | `surface-*, tint-*` | body text inside fills, headings, node labels |
| `ink-soft` | `#454953` | ✓ | – | – | – | `page` | secondary body text on an unfilled background |
| `muted` | `#575d69` | ✓ | – | – | – | `page` | captions, axes tick labels, metadata — never inside a tinted fill |
| `line` | `#737a8a` | – | ✓ | – | – | – | borders, edges, arrows, axes, rules |
| `line-strong` | `#4c505a` | – | ✓ | – | – | – | emphasis border, connector on a tinted fill |
| `surface-0` | `#fbfcfe` | – | – | ✓ | `#292c31` | – | quietest container fill |
| `surface-1` | `#f4f6fa` | – | – | ✓ | `#292c31` | – | default shape / card fill |
| `surface-2` | `#e9edf4` | – | – | ✓ | `#292c31` | – | nested or selected container fill |
| `cat-1` | `#0072b2` | ✓ | ✓ | ✓ | `#ffffff` | – | category 1 — also the accent colour |
| `cat-2` | `#e69f00` | – | – | ✓ | – | – | category 2 — marks and lines only |
| `cat-3` | `#009e73` | – | ✓ | ✓ | – | – | category 3 — fill only; the family is too light for text or lines in any theme |
| `cat-4` | `#d55e00` | – | ✓ | ✓ | – | – | category 4 |
| `cat-5` | `#56b4e9` | – | – | ✓ | – | – | category 5 |
| `cat-6` | `#f0e442` | – | – | ✓ | – | – | category 6 — marks and lines only |
| `cat-7` | `#cc79a7` | – | ✓ | ✓ | – | – | category 7 — marks and lines only |
| `cat-8` | `#6e6e6e` | ✓ | ✓ | ✓ | `#ffffff` | – | category 8 |
| `positive` | `#009e73` | – | ✓ | ✓ | – | – | gains, passes, healthy state |
| `positive-ink` | `#008663` | ✓ | ✓ | – | – | `page` | positive text and deltas |
| `negative` | `#d55e00` | – | ✓ | ✓ | – | – | failures, regressions |
| `negative-ink` | `#bb5300` | ✓ | ✓ | – | – | `page` | negative text and deltas — the family shade, granted the text role so a red chip can carry red words |
| `warning` | `#e69f00` | – | – | ✓ | – | – | warning fill / band |
| `warning-ink` | `#9d6d00` | ✓ | ✓ | – | – | `page` | warning text and threshold lines |
| `target` | `#575d69` | – | ✓ | – | – | – | dashed reference lines / goal markers |

## Derived colours

Computed from the token values, never hand-picked: `tint` = mix(`#ffffff`, family, 18 %),
`shade` = darken the family by 12 % (HSL lightness). The mix base is the theme's
**ground**, not a surface: mixing into a tinted near-white drags every hue towards the same
grey and the tints stop being tellable apart. A family has a shade only when this theme lets
it be a line — a family too light to be a line is too light to border its own fill, so it
takes the neutral `line` border instead.

| family | value | tint | shade | ink on tint |
|---|---|---|---|---|
| `cat-1` | `#0072b2` | `#d1e6f1` | `#00649d` | `#292c31` |
| `cat-2` | `#e69f00` | `#fbeed1` | – | `#292c31` |
| `cat-3` | `#009e73` | `#d1eee6` | `#008b65` | `#292c31` |
| `cat-4` | `#d55e00` | `#f7e2d1` | `#bb5300` | `#292c31` |
| `cat-5` | `#56b4e9` | `#e1f2fb` | – | `#292c31` |
| `cat-6` | `#f0e442` | `#fcfadd` | – | `#292c31` |
| `cat-7` | `#cc79a7` | `#f6e7ef` | `#c15d94` | `#292c31` |
| `cat-8` | `#6e6e6e` | `#e5e5e5` | `#616161` | `#292c31` |
| `positive` | `#009e73` | `#d1eee6` | `#008b65` | `#292c31` |
| `negative` | `#d55e00` | `#f7e2d1` | `#bb5300` | `#292c31` |
| `warning` | `#e69f00` | `#fbeed1` | – | `#292c31` |

## Blocks

Copy-paste blocks for this theme. Use exactly one block per figure; mixing blocks, or
adding a hex of your own on top, gives up the consistency the theme exists for.
Every value is literal — no alias layer, here or in any other theme.

### plantuml · structure

_structure, class, component, deployment._ One block per diagram. This is the UML family — `@startmindmap`, `@startgantt`, `@startpacketdiag` and `@startwbs` ignore `skinparam` entirely (measured: byte-identical output with and without it). `Package` carries two lines rather than three: `PackageFontColor` is a measured no-op.

```plantuml
skinparam RectangleBackgroundColor #f4f6fa
skinparam RectangleBorderColor #737a8a
skinparam RectangleFontColor #292c31
skinparam ComponentBackgroundColor #f4f6fa
skinparam ComponentBorderColor #737a8a
skinparam ComponentFontColor #292c31
skinparam ClassBackgroundColor #f4f6fa
skinparam ClassBorderColor #737a8a
skinparam ClassFontColor #292c31
skinparam UsecaseBackgroundColor #f4f6fa
skinparam UsecaseBorderColor #737a8a
skinparam UsecaseFontColor #292c31
skinparam DatabaseBackgroundColor #f4f6fa
skinparam DatabaseBorderColor #737a8a
skinparam DatabaseFontColor #292c31
skinparam NodeBackgroundColor #f4f6fa
skinparam NodeBorderColor #737a8a
skinparam NodeFontColor #292c31
skinparam ActorBackgroundColor #f4f6fa
skinparam ActorBorderColor #737a8a
skinparam ActorFontColor #292c31
skinparam StateBackgroundColor #f4f6fa
skinparam StateBorderColor #737a8a
skinparam StateFontColor #292c31
skinparam ArtifactBackgroundColor #f4f6fa
skinparam ArtifactBorderColor #737a8a
skinparam ArtifactFontColor #292c31
skinparam CloudBackgroundColor #f4f6fa
skinparam CloudBorderColor #737a8a
skinparam CloudFontColor #292c31
skinparam FolderBackgroundColor #f4f6fa
skinparam FolderBorderColor #737a8a
skinparam FolderFontColor #292c31
skinparam PackageBackgroundColor #f4f6fa
skinparam PackageBorderColor #737a8a
skinparam DefaultFontColor #292c31
skinparam ArrowColor #737a8a
skinparam ArrowFontColor #292c31
skinparam NoteBackgroundColor #e9edf4
skinparam NoteBorderColor #737a8a
skinparam NoteFontColor #292c31
skinparam stereotypeABackgroundColor #d1e6f1
skinparam stereotypeABorderColor #737a8a
skinparam stereotypeCBackgroundColor #d1e6f1
skinparam stereotypeCBorderColor #737a8a
skinparam stereotypeEBackgroundColor #d1e6f1
skinparam stereotypeEBorderColor #737a8a
skinparam stereotypeIBackgroundColor #d1e6f1
skinparam stereotypeIBorderColor #737a8a
```

### plantuml · sequence

_sequence._ Sequence diagrams take their own participant and lifeline keys; `ArrowColor` is shared with the structure block.

```plantuml
skinparam DefaultFontColor #292c31
skinparam ArrowColor #737a8a
skinparam ArrowFontColor #292c31
skinparam ParticipantBackgroundColor #f4f6fa
skinparam ParticipantBorderColor #737a8a
skinparam ParticipantFontColor #292c31
skinparam SequenceLifeLineBorderColor #737a8a
skinparam NoteBackgroundColor #e9edf4
skinparam NoteBorderColor #737a8a
skinparam NoteFontColor #292c31
```

### plantuml · activity

_activity._ Activity steps take their own keys; the diamond is the decision node. A step can also be coloured on its own with `:step; <<#fill>>` — see the element block.

```plantuml
skinparam DefaultFontColor #292c31
skinparam ArrowColor #737a8a
skinparam ArrowFontColor #292c31
skinparam ActivityBackgroundColor #f4f6fa
skinparam ActivityBorderColor #737a8a
skinparam ActivityDiamondBackgroundColor #e9edf4
```

### plantuml · element

_per-element colour._ When a block is not enough, colour one element. Use the **semicolon** form on every shape: `#fill;line:border`, with **no `#`** on the inner value. The `##` form is legal on the `class` family only — on a `rectangle`, official PlantUML does not error, it appends the suffix to the element name and falls back to an unparsed-colour fill, which is worse than a syntax error.

```plantuml
rectangle "Order service" as svc #d1e6f1;line:00649d
rectangle "Failed batch" as fail #f7e2d1;line:bb5300
```

### infographic · theme

_theme block._ Paste directly after the `infographic <template>` line, before `data`. `palette` must be a **list** — one `- #hex` per line; the space-separated form is a syntax error. Multi-colour templates read the ramp in order; single-colour templates ignore it and derive everything from `colorPrimary`, which is why one block serves all 113 templates.

```infographic
theme
  colorPrimary #0072b2
  palette
    - #0072b2
    - #e69f00
    - #009e73
    - #d55e00
    - #56b4e9
    - #f0e442
    - #cc79a7
    - #6e6e6e
```

### echarts · color

_colour ramp._ One line at the top level of every spec. Multi-series charts take one colour per series; a single series with coloured items (pie, sunburst, treemap, radar) takes one per data item; a plain single-series chart uses only the first. `itemStyle.color` on a series overrides this ramp.

```echarts
"color": ["#0072b2", "#e69f00", "#009e73", "#d55e00", "#56b4e9", "#f0e442", "#cc79a7", "#6e6e6e"]
```

### vega-lite · config

_config (Vega-Lite)._ Add as the first key of the spec. This sets the categorical range for every scale that does not declare its own.

```vega-lite
"config": { "range": { "category": ["#0072b2", "#e69f00", "#009e73", "#d55e00", "#56b4e9", "#f0e442", "#cc79a7", "#6e6e6e"] } }
```

### vega · scale

_ordinal colour scale (Vega)._ Rewrite the `range` of the ordinal colour scale the marks reference. Replace the `<dataset>` / `<category field>` placeholders with the real names. An explicit `scale.range` beats `config.range.category`, so a Vega spec must carry the ramp here.

```vega
{ "name": "color", "type": "ordinal", "domain": { "data": "<dataset>", "field": "<category field>" }, "range": ["#0072b2", "#e69f00", "#009e73", "#d55e00", "#56b4e9", "#f0e442", "#cc79a7", "#6e6e6e"] }
```

### html-css · card

_card._ Bare HTML card, coloured from the theme. The values are literal on purpose: documd-visuals does not follow the host document, so a card looks the same wherever it is pasted.

```css
.card {
  background: #f4f6fa;
  border-left: 4px solid #0072b2;
  color: #292c31;
}
.card .kicker { color: #0072b2; }
```

### html-css · badge

_badge._ A small status chip: the tint carries the fill, the shade the border, and `ink` the label.

```css
.badge {
  background: #d1e6f1;
  color: #292c31;
  border: 1px solid #00649d;
}
```

## Verification

Every block above is rendered by the theme gate, which requires the declared values to land
and the engine defaults to be gone. The contrast gate recomputes every ratio in the token
table against this theme's ground. Both run per theme; see
[`../palette.md`](../palette.md) for the contract, and for the per-engine mechanism
[`../../engines/plantuml.md`](../../engines/plantuml.md) · [`../../engines/echarts.md`](../../engines/echarts.md) · [`../../engines/vega.md`](../../engines/vega.md) · [`../../engines/infographic.md`](../../engines/infographic.md) · [`../../engines/html-css.md`](../../engines/html-css.md).
