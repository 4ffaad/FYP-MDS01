# Nord theme

Nord’s bright-ambiance reading: Snow Storm as page and ink, Frost for the cool half of the ramp, a muted Aurora for the warm half. Deliberately desaturated and cool — Nord’s own hues rather than brightened versions of them, which is why several members are fill-only on a light page.

| | |
|---|---|
| scenario | cool technical decks, developer-facing docs, calm long sessions, Nordic branding |
| ground | `#eceff4` |

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
    {"type":"rect","left":0,"top":0,"z":-10,"shape":{"width":640,"height":360},"style":{"fill":"#f6f8fb","stroke":"#6b7994","lineWidth":1}},
    {"type":"rect","left":42,"top":70,"z":-9,"shape":{"width":570,"height":228},"style":{"fill":"#e5e9f0","stroke":"#6b7994","lineWidth":1}}
  ],
  "title": {
    "text": "Quarterly volume by channel",
    "subtext": "all eight categories, adjacent, on this theme’s own surface",
    "left": 14,
    "top": 10,
    "textStyle": {"color":"#303643","fontSize":15},
    "subtextStyle": {"color":"#505a6f","fontSize":11}
  },
  "color": ["#5e81ac","#bf616a","#4f7a3f","#a35a2e","#8f6aa8","#3d7f8c","#7d6a3a","#81a1c1"],
  "legend": {"bottom":6,"itemWidth":10,"itemHeight":10,"textStyle":{"color":"#303643","fontSize":10}},
  "grid": {"left":52,"right":18,"top":76,"bottom":52},
  "xAxis": {
    "type": "category",
    "data": ["Q1","Q2","Q3","Q4"],
    "axisLine": {"lineStyle":{"color":"#6b7994"}},
    "axisTick": {"lineStyle":{"color":"#6b7994"}},
    "axisLabel": {"color":"#505a6f"}
  },
  "yAxis": {"type":"value","axisLine":{"show":false},"axisLabel":{"color":"#505a6f"},"splitLine":{"lineStyle":{"color":"#6b7994"}}},
  "series": [
    {"name":"Direct","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#5e81ac"},"data":[18,31,18,31]},
    {"name":"Partner","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#bf616a"},"data":[25,38,25,38]},
    {"name":"Search","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#4f7a3f"},"data":[32,19,32,19]},
    {"name":"Social","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#a35a2e"},"data":[39,26,39,26]},
    {"name":"Email","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#8f6aa8"},"data":[20,33,20,33]},
    {"name":"Referral","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#3d7f8c"},"data":[27,40,27,40]},
    {"name":"Events","type":"bar","stack":"total","barWidth":"52%","itemStyle":{"color":"#7d6a3a"},"data":[34,21,34,21]},
    {
      "name": "Other",
      "type": "bar",
      "stack": "total",
      "barWidth": "52%",
      "itemStyle": {"color":"#81a1c1"},
      "data": [41,28,41,28],
      "markLine": {
        "silent": true,
        "symbol": "none",
        "data": [
          {"yAxis":150,"lineStyle":{"type":"dashed","color":"#505a6f"},"label":{"color":"#505a6f","formatter":"target"}},
          {"yAxis":185,"lineStyle":{"type":"dotted","color":"#bf616a"},"label":{"color":"#505a6f","formatter":"limit"}}
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
| `ink` | `#303643` | ✓ | – | – | – | `surface-*, tint-*` | body text inside fills, headings, node labels |
| `ink-soft` | `#3f4758` | ✓ | – | – | – | `page` | secondary body text on an unfilled background |
| `muted` | `#505a6f` | ✓ | – | – | – | `page` | captions, axes tick labels, metadata — never inside a tinted fill |
| `line` | `#6b7994` | – | ✓ | – | – | – | borders, edges, arrows, axes, rules |
| `line-strong` | `#475063` | – | ✓ | – | – | – | emphasis border, connector on a tinted fill |
| `surface-0` | `#f6f8fb` | – | – | ✓ | `#303643` | – | quietest container fill |
| `surface-1` | `#e5e9f0` | – | – | ✓ | `#303643` | – | default shape / card fill |
| `surface-2` | `#d8dee9` | – | – | ✓ | `#303643` | – | nested or selected container fill |
| `cat-1` | `#5e81ac` | – | ✓ | ✓ | – | – | category 1 — also the accent colour |
| `cat-2` | `#bf616a` | – | ✓ | ✓ | – | – | category 2 — marks and lines only |
| `cat-3` | `#4f7a3f` | – | ✓ | ✓ | – | – | category 3 — fill only; the family is too light for text or lines in any theme |
| `cat-4` | `#a35a2e` | – | ✓ | ✓ | – | – | category 4 |
| `cat-5` | `#8f6aa8` | – | ✓ | ✓ | – | – | category 5 |
| `cat-6` | `#3d7f8c` | – | ✓ | ✓ | – | – | category 6 — marks and lines only |
| `cat-7` | `#7d6a3a` | ✓ | ✓ | ✓ | `#ffffff` | – | category 7 — marks and lines only |
| `cat-8` | `#81a1c1` | – | – | ✓ | – | – | category 8 |
| `positive` | `#4f7a3f` | – | ✓ | ✓ | – | – | gains, passes, healthy state |
| `positive-ink` | `#4b763d` | ✓ | ✓ | – | – | `page` | positive text and deltas |
| `negative` | `#bf616a` | – | ✓ | ✓ | – | – | failures, regressions |
| `negative-ink` | `#a4535b` | ✓ | ✓ | – | – | `page` | negative text and deltas — the family shade, granted the text role so a red chip can carry red words |
| `warning` | `#7d6a3a` | – | – | ✓ | – | – | warning fill / band |
| `warning-ink` | `#7d6a3a` | ✓ | ✓ | – | – | `page` | warning text and threshold lines |
| `target` | `#505a6f` | – | ✓ | – | – | – | dashed reference lines / goal markers |

## Derived colours

Computed from the token values, never hand-picked: `tint` = mix(`#eceff4`, family, 18 %),
`shade` = darken the family by 12 % (HSL lightness). The mix base is the theme's
**ground**, not a surface: mixing into a tinted near-white drags every hue towards the same
grey and the tints stop being tellable apart. A family has a shade only when this theme lets
it be a line — a family too light to be a line is too light to border its own fill, so it
takes the neutral `line` border instead.

| family | value | tint | shade | ink on tint |
|---|---|---|---|---|
| `cat-1` | `#5e81ac` | `#d2dbe7` | `#537297` | `#303643` |
| `cat-2` | `#bf616a` | `#e4d5db` | `#a8555d` | `#303643` |
| `cat-3` | `#4f7a3f` | `#d0dad3` | `#466b37` | `#303643` |
| `cat-4` | `#a35a2e` | `#dfd4d0` | `#8f4f28` | `#303643` |
| `cat-5` | `#8f6aa8` | `#dbd7e6` | `#7e5d94` | `#303643` |
| `cat-6` | `#3d7f8c` | `#cddbe1` | `#36707b` | `#303643` |
| `cat-7` | `#7d6a3a` | `#d8d7d3` | `#6e5d33` | `#303643` |
| `cat-8` | `#81a1c1` | `#d9e1eb` | – | `#303643` |
| `positive` | `#4f7a3f` | `#d0dad3` | `#466b37` | `#303643` |
| `negative` | `#bf616a` | `#e4d5db` | `#a8555d` | `#303643` |
| `warning` | `#7d6a3a` | `#d8d7d3` | – | `#303643` |

## Blocks

Copy-paste blocks for this theme. Use exactly one block per figure; mixing blocks, or
adding a hex of your own on top, gives up the consistency the theme exists for.
Every value is literal — no alias layer, here or in any other theme.

### plantuml · structure

_structure, class, component, deployment._ One block per diagram. This is the UML family — `@startmindmap`, `@startgantt`, `@startpacketdiag` and `@startwbs` ignore `skinparam` entirely (measured: byte-identical output with and without it). `Package` carries two lines rather than three: `PackageFontColor` is a measured no-op.

```plantuml
skinparam RectangleBackgroundColor #e5e9f0
skinparam RectangleBorderColor #6b7994
skinparam RectangleFontColor #303643
skinparam ComponentBackgroundColor #e5e9f0
skinparam ComponentBorderColor #6b7994
skinparam ComponentFontColor #303643
skinparam ClassBackgroundColor #e5e9f0
skinparam ClassBorderColor #6b7994
skinparam ClassFontColor #303643
skinparam UsecaseBackgroundColor #e5e9f0
skinparam UsecaseBorderColor #6b7994
skinparam UsecaseFontColor #303643
skinparam DatabaseBackgroundColor #e5e9f0
skinparam DatabaseBorderColor #6b7994
skinparam DatabaseFontColor #303643
skinparam NodeBackgroundColor #e5e9f0
skinparam NodeBorderColor #6b7994
skinparam NodeFontColor #303643
skinparam ActorBackgroundColor #e5e9f0
skinparam ActorBorderColor #6b7994
skinparam ActorFontColor #303643
skinparam StateBackgroundColor #e5e9f0
skinparam StateBorderColor #6b7994
skinparam StateFontColor #303643
skinparam ArtifactBackgroundColor #e5e9f0
skinparam ArtifactBorderColor #6b7994
skinparam ArtifactFontColor #303643
skinparam CloudBackgroundColor #e5e9f0
skinparam CloudBorderColor #6b7994
skinparam CloudFontColor #303643
skinparam FolderBackgroundColor #e5e9f0
skinparam FolderBorderColor #6b7994
skinparam FolderFontColor #303643
skinparam PackageBackgroundColor #e5e9f0
skinparam PackageBorderColor #6b7994
skinparam DefaultFontColor #303643
skinparam ArrowColor #6b7994
skinparam ArrowFontColor #303643
skinparam NoteBackgroundColor #d8dee9
skinparam NoteBorderColor #6b7994
skinparam NoteFontColor #303643
skinparam stereotypeABackgroundColor #d2dbe7
skinparam stereotypeABorderColor #6b7994
skinparam stereotypeCBackgroundColor #d2dbe7
skinparam stereotypeCBorderColor #6b7994
skinparam stereotypeEBackgroundColor #d2dbe7
skinparam stereotypeEBorderColor #6b7994
skinparam stereotypeIBackgroundColor #d2dbe7
skinparam stereotypeIBorderColor #6b7994
```

### plantuml · sequence

_sequence._ Sequence diagrams take their own participant and lifeline keys; `ArrowColor` is shared with the structure block.

```plantuml
skinparam DefaultFontColor #303643
skinparam ArrowColor #6b7994
skinparam ArrowFontColor #303643
skinparam ParticipantBackgroundColor #e5e9f0
skinparam ParticipantBorderColor #6b7994
skinparam ParticipantFontColor #303643
skinparam SequenceLifeLineBorderColor #6b7994
skinparam NoteBackgroundColor #d8dee9
skinparam NoteBorderColor #6b7994
skinparam NoteFontColor #303643
```

### plantuml · activity

_activity._ Activity steps take their own keys; the diamond is the decision node. A step can also be coloured on its own with `:step; <<#fill>>` — see the element block.

```plantuml
skinparam DefaultFontColor #303643
skinparam ArrowColor #6b7994
skinparam ArrowFontColor #303643
skinparam ActivityBackgroundColor #e5e9f0
skinparam ActivityBorderColor #6b7994
skinparam ActivityDiamondBackgroundColor #d8dee9
```

### plantuml · element

_per-element colour._ When a block is not enough, colour one element. Use the **semicolon** form on every shape: `#fill;line:border`, with **no `#`** on the inner value. The `##` form is legal on the `class` family only — on a `rectangle`, official PlantUML does not error, it appends the suffix to the element name and falls back to an unparsed-colour fill, which is worse than a syntax error.

```plantuml
rectangle "Order service" as svc #d2dbe7;line:537297
rectangle "Failed batch" as fail #dfd4d0;line:8f4f28
```

### infographic · theme

_theme block._ Paste directly after the `infographic <template>` line, before `data`. `palette` must be a **list** — one `- #hex` per line; the space-separated form is a syntax error. Multi-colour templates read the ramp in order; single-colour templates ignore it and derive everything from `colorPrimary`, which is why one block serves all 113 templates.

```infographic
theme
  colorPrimary #5e81ac
  palette
    - #5e81ac
    - #bf616a
    - #4f7a3f
    - #a35a2e
    - #8f6aa8
    - #3d7f8c
    - #7d6a3a
    - #81a1c1
```

### echarts · color

_colour ramp._ One line at the top level of every spec. Multi-series charts take one colour per series; a single series with coloured items (pie, sunburst, treemap, radar) takes one per data item; a plain single-series chart uses only the first. `itemStyle.color` on a series overrides this ramp.

```echarts
"color": ["#5e81ac", "#bf616a", "#4f7a3f", "#a35a2e", "#8f6aa8", "#3d7f8c", "#7d6a3a", "#81a1c1"]
```

### vega-lite · config

_config (Vega-Lite)._ Add as the first key of the spec. This sets the categorical range for every scale that does not declare its own.

```vega-lite
"config": { "range": { "category": ["#5e81ac", "#bf616a", "#4f7a3f", "#a35a2e", "#8f6aa8", "#3d7f8c", "#7d6a3a", "#81a1c1"] } }
```

### vega · scale

_ordinal colour scale (Vega)._ Rewrite the `range` of the ordinal colour scale the marks reference. Replace the `<dataset>` / `<category field>` placeholders with the real names. An explicit `scale.range` beats `config.range.category`, so a Vega spec must carry the ramp here.

```vega
{ "name": "color", "type": "ordinal", "domain": { "data": "<dataset>", "field": "<category field>" }, "range": ["#5e81ac", "#bf616a", "#4f7a3f", "#a35a2e", "#8f6aa8", "#3d7f8c", "#7d6a3a", "#81a1c1"] }
```

### html-css · card

_card._ Bare HTML card, coloured from the theme. The values are literal on purpose: documd-visuals does not follow the host document, so a card looks the same wherever it is pasted.

```css
.card {
  background: #e5e9f0;
  border-left: 4px solid #5e81ac;
  color: #303643;
}
.card .kicker { color: #5e81ac; }
```

### html-css · badge

_badge._ A small status chip: the tint carries the fill, the shade the border, and `ink` the label.

```css
.badge {
  background: #d2dbe7;
  color: #303643;
  border: 1px solid #537297;
}
```

## Verification

Every block above is rendered by the theme gate, which requires the declared values to land
and the engine defaults to be gone. The contrast gate recomputes every ratio in the token
table against this theme's ground. Both run per theme; see
[`../palette.md`](../palette.md) for the contract, and for the per-engine mechanism
[`../../engines/plantuml.md`](../../engines/plantuml.md) · [`../../engines/echarts.md`](../../engines/echarts.md) · [`../../engines/vega.md`](../../engines/vega.md) · [`../../engines/infographic.md`](../../engines/infographic.md) · [`../../engines/html-css.md`](../../engines/html-css.md).
