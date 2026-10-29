# echarts coverage ledger

> Generated from `catalog/scenarios.json` plus the curated unit table for this engine.
> Runtime: echarts 6.1.0 (full package, no `echarts-gl`). Last generated: 2026-09-22.

**Units** record what this engine does with each unit of its official documentation — kept, or
excluded with the reason. **Examples by goal** is collected from the catalog, so every link below is
resolvable from this file.

## Chart families (24 official → 22 kept)

| Family | `series.type` | Disposition | Example in this package |
|---|---|---|---|
| Line | `line` | kept | [trend-line-multi-series](../../examples/ops-monitoring/trend-line-multi-series.md), [incident-trend-stacked-area](../../examples/ops-monitoring/incident-trend-stacked-area.md) |
| Bar | `bar` | kept | [comparison-bars](../../examples/business-reporting/comparison-bars.md), [run-rate-waterfall](../../examples/cost-and-budget/run-rate-waterfall.md), [goal-attainment-background-bars](../../examples/goal-and-status-reporting/goal-attainment-background-bars.md) |
| Pie | `pie` | kept | [pie-budget-share](../../examples/cost-and-budget/pie-budget-share.md), [donut-channel-mix](../../examples/go-to-market/donut-channel-mix.md), `lead-source-rose`, `cloud-spend-nested-pie` |
| Scatter | `scatter` `effectScatter` | kept | [scatter-segment-correlation](../../examples/data-exploration/scatter-segment-correlation.md), [effectscatter-outlier-alerts](../../examples/ops-monitoring/effectscatter-outlier-alerts.md) |
| Candlestick | `candlestick` | kept | [candlestick-quarterly-price-range](../../examples/business-reporting/candlestick-quarterly-price-range.md) |
| Radar | `radar` | kept | [radar-capability-profile](../../examples/ops-monitoring/radar-capability-profile.md) |
| Boxplot | `boxplot` | kept | [boxplot-latency-distribution](../../examples/service-reliability/boxplot-latency-distribution.md) |
| Heatmap | `heatmap` | kept | [heatmap-incident-load](../../examples/ops-monitoring/heatmap-incident-load.md), [calendar-release-pace](../../examples/engineering-operations/calendar-release-pace.md) |
| Graph | `graph` | kept | [graph-platform-dependencies](../../examples/dependencies-and-relations/graph-platform-dependencies.md), `service-ownership-circle-graph` |
| Lines | `lines` | kept | [lines-route-flows](../../examples/network-topology/lines-route-flows.md) |
| Tree | `tree` | kept | [tree-support-routing](../../examples/incident-management/tree-support-routing.md) |
| Treemap | `treemap` | kept | [treemap-portfolio-breakdown](../../examples/cost-and-budget/treemap-portfolio-breakdown.md) |
| Sunburst | `sunburst` | kept | [sunburst-lifecycle-share](../../examples/cost-and-budget/sunburst-lifecycle-share.md) |
| Parallel | `parallel` | kept | [parallel-risk-screen](../../examples/data-exploration/parallel-risk-screen.md) |
| Sankey | `sankey` | kept | [sankey-channel-to-fulfilment](../../examples/product-metrics/sankey-channel-to-fulfilment.md) |
| Funnel | `funnel` | kept | [funnel-stage-conversion](../../examples/product-metrics/funnel-stage-conversion.md) |
| Gauge | `gauge` | kept | [gauge-sla-attainment](../../examples/service-reliability/gauge-sla-attainment.md) |
| PictorialBar | `pictorialBar` | kept | [pictorialbar-capacity-symbols](../../examples/delivery-throughput/pictorialbar-capacity-symbols.md) |
| ThemeRiver | `themeRiver` | kept | [themeriver-topic-attention](../../examples/knowledge-and-outline/themeriver-topic-attention.md) |
| Calendar | `calendar` + `heatmap`/`scatter` | kept | [calendar-release-pace](../../examples/engineering-operations/calendar-release-pace.md) |
| Matrix | `matrix` (v6) | kept | [matrix-service-scorecards](../../examples/ops-monitoring/matrix-service-scorecards.md) |
| Chord | `chord` (v6) | kept | [chord-team-handoffs](../../examples/organization-and-roles/chord-team-handoffs.md) |
| **GEO/Map** | `map` `geo` | **excluded** | needs `registerMap` and map data the package does not ship; no GeoJSON on the offline export path |
| **Custom** | `custom` | **excluded** | needs a JS `renderItem` function; the option must stay pure JSON |

## GL / 3D (11 official families → all excluded)

