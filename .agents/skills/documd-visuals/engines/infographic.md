# infographic

> Template-driven boards: roadmaps, sequences, comparisons, knowledge maps.
> Runtime: `@antv/infographic` **0.2.20** (113 templates, 42 registered structures). Fence:
> ` ```infographic `. Template key index: [`infographic-templates.tsv`](infographic-templates.tsv).

## Scope

Template-driven infographics: a small set of layouts that already look designed, filled with your content.
Seven families, 42 structures:

| Family | Structures | `data` collection |
|---|---|---|
| `list-*` | grid · row · column · pyramid · sector · waterfall · zigzag | `lists` |
| `sequence-*` | steps · timeline · roadmap · snake · zigzag · stairs · funnel · circular · cycle · ascending … | `sequences` |
| `compare-*` | binary-horizontal · hierarchy-row · hierarchy-left-right · swot · quadrant | `compares` |
| `relation-*` | network · circle · dagre-flow | `nodes` + `relations` |
| `hierarchy-*` | structure · structure-mirror · tree · mindmap | `root` (nested `children`) |
| `chart-*` | bar · column · line · pie · wordcloud | `values` |

## Syntax

```infographic
infographic sequence-snake-steps-simple
data
  title Customer Onboarding Flow
  desc Six sequential steps from signup to productive usage
  sequences
    - label Sign Up
      desc Account created
    - label Verify Identity
      icon mdi/email-check-outline
```

- Line 1: `infographic <template-name>`. The template name **is** the layout — there is no separate layout
  property in the common case.
- `data` holds `title`, `desc`, then exactly **one** collection, chosen by the structure (table above).
- Item fields: `label` (always), `desc`, `icon` (any `mdi/*` name), and structure-specific extras —
  `done true|false` (checklists), `value <number>` (`chart-*`), `children` (`compare-*`, `hierarchy-*`),
  `id`/`group` (`relation-*`), `from`/`to`/`label` (relations).
- Indentation is two spaces per level; `- ` starts a list item.
- A `theme` line or a `themeConfig` block may follow the first line; `order desc` can be given where the
  engine supports reversing the data order.

### Templates without a template name

Four registered structures have no template key. Use the inline design block instead:

```infographic
infographic
design
  structure hierarchy-tree
  item rounded-rect-node
data
  title …
  root
    label …
    children
      - label …
```

Template-less structures: `hierarchy-tree` · `hierarchy-mindmap` · `relation-dagre-flow` ·
`sequence-interaction`.

## Fit

- Choose Infographic when the deliverable should **look designed without design work**: roadmaps, timelines,
  checklists, comparisons, quadrant sorting, knowledge maps, metric callouts.
- Choose `echarts` instead as soon as there are axes, several series, or statistical shapes — the `chart-*`
  templates are deliberately lightweight callouts, not analytical charts.
- Choose `plantuml` when the diagram is a system (UML, dependencies, topology) rather than a narrative.

## Constraints

- **Canvas grows with the content.** Unlike ECharts there is no fixed frame: the SVG is sized by the item
  count and the structure. Keep list/sequence items to **3–6**; a 12-step snake becomes a very wide strip.
  (Measured: `hierarchy-tree` ≈ 365 px per leaf; `sequence-interaction` ≈ 390 px per item;
  `hierarchy-mindmap` is pinned at 2086 px wide regardless of content.)
- **The theme is not yours to set per block** in a themed document: the renderer maps the document theme to
  `light`/`dark`, and `hand-drawn` styling is applied from the document's rough mode.
- **No free layout.** Item order is the reading order; there is no coordinate control, no per-item styling and
  no way to move one item somewhere else.
- Icons must be valid `mdi/*` names; an unknown name degrades to a blank slot.
- Long `desc` strings overflow their slot: one clause per item.
- The renderer reports syntax errors with `Expected format: infographic <template-name> …`, which is what you
  see when the template name is misspelled (a near-miss name may still resolve to a *different* template).

## Anti-patterns

| ❌ Don't | ✅ Do |
|---|---|
| Seven or more items in a list/sequence | Split into two infographics, or aggregate |
| `values` with ten categories | `echarts` bar/line — `chart-*` is a callout, not a chart |
| The wrong collection name for the family | Match `lists`/`sequences`/`compares`/`values`/`nodes`+`relations`/`root` |
| Items with long prose | Move detail to the body text; the figure carries the labels |
| Using a quadrant template for ranking | Quadrants classify; use a scored table or a ranked bar chart |
| Inventing a template name | Pick from the 113-key index in [`infographic-templates.tsv`](infographic-templates.tsv) |
| Expecting a second layout pass | Choose the template whose item style already reads the way you want |
| Mixing light/dark palettes inside one block | Let the document theme drive it |

## Styling

Every example carries the same `theme` block, copied from the theme file it is written in —
themes are indexed in [`../styles/palette.md`](../styles/palette.md), and
[`../styles/themes/default.md`](../styles/themes/default.md) is the one the corpus uses. The block
is deliberately one shape for all 113 templates:

```infographic
theme
  colorPrimary #2b66c4
  palette
    - #2b66c4
    - #2f9e44
    - #f3a33c
```

- `palette` **must be a list**, one `- #hex` per line — the space-separated single-line form is a
  syntax error.
- A ramp template (`chart-*`, colour-bearing `compare-*` / `relation-*`) reads the ramp in order;
  a single-colour template (`sequence-*-simple`, `list-*-simple`, `hierarchy-*`) ignores `palette`
  and derives everything from `colorPrimary`. Keeping both keys is what lets one block serve
  every template.
- The theme vocabulary is much narrower than the runtime's type suggests. `colorPrimary` and
  `colorBg` are the only colour keys the DSL accepts besides `palette`; **`colorText`,
  `colorTextSecondary`, `colorPrimaryText`, `colorPrimaryBg`, `colorBgElevated` and `colorWhite`
  are rejected with a syntax error.** Text colour therefore stays with the engine — do not try to
  theme it, and do not add a `style` workaround.
- Leave `colorBg` unset: the board sits on the document's page background, not on a colour of ours.

## Sources

- Coverage ledger — families, structures, templates and item styles, generated from the installed package:
  [`coverage/infographic.md`](coverage/infographic.md)
- Syntax: <https://infographic.antv.vision/learn/infographic-syntax> · concepts:
  <https://infographic.antv.vision/learn/core-concepts>
- Gallery (276 cards, 7 families): <https://infographic.antv.vision/gallery> · template mechanism:
  <https://infographic.antv.vision/learn/template> · data: <https://infographic.antv.vision/learn/data> ·
  theme: <https://infographic.antv.vision/learn/theme>
- Template index (generated from the installed package): [`infographic-templates.tsv`](infographic-templates.tsv)
  — template → structure → item style, one row per template
