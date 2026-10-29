# html-css

> System architecture diagrams, cards and page-level layouts written as bare HTML, rendered by the
> document pipeline. There is **no fence**: HTML is embedded directly in the Markdown document. This
> engine has no external runtime — it is the document's own renderer plus the patterns in this file.

## Scope

Three jobs, all done with the same tool. The first is the reason this engine exists.

| Job | What it is | Examples |
|---|---|---|
| **System architecture** — the whole system on one page | boxes, layers, boundaries and connectors laid out by hand, with full control over where every component sits | [`examples/system-architecture/layered-with-wings.md`](../examples/system-architecture/layered-with-wings.md) · [`complex-system-blueprint.md`](../examples/system-architecture/complex-system-blueprint.md) · [`layer-stack.md`](../examples/system-architecture/layer-stack.md) · [`operations-overview.md`](../examples/system-architecture/operations-overview.md) · [`nested-zones.md`](../examples/system-architecture/nested-zones.md) · [`pipeline-stages.md`](../examples/system-architecture/pipeline-stages.md) · [`request-paths.md`](../examples/system-architecture/request-paths.md) · [`service-catalog.md`](../examples/system-architecture/service-catalog.md) |
| **Content artefact** — one page that explains one thing | a memo, policy note, incident review, brief or bulletin | [`examples/internal-documents/executive-brief-summary.md`](../examples/internal-documents/executive-brief-summary.md) · [`examples/incident-management/incident-review-card.md`](../examples/incident-management/incident-review-card.md) · [`examples/customer-and-partner-comms/customer-story-card.md`](../examples/customer-and-partner-comms/customer-story-card.md) |
| **Page geometry** — the skeleton either of the above is built on | a grid that holds blocks | [`examples/goal-and-status-reporting/leadership-metric-board.md`](../examples/goal-and-status-reporting/leadership-metric-board.md) · [`examples/planning-and-roadmap/delivery-roadmap-board.md`](../examples/planning-and-roadmap/delivery-roadmap-board.md) · [`examples/comparison-and-selection/decision-comparison-card.md`](../examples/comparison-and-selection/decision-comparison-card.md) |

When a diagram engine can draw the figure, prefer it: `plantuml` computes a layout, and this
engine does not. Choose HTML when the figure is a **page** — when the arrangement itself is the design, or
when the boxes need to hold prose.

## Rules of the form

1. **Embed HTML directly.** Never wrap cards in a ```` ```html ```` fence — a fenced block is rendered as an
   image by the HTML renderer, while direct HTML stays live markup.
2. **No blank lines inside the HTML.** A CommonMark HTML block ends at a blank line; the pipeline can only
   merge *adjacent* HTML nodes, so a blank line silently cuts the card in two and breaks its CSS.
3. **Prefix every class name.** `<style scoped>` is dead (browsers dropped the attribute) and the pipeline has
   no scoping step — use a unique prefix such as `card-*`, otherwise two cards in one document fight.
4. **Constrain the root container**: `max-width` plus `box-sizing: border-box`, so the export width is
   predictable. `860px` is the value for a card; an architecture diagram needs more room and uses
   `1040px`–`1140px`.
5. **Analyse the content first** (density → structure → mood) before picking a layout:
   - density: ≤ 50 words → one large anchor + whitespace; 50–200 → hero + 2–3 supporting blocks;
     200+ → asymmetric columns with an explicit primary/secondary/tertiary hierarchy (never equal-weight tiling)
   - structure: single point → one anchor; contrast → split; hierarchy → stacked modules; process → vertical
     cascade with numbers; radial → hub and spokes; peers → asymmetric grid
   - mood → colour temperature and tone of the copy

## Styling

Colour comes from the chosen theme — pick one in [`../styles/palette.md`](../styles/palette.md), then
copy that theme's card block (for example
[`../styles/themes/default.md`](../styles/themes/default.md)). The values are literal: this skill
does not follow the host document, which is why no other engine can do what it does either.

- Palette tokens only: `tint-*` / `surface-*` fills, `ink` text, `line` borders, `cat-*` for the ramp.
- **Never `var(--md-*)`.** The viewer exposes eight such variables and an earlier revision used them to
  make cards follow the document; that was removed, because a figure which changes colour with the host
  document is not an artefact. Every value is literal, in every engine.
- One accent + neutrals + at most one semantic colour per card. An architecture diagram is the exception:
  its layer bands may use several `tint-*` values, because there the hue *encodes* the layer.
- Never invent a neutral (one card in this corpus carried nine near-blacks and greys), and never set
  `font-family`.

## Constraints

- **Export rasterises HTML.** Both the HTML and DOCX export paths turn a card into a PNG. Consequences:
  text inside a card is **not selectable or searchable** in the exported file, the theme is baked in, and the
  card width is the final pixel width. Never put information *only* inside a card.
- No DOCX semantics for `grid`, `flex`, `border-radius`, `gradient`, `box-shadow` — those layouts survive as a
  screenshot, not as reflowable content.
- Do not hard-code `font-family`: text follows the document theme's font.
- Images must be local or data URLs; remote images are unreliable on the export path.
- Keep the CSS to what a static render needs — no animation, no hover-only affordances, no JS.

## Anti-patterns

| ❌ Don't | ✅ Do |
|---|---|
| ```` ```html ```` fences for cards | Direct HTML |
| A blank line between blocks | Keep the card as one uninterrupted block |
| Generic class names (`.section`, `.header`) | `card-section`, `card-header` … |
| Unbounded width | `max-width: 860px; box-sizing: border-box` |
| Equal-width columns for a prioritised list | Asymmetric grid; the eye needs the hierarchy |
| Colour as decoration | Colour encodes a layer or a severity, consistently |
| Twelve-colour palettes | One accent + neutrals + one semantic colour |
| Hard-coded `font-family` / dark-mode hex values | Theme fonts and theme-neutral tokens |
| Putting the only copy of a fact into a card | Keep the fact in prose too — cards export as images |

