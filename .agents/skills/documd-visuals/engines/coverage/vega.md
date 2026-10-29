# vega coverage ledger

> Generated from `catalog/scenarios.json` plus the curated unit table for this engine.
> Runtime: vega 6.4.0 + vega-lite 6.4.3. Last generated: 2026-09-21.

**Units** record what this engine does with each unit of its official documentation — kept, or
excluded with the reason. **Examples by goal** is collected from the catalog, so every link below is
resolvable from this file.

## Marks (18 official → 16 kept)

| Unit | Fence | Disposition | Example in this package |
|---|---|---|---|
| `bar` · `line` · `area` | vega-lite | kept | `delivery-throughput/*`, [incident-trend-stacked-area](../../examples/ops-monitoring/incident-trend-stacked-area.md), [streamgraph-topic-composition](../../examples/data-exploration/streamgraph-topic-composition.md) |
| `point` · `circle` · `square` | vega-lite | kept | `data-exploration/*`, [support-capacity-units](../../examples/delivery-throughput/support-capacity-units.md) |
| `tick` | vega-lite | kept | [stripplot-region-spread](../../examples/data-exploration/stripplot-region-spread.md) |
| `rect` | vega-lite | kept | [deploy-frequency-calendar](../../examples/engineering-operations/deploy-frequency-calendar.md), [service-drift-lasagna](../../examples/service-reliability/service-drift-lasagna.md) |
| `rule` | vega-lite | kept | [team-variance-interval](../../examples/service-reliability/team-variance-interval.md), [build-time-candles](../../examples/delivery-throughput/build-time-candles.md) |
| `text` | vega-lite | kept | [support-capacity-units](../../examples/delivery-throughput/support-capacity-units.md) |
| `arc` | vega-lite | kept | [release-time-split-donut](../../examples/delivery-throughput/release-time-split-donut.md) |
| `trail` | vega-lite | kept | [error-budget-burn-trail](../../examples/service-reliability/error-budget-burn-trail.md) |
| `boxplot` · `errorbar` · `errorband` | vega-lite (composite) | kept | [release-duration-distribution](../../examples/delivery-throughput/release-duration-distribution.md), [forecast-range-band](../../examples/service-reliability/forecast-range-band.md) |
| `image` | vega-lite | **excluded** | needs an external image file |
| `geoshape` | vega-lite | **excluded** | needs GeoJSON/TopoJSON; the export path is offline |

## Transforms (19 Vega-Lite + Vega additions → 25 used)

| Group | Units kept |
|---|---|
| Row/field maths | `calculate` `filter` `fold` `flatten` `pivot` `impute` `sample` |
| Aggregation & windows | `aggregate` `joinaggregate` `window` `stack` `bin` `quantile` |
| Statistics | `density` `regression` `loess` `kde` `kde2d` `isocontour` |
| Joins | `lookup` `sequence` (data generator) |
| Hierarchy & layout (Vega) | `stratify` `tree` `treelinks` `treemap` `pack` `partition` `force` `linkpath` `geopath` `pie` |
| Not used | `project` (geo), `voronoi`, `wordcloud` (covered by the infographic engine), `crossfilter`/`relay` (interaction) |

## Vega-only capability (what Vega-Lite cannot express)

| Unit | Disposition | Example |
|---|---|---|
| `force` + `linkpath` | kept — needs `"static": true` | [service-call-force-map](../../examples/dependencies-and-relations/service-call-force-map.md) |
| `tree` (cluster) + radial | kept | [org-chart-radial-tree](../../examples/organization-and-roles/org-chart-radial-tree.md) |
| `treemap` · `pack` · `partition` (+ `arc`) | kept | [cost-center-treemap](../../examples/cost-and-budget/cost-center-treemap.md), [asset-size-packing](../../examples/delivery-throughput/asset-size-packing.md), [catalog-sunburst-share](../../examples/knowledge-and-outline/catalog-sunburst-share.md) |
| `kde` · `kde2d` + `isocontour` + `geopath` | kept | [release-size-violin](../../examples/delivery-throughput/release-size-violin.md), [alert-density-contours](../../examples/ops-monitoring/alert-density-contours.md) |
| `arc` diagrams / radial layouts | kept | [module-import-arcs](../../examples/dependencies-and-relations/module-import-arcs.md) |
| Parallel coordinates | kept (built from `fold` + faceted lines, not a transform) | [parallel-risk-screen](../../examples/data-exploration/parallel-risk-screen.md) |
| Word cloud | excluded here — the infographic engine has a template for it | — |