`globe` · `bar3D` · `scatter3D` · `surface` · `map3D` · `lines3D` · `line3D` · `scatterGL` · `linesGL` ·
`flowGL` · `graphGL` — all require `echarts-gl`, which is not bundled. Use the 2D equivalents.

## Components (28 official → 21 kept)

| Kept | Excluded (interaction-only or unusable here) |
|---|---|
| `title` `legend` `grid` `xAxis`/`yAxis` `polar` `radiusAxis`/`angleAxis` `radar` `visualMap` `markLine`/`markArea`/`markPoint` `dataset` + `encode` `graphic` `aria` `parallel`/`parallelAxis` `singleAxis` `calendar` `matrix` | `tooltip` `dataZoom` `toolbox` `brush` `axisPointer` `timeline` `thumbnail` — an exported image cannot show them; `geo` — see above |

## Capability items

| Item | Disposition |
|---|---|
| `dataset.source` + `encode` + `dimensions` | kept — [backlog-ranking-dataset](../../examples/delivery-throughput/backlog-ranking-dataset.md) |
| `dataset.transform` | **excluded — broken**: any `sort`/`filter` transform throws `RangeError: Maximum call stack size exceeded` at `setOption` under both the SVG and canvas renderers (reproduced against 6.1.0, the current release). Sort and derive upstream |
| Functions anywhere in the option | excluded — the block is parsed as JSON; use template strings and per-item label objects |
| Rich text labels (`label.rich`) | kept — [cloud-spend-nested-pie](../../examples/cost-and-budget/cloud-spend-nested-pie.md) |
| Visual mapping | kept (`visualMap`) |
| Events and actions | excluded — interaction-only |
| Canvas renderer | excluded — this pipeline renders SVG, so canvas-only effects (trail lines, heatmap blending) are unavailable |

## Examples by goal

39 examples across 16 goal domains.

### [ops-monitoring](../../goals/ops-monitoring.md)

| Scenario | Tier | Example |
|---|---|---|
| incident load | T0 | [heatmap-incident-load.md](../../examples/ops-monitoring/heatmap-incident-load.md) |
| service profile | T0 | [radar-capability-profile.md](../../examples/ops-monitoring/radar-capability-profile.md) |
| support load | T0 | [support-volume-radial-bars.md](../../examples/ops-monitoring/support-volume-radial-bars.md) |
| anomaly scan | T1 | [effectscatter-outlier-alerts.md](../../examples/ops-monitoring/effectscatter-outlier-alerts.md) |
| incident trend | T1 | [incident-trend-stacked-area.md](../../examples/ops-monitoring/incident-trend-stacked-area.md) |
| metric trend | T1 | [trend-line-multi-series.md](../../examples/ops-monitoring/trend-line-multi-series.md) |
| service scorecard | T1 | [matrix-service-scorecards.md](../../examples/ops-monitoring/matrix-service-scorecards.md) |

### [delivery-throughput](../../goals/delivery-throughput.md)

| Scenario | Tier | Example |
|---|---|---|
| team capacity | T0 | [pictorialbar-capacity-symbols.md](../../examples/delivery-throughput/pictorialbar-capacity-symbols.md) |
| rank movement | T0 | [team-rank-bump-chart.md](../../examples/delivery-throughput/team-rank-bump-chart.md) |
| backlog flow | T1 | [backlog-ranking-dataset.md](../../examples/delivery-throughput/backlog-ranking-dataset.md) |
| throughput vs cycle | T1 | [throughput-band-range-area.md](../../examples/delivery-throughput/throughput-band-range-area.md) |
| work mix | T1 | [engineering-time-100pct-bars.md](../../examples/delivery-throughput/engineering-time-100pct-bars.md) |

### [cost-and-budget](../../goals/cost-and-budget.md)

| Scenario | Tier | Example |
|---|---|---|
| budget split | T0 | [pie-budget-share.md](../../examples/cost-and-budget/pie-budget-share.md) |
| cost walk | T0 | [run-rate-waterfall.md](../../examples/cost-and-budget/run-rate-waterfall.md) |
| spend hierarchy | T0 | [treemap-portfolio-breakdown.md](../../examples/cost-and-budget/treemap-portfolio-breakdown.md)<br>[sunburst-lifecycle-share.md](../../examples/cost-and-budget/sunburst-lifecycle-share.md) |
| spend by scope | T1 | [cloud-spend-nested-pie.md](../../examples/cost-and-budget/cloud-spend-nested-pie.md) |
| variance vs plan | T1 | [headcount-variance-diverging-bars.md](../../examples/cost-and-budget/headcount-variance-diverging-bars.md) |