## Page skeletons worth reusing

Compose a page from one of these; each is a few lines of `display: grid` — nothing to install. The
**first row is the default**: reach for it when nothing more specific is called for.

| Skeleton | Shape | Use for | Example |
|---|---|---|---|
| **Layered with wings** ★ | A stack of layer bands, flanked by two full-height columns | The default architecture figure — the layers, plus what serves and governs all of them | [`layered-with-wings.md`](../examples/system-architecture/layered-with-wings.md) · six bands, wings grouped: [`complex-system-blueprint.md`](../examples/system-architecture/complex-system-blueprint.md) |
| Layered stack | Full-width bands, one per layer | The layers alone, with no wings | [`layer-stack.md`](../examples/system-architecture/layer-stack.md) |
| Sidebar | Core layers + one narrow rail | Systems where operations or security needs its own lane | [`operations-overview.md`](../examples/system-architecture/operations-overview.md) |
| Nested containers | Boxes inside boxes | Environments, regions, zones, VPCs, tenant isolation | [`nested-zones.md`](../examples/system-architecture/nested-zones.md) |
| Staged flow | Horizontal stage blocks with arrows | Pipelines, CI/CD, ETL, value streams | [`pipeline-stages.md`](../examples/system-architecture/pipeline-stages.md) |
| Connector overlay | Absolutely positioned boxes + an SVG layer | Call paths, dependencies, fan-in | [`request-paths.md`](../examples/system-architecture/request-paths.md) |
| Catalogue grid | Uniform small cells | Equal-weight inventories: services, tools, skills | [`service-catalog.md`](../examples/system-architecture/service-catalog.md) |
| Asymmetric grid (bento) | Mixed-weight cells | Multi-topic overviews where one cell is the headline | [`leadership-metric-board.md`](../examples/goal-and-status-reporting/leadership-metric-board.md) |
| Two / three column | 2–3 equal columns | Side-by-side views, comparisons | [`decision-comparison-card.md`](../examples/comparison-and-selection/decision-comparison-card.md) |
| Hub and spokes | Centred node + satellites | Integration platforms, core-plus-features | [`radial-hub-network.md`](../examples/network-topology/radial-hub-network.md) |
| Single stack | One column, generous spacing | One topic, low to medium density | [`executive-brief-summary.md`](../examples/internal-documents/executive-brief-summary.md) |

Rules that apply to all of them: **`align-items: stretch` whenever a column is meant to span the others**
(a rail that floats to its own content height says the opposite of what it means), layer colours encode
meaning rather than decorate, and equal-width columns are wrong for a prioritised list.

## Connectors between components

When a layout needs lines between boxes, draw them as inline SVG rather than borders:

```xml
<defs>
  <marker id="arrowhead" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto">
    <polygon points="0 0, 10 4, 0 8" fill="#4a4a4a"/>
  </marker>
</defs>
```

- Orthogonal routing (`M x1,y1 L x1,ym L x2,ym L x2,y2`) reads best with a grid layout; use `marker-end="url(#arrowhead)"` on the path.
- Keep connector stroke at 1–1.5 px and a neutral grey; the boxes carry the meaning, the line only the direction.
- Label a connector only when the relationship is not obvious from the two boxes.

## Sources

- Coverage ledger — the inherited inventory and the export boundaries, with dispositions:
  [`coverage/html-css.md`](coverage/html-css.md)
- Rules 1–5 govern every card; the nine skeletons above are the geometry worth reusing.
- Implemented pipeline: `src/plugins/html-plugin.ts`, `src/plugins/remark-inline-html.ts`,
  `src/renderers/html-renderer.ts`, `src/exporters/docx-exporter.ts` (rasterisation).
- MDN for CSS behaviour: <https://developer.mozilla.org/>