## Composition, interaction, maps

| Unit | Disposition |
|---|---|
| `layer` · `facet` · `concat`/`hconcat`/`vconcat` · `repeat` · `resolve` | kept |
| `params` · `select` · `bind` (interaction) | excluded — an exported image cannot show them; a static overview+detail is built from two views |
| Projections / geo displays | excluded — no external geographic data |
| `mark.invalid` (`filter`, `break-paths-*`, `show`) | documented as a boundary: nulls are filtered by default, so broken lines need an explicit setting |

## Implementation boundaries

| Item | Fact |
|---|---|
| Data resolution order (Vega) | a dataset using `"source"` must be declared **after** the dataset it reads, or the spec fails with `Undefined data set name` |
| Auto-sorting | disabled by the renderer: every ordinal axis whose order matters needs an explicit `sort`, otherwise data row order decides |
| Expression evaluator | `vega-interpreter` — expressions are allowed, JavaScript functions are not |
| External data | `data.url` is unreliable on the export path; use `values` or the `sequence` generator |
| `kde2d` coordinates | receives **pixel** values (`scale('x', datum.field)`), so `bandwidth` is in pixels |

## Examples by goal

46 examples across 12 goal domains.

### [data-exploration](../../goals/data-exploration.md)

| Scenario | Tier | Example |
|---|---|---|
| distribution comparison | T1 | [metric-distribution-small-multiples.md](../../examples/data-exploration/metric-distribution-small-multiples.md)<br>[stripplot-region-spread.md](../../examples/data-exploration/stripplot-region-spread.md) |
| correlation | T1 | [metric-correlation-matrix.md](../../examples/data-exploration/metric-correlation-matrix.md) |
| composition over time | T1 | [streamgraph-topic-composition.md](../../examples/data-exploration/streamgraph-topic-composition.md) |
| deviation analysis | T1 | [deviation-from-average.md](../../examples/data-exploration/deviation-from-average.md) |
| missing data | T1 | [imputed-gap-trend.md](../../examples/data-exploration/imputed-gap-trend.md) |
| regression fit | T1 | [regression-trend-fit.md](../../examples/data-exploration/regression-trend-fit.md) |
| small multiples | T1 | [segment-pattern-small-multiples.md](../../examples/data-exploration/segment-pattern-small-multiples.md) |

### [delivery-throughput](../../goals/delivery-throughput.md)

| Scenario | Tier | Example |
|---|---|---|
| team capacity | T0 | [support-capacity-units.md](../../examples/delivery-throughput/support-capacity-units.md) |
| release packet profile | T0 | [release-duration-distribution.md](../../examples/delivery-throughput/release-duration-distribution.md)<br>[release-size-violin.md](../../examples/delivery-throughput/release-size-violin.md)<br>[build-time-candles.md](../../examples/delivery-throughput/build-time-candles.md)<br>[request-size-distribution.md](../../examples/delivery-throughput/request-size-distribution.md)<br>[asset-size-packing.md](../../examples/delivery-throughput/asset-size-packing.md)<br>[release-time-split-donut.md](../../examples/delivery-throughput/release-time-split-donut.md) |
| rank movement | T0 | [rank-movement-over-time.md](../../examples/delivery-throughput/rank-movement-over-time.md)<br>[adoption-shift-slope.md](../../examples/delivery-throughput/adoption-shift-slope.md) |
| backlog flow | T1 | [demand-overview-detail.md](../../examples/delivery-throughput/demand-overview-detail.md) |
| throughput vs cycle | T1 | [growth-vs-efficiency-path.md](../../examples/delivery-throughput/growth-vs-efficiency-path.md) |
| plan vs actual | T1 | [plan-to-actual-bridge.md](../../examples/delivery-throughput/plan-to-actual-bridge.md) |

### [service-reliability](../../goals/service-reliability.md)

