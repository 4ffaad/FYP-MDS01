# echarts

> Chart options rendered as static images: report-grade charts and KPI boards.
> Runtime: **echarts 6.1.0** (full package, no `echarts-gl`).
> Fence: ` ```echarts ` — the block body is a **JSON option object**, not JavaScript.

## Scope

| Family | Series `type` |
|---|---|
| Trends | `line` (stacked areas, step, smooth, bump) |
| Comparison | `bar` (grouped, stacked, normalized, radial on `polar`, `showBackground` tracks) |
| Part-of-whole | `pie` (donut, rose `roseType`, nested rings with `label.rich`) |
| Correlation | `scatter` · `effectScatter` |
| Distribution | `boxplot` · `heatmap` (+ `calendar`) |
| Hierarchy | `tree` · `treemap` · `sunburst` |
| Flow | `sankey` · `funnel` · `chord` |
| Relations | `graph` (force or `circular`) · `lines` |
| Multi-metric | `radar` · `parallel` · `matrix` |
| Time / composition | `themeRiver` · `calendar` |
| Status | `gauge` (dial, ring, progress) |
| Sizing | `pictorialBar` |
| Financial | `candlestick` |

Components: `title` · `legend` · `grid` · `xAxis`/`yAxis` · `polar`/`radiusAxis`/`angleAxis` · `radar` ·
`visualMap` · `markLine`/`markArea`/`markPoint` · `dataset` + `encode` · `graphic` · `aria` ·
`parallel`/`parallelAxis` · `calendar` · `matrix`.

## Fit

- Choose ECharts for **report-grade charts**: one clear reading, explicit axes, styled series, annotations
  (threshold bands, target lines), KPI dashboards assembled from several charts in one option.
- Choose ECharts over Vega-Lite when the visual polish and the built-in series library matter more than data
  transformation. Choose Vega-Lite when the data needs reshaping first.
- Choose ECharts over the `chart-*` infographic templates once axes, multi-series data or statistical shapes
  are involved.

## Styling

Colour comes from the chosen theme — pick one in [`../styles/palette.md`](../styles/palette.md), then
copy that theme's one-line `"color"` ramp (for example
[`../styles/themes/default.md`](../styles/themes/default.md)). Before adding a colour by hand,
know how the ramp is distributed:

| chart shape | what the ramp colours |
|---|---|
| several series | one colour per series, in order |
| one series with coloured items (pie, sunburst, treemap) | one colour per data item, in order |
| one series, one colour | only `color[0]` — the rest of the ramp is idle |

`itemStyle.color` on a series overrides the top-level `color`. Never set `textStyle` /
`axisLabel.color` / `backgroundColor`, and never hand-write a series colour the ramp already
supplies: an unstyled spec falls back to the engine's own accent (`#5070dd`).

## Constraints (verified, not assumed)

- **The option must be pure JSON** — no functions. `formatter`, `renderItem` (custom series) and every other
  callback are impossible. Format with template strings instead:
  `"{b}\n{d}%"`, `"-{c}"`, `"gate · 90"`.
- ❗ **`dataset.transform` is broken in 6.1.0** (the current release): any `sort`/`filter` transform makes
  `setOption` throw `RangeError: Maximum call stack size exceeded`, under both the SVG and canvas renderers.
  Sort and derive upstream, then hand ordered rows to `dataset.source`. `dataset` + `encode` without
  transforms works fine.
- **No maps**: `map`/`geo` need `registerMap` with map data that the package does not ship → geographic
  displays are out of scope.
- **No 3D/GL**: `globe`, `bar3D`, `scatter3D`, `surface`, `map3D`, `lines3D`, `graphGL` and friends need
  `echarts-gl`, which is not installed.
- The renderer uses the **SVG renderer**: canvas-only effects are unavailable (`lines.effect` trails, heatmap
  blending). Large datasets (> a few thousand points) are not appropriate.
- **Animation is off** by default: layouts that normally settle by simulation (`graph` force) must specify
  static geometry (`layout: "circular"` or explicit `x`/`y`).
- Interactive components are pointless in an export and should be omitted: `tooltip` · `dataZoom` · `toolbox` ·
  `brush` · `axisPointer` · `timeline` · `thumbnail`.
- `width`/`height` at the **top level** of the option set the canvas size (defaults 800×450). Do not set
  `backgroundColor` — the renderer forces a transparent background.

## Anti-patterns

| ❌ Don't | ✅ Do |
|---|---|
| A callback in `formatter` | Template strings (`"{c}%"`), per-item `label` objects, or pre-computed label fields |
| `dataset.transform` | Sort/filter upstream |
| Relying on a force layout settling | `layout: "circular"` or explicit coordinates |
| `tooltip` / `dataZoom` for a static figure | Drop them; exports cannot show them |
| A pie with eight slices | `bar` (ranked), `treemap`, or `sunburst` |
| A truncated value axis on a diverging chart | Keep zero in the axis range; the sign is the message |
| Stacking series measured in different units | Grouped bars, or two charts |
| Radial bars for non-cyclic categories | The polar system only pays off when the axis wraps (hours, weekdays, sectors) |
| Filling a wide frame with `barMaxWidth` unset | Set `barMaxWidth`/`barWidth` — bars otherwise become slabs |

## Sources

- Coverage ledger — all 24 chart families, 28 components and the GL roster, kept or excluded with a reason:
  [`coverage/echarts.md`](coverage/echarts.md)
- Option manual: <https://echarts.apache.org/en/option.html>
- Examples gallery: <https://echarts.apache.org/examples/en/index.html>
- Handbook: <https://echarts.apache.org/handbook/en/> (chart container sizing, SVG vs canvas, aria, security)
- Implemented boundary: `src/renderers/echarts-renderer.ts` (SVG renderer, JSON parse, transparent background);
  `dataset.transform` failure reproduced locally against 6.1.0
