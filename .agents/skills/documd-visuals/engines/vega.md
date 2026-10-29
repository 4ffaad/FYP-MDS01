# vega

> Vega-Lite's declarative grammar plus the Vega runtime for everything it cannot express.
> Runtime: **vega 6.4.0** + **vega-lite 6.4.3**.
> Fences: ` ```vega-lite ` (alias `vegalite`) for the declarative grammar, ` ```vega ` for the
> low-level runtime. Expressions are evaluated by `vega-interpreter` — **no JavaScript in specs**.

## Scope

**Vega-Lite** — declarative single and multi-view charts:

| Area | Units |
|---|---|
| Marks | `bar` `line` `area` `point` `circle` `square` `tick` `rect` `rule` `text` `arc` `trail` |
| Composite marks | `boxplot` `errorbar` `errorband` |
| Transforms | aggregate · bin · calculate · density · filter · flatten · fold · impute · joinaggregate · loess · lookup · pivot · quantile · regression · sample · stack · timeUnit · window |
| Composition | `layer` · `facet` · `concat`/`hconcat`/`vconcat` · `repeat` · `resolve` |
| Data | inline `values`, `sequence`/`sphere` generators |

**Vega** — everything Vega-Lite cannot express: layouts and statistics implemented as transforms with marks:

`force` (+ `linkpath`) · `tree` (+ `treelinks`, radial via `orient`) · `treemap` · `pack` · `partition`
(+ `arc` = sunburst) · `kde` (violin / density) · `kde2d` + `isocontour` + `geopath` (contour plots) ·
`wordcloud` · `voronoi` · `quantile` · `stratify` · `heatmap` · `pie` (+ `arc`) · `trail` marks.

## Fit

- Choose Vega/Vega-Lite when the **data needs work before it can be drawn**: joins, windows, regression,
  LOESS, density, imputation, top-k, percent-of-total, small multiples, faceting.
- Choose Vega-Lite for **exploration-style** charts and statistical views; choose `echarts` for
  report-grade single charts with heavy styling and a legend-heavy layout.
- Vega-Lite is the fastest route to "one more panel": `layer`/`facet`/`repeat` compose without new engines.

## Styling

Colour comes from the chosen theme — pick one in [`../styles/palette.md`](../styles/palette.md), then
copy that theme's two mechanisms (for example
[`../styles/themes/default.md`](../styles/themes/default.md)) — two dialects, two mechanisms:

- **vega-lite**: `"config": { "range": { "category": [ … ] } }`. It replaces the default `tableau10`
  scheme for every categorical channel; a channel's own `scale.range` still wins.
- **vega**: an explicit `"type": "ordinal"` colour scale whose `range` is the ramp, with the marks
  reading it (`"fill": { "scale": "color", "field": … }`). Without it every mark gets the same
  default blue.

Leave `config.axis.*` / `config.text.*` colours and `config.background` alone — the renderer owns
 text and the figure must stay transparent. `"scheme"` values are for continuous scales; a continuous
scale derived from the palette interpolates within one family (`tint-*` → `shade-*`).

## Constraints

- **No external data**: `data.url` is unreliable on the offline/export path — always inline `data.values`,
  or use the `sequence` generator. Geographic displays are out of scope (they need GeoJSON/TopoJSON).
- **Interactions are out of scope**: `params`/`select`/`bind` and the interactive gallery are for live pages;
  an exported image cannot show them. Static overview+detail is fine (two views, one axis).
- **Vega resolves datasets in declaration order**: a dataset that uses `"source": "<name>"` must come *after*
  the dataset it reads, or you get `Undefined data set name`.
- **`force` must be `"static": true`**, otherwise the render captures mid-simulation and the picture changes
  between runs.
- **Vega-Lite auto-sorting is disabled** by the renderer: every ordinal axis whose order matters needs an
  explicit `"sort"` (or a deliberate data row order). Sorting is not inferred from the data type.
- `kde2d` receives **pixel** coordinates (`{"expr": "scale('x', datum.field)"}`), so its `bandwidth` is in
  pixels, not data units.
- Data field names produced by transforms must be used verbatim: `density` → `value` + `density`;
  `bin` → `bin_maxbins_*`; `regression` → `x` + `y`; `fold` → `key` + `value`.
- `mark.color`/`fill` values are pixel-level styling: when a document defines both light and dark themes,
  prefer theme-neutral schemes (`redblue`, `blues`) or a small set of literal accents.

## Anti-patterns

| ❌ Don't | ✅ Do |
|---|---|
| `data: {"url": …}` | Inline `values` (or `sequence`) |
| `params` / `select` for a static export | Layer or facet to show both states |
| A force layout without `static: true` | `"static": true`, `iterations` ≥ 200 |
| Implicit ordinal order | Explicit `"sort"` on the encoding channel |
| A 200-row inline `values` array | Aggregate upstream, or use `sequence` + `calculate` |
| Smoothing a stacked area hard (`smooth: true`) | Small `smooth` values, or none — interpolated area invents volume |
| Pie charts with many slices | `arc` for ≤ 6 parts, bars otherwise |
| Reading a Vega `tree`/`treemap`/`pack` output as data | Those transforms *generate* geometry; the fields (`x`,`y`,`r`,`x0`…) are layout output |

## Sources

- Coverage ledger — every mark, transform and composition unit, kept or excluded with a reason:
  [`coverage/vega.md`](coverage/vega.md)
- Vega-Lite docs: <https://vega.github.io/vega-lite/docs/> · gallery: <https://vega.github.io/vega-lite/examples/>
- Vega docs: <https://vega.github.io/vega/docs/> · transforms: <https://vega.github.io/vega/docs/transforms/> ·
  gallery: <https://vega.github.io/vega/examples/>
- Implemented boundary: `src/renderers/vega-renderer.ts` (canvas renderer, interpreter, auto-sort disabled)