| Scenario | Tier | Example |
|---|---|---|
| latency profile | T0 | [latency-beeswarm-regions.md](../../examples/service-reliability/latency-beeswarm-regions.md)<br>[service-latency-density.md](../../examples/service-reliability/service-latency-density.md)<br>[before-after-latency-gap.md](../../examples/service-reliability/before-after-latency-gap.md)<br>[service-drift-lasagna.md](../../examples/service-reliability/service-drift-lasagna.md) |
| forecast band | T1 | [forecast-range-band.md](../../examples/service-reliability/forecast-range-band.md)<br>[team-variance-interval.md](../../examples/service-reliability/team-variance-interval.md) |
| error budget | T1 | [error-budget-burn-trail.md](../../examples/service-reliability/error-budget-burn-trail.md) |
| threshold monitoring | T1 | [threshold-breach-annotation.md](../../examples/service-reliability/threshold-breach-annotation.md) |

### [business-reporting](../../goals/business-reporting.md)

| Scenario | Tier | Example |
|---|---|---|
| revenue mix | T0 | [quarterly-share-normalized-stack.md](../../examples/business-reporting/quarterly-share-normalized-stack.md) |
| revenue concentration | T1 | [revenue-concentration-topk-others.md](../../examples/business-reporting/revenue-concentration-topk-others.md) |

### [dependencies-and-relations](../../goals/dependencies-and-relations.md)

| Scenario | Tier | Example |
|---|---|---|
| service dependencies | T0 | [service-call-force-map.md](../../examples/dependencies-and-relations/service-call-force-map.md) |
| import coupling | T1 | [module-import-arcs.md](../../examples/dependencies-and-relations/module-import-arcs.md) |

### [cost-and-budget](../../goals/cost-and-budget.md)

| Scenario | Tier | Example |
|---|---|---|
| spend hierarchy | T0 | [cost-center-treemap.md](../../examples/cost-and-budget/cost-center-treemap.md) |
| cost vs capacity | T1 | [capacity-cost-dual-axis.md](../../examples/cost-and-budget/capacity-cost-dual-axis.md) |

### [knowledge-and-outline](../../goals/knowledge-and-outline.md)

| Scenario | Tier | Example |
|---|---|---|
| keyword cloud | T0 | [topic-landscape-wordcloud.md](../../examples/knowledge-and-outline/topic-landscape-wordcloud.md) |
| content mix | T2 | [catalog-sunburst-share.md](../../examples/knowledge-and-outline/catalog-sunburst-share.md) |

### [ops-monitoring](../../goals/ops-monitoring.md)

| Scenario | Tier | Example |
|---|---|---|
| incident load | T0 | [alert-density-contours.md](../../examples/ops-monitoring/alert-density-contours.md)<br>[incident-rate-stripes.md](../../examples/ops-monitoring/incident-rate-stripes.md) |
| service profile | T0 | [capability-comparison-radar.md](../../examples/ops-monitoring/capability-comparison-radar.md)<br>[risk-profile-parallel.md](../../examples/ops-monitoring/risk-profile-parallel.md) |

### [organization-and-roles](../../goals/organization-and-roles.md)

| Scenario | Tier | Example |
|---|---|---|
| org structure | T0 | [org-chart-radial-tree.md](../../examples/organization-and-roles/org-chart-radial-tree.md) |
| workforce profile | T2 | [workforce-seniority-pyramid.md](../../examples/organization-and-roles/workforce-seniority-pyramid.md) |

### [goal-and-status-reporting](../../goals/goal-and-status-reporting.md)

| Scenario | Tier | Example |
|---|---|---|
| goal attainment | T0 | [target-attainment-bullet.md](../../examples/goal-and-status-reporting/target-attainment-bullet.md) |

### [engineering-operations](../../goals/engineering-operations.md)

| Scenario | Tier | Example |
|---|---|---|
| deploy rhythm | T1 | [deploy-frequency-calendar.md](../../examples/engineering-operations/deploy-frequency-calendar.md)<br>[deploy-punchcard-weekday-hour.md](../../examples/engineering-operations/deploy-punchcard-weekday-hour.md) |

### [planning-and-roadmap](../../goals/planning-and-roadmap.md)

| Scenario | Tier | Example |
|---|---|---|
| release schedule | T2 | [release-window-schedule.md](../../examples/planning-and-roadmap/release-window-schedule.md) |

## Counts

| | |
|---|---|
| Examples using this engine | 46 |
| Goal domains reached | 12 |
| Scenarios | 32 |
| T0 scenarios | 12 |

## Sources

- Engine reference: [`../vega.md`](../vega.md)
- Catalog: [`../../catalog/scenarios.md`](../../catalog/scenarios.md)