### [dependencies-and-relations](../../goals/dependencies-and-relations.md)

| Scenario | Tier | Example |
|---|---|---|
| service dependencies | T0 | [graph-platform-dependencies.md](../../examples/dependencies-and-relations/graph-platform-dependencies.md) |
| ownership graph | T1 | [service-ownership-circle-graph.md](../../examples/dependencies-and-relations/service-ownership-circle-graph.md) |

### [business-reporting](../../goals/business-reporting.md)

| Scenario | Tier | Example |
|---|---|---|
| periodic results | T0 | [candlestick-quarterly-price-range.md](../../examples/business-reporting/candlestick-quarterly-price-range.md) |
| category comparison | T0 | [comparison-bars.md](../../examples/business-reporting/comparison-bars.md) |

### [product-metrics](../../goals/product-metrics.md)

| Scenario | Tier | Example |
|---|---|---|
| conversion funnel | T0 | [funnel-stage-conversion.md](../../examples/product-metrics/funnel-stage-conversion.md) |
| channel flow | T1 | [sankey-channel-to-fulfilment.md](../../examples/product-metrics/sankey-channel-to-fulfilment.md) |

### [service-reliability](../../goals/service-reliability.md)

| Scenario | Tier | Example |
|---|---|---|
| latency profile | T0 | [boxplot-latency-distribution.md](../../examples/service-reliability/boxplot-latency-distribution.md) |
| slo attainment | T1 | [gauge-sla-attainment.md](../../examples/service-reliability/gauge-sla-attainment.md) |

### [goal-and-status-reporting](../../goals/goal-and-status-reporting.md)

| Scenario | Tier | Example |
|---|---|---|
| goal attainment | T0 | [goal-attainment-background-bars.md](../../examples/goal-and-status-reporting/goal-attainment-background-bars.md)<br>[delivery-score-threshold-bands.md](../../examples/goal-and-status-reporting/delivery-score-threshold-bands.md) |
| kpi dashboard | T1 | [kpi-dashboard.md](../../examples/goal-and-status-reporting/kpi-dashboard.md) |

### [data-exploration](../../goals/data-exploration.md)

| Scenario | Tier | Example |
|---|---|---|
| correlation | T1 | [scatter-segment-correlation.md](../../examples/data-exploration/scatter-segment-correlation.md) |
| multi metric screen | T1 | [parallel-risk-screen.md](../../examples/data-exploration/parallel-risk-screen.md) |

### [incident-management](../../goals/incident-management.md)

| Scenario | Tier | Example |
|---|---|---|
| escalation path | T0 | [tree-support-routing.md](../../examples/incident-management/tree-support-routing.md) |

### [go-to-market](../../goals/go-to-market.md)

| Scenario | Tier | Example |
|---|---|---|
| acquisition mix | T0 | [donut-channel-mix.md](../../examples/go-to-market/donut-channel-mix.md)<br>[lead-source-rose.md](../../examples/go-to-market/lead-source-rose.md) |

### [engineering-operations](../../goals/engineering-operations.md)

| Scenario | Tier | Example |
|---|---|---|
| release pace | T1 | [calendar-release-pace.md](../../examples/engineering-operations/calendar-release-pace.md) |

### [knowledge-and-outline](../../goals/knowledge-and-outline.md)

| Scenario | Tier | Example |
|---|---|---|
| topic flow | T2 | [themeriver-topic-attention.md](../../examples/knowledge-and-outline/themeriver-topic-attention.md) |

### [network-topology](../../goals/network-topology.md)

| Scenario | Tier | Example |
|---|---|---|
| route flows | T2 | [lines-route-flows.md](../../examples/network-topology/lines-route-flows.md) |

### [organization-and-roles](../../goals/organization-and-roles.md)

| Scenario | Tier | Example |
|---|---|---|
| team handoffs | T2 | [chord-team-handoffs.md](../../examples/organization-and-roles/chord-team-handoffs.md) |

### [theme-and-tone](../../goals/theme-and-tone.md)

| Scenario | Tier | Example |
|---|---|---|
| vivid launch share | T2 | [vivid-launch-share.md](../../examples/theme-and-tone/vivid-launch-share.md) |

## Counts

| | |
|---|---|
| Examples using this engine | 39 |
| Goal domains reached | 16 |
| Scenarios | 36 |
| T0 scenarios | 16 |

## Sources

- Engine reference: [`../echarts.md`](../echarts.md)
- Catalog: [`../../catalog/scenarios.md`](../../catalog/scenarios.md)
