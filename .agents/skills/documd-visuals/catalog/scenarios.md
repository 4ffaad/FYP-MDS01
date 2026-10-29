# Scenario catalog

> Generated from `catalog/scenarios.tsv` — edit the TSV, not this file.

**242 examples · 183 scenarios · 31 domains.**

| Tier | Count |
|---|---|
| T0 | 20 |
| T1 | 85 |
| T2 | 78 |
| T3 | 0 |

## A — data & metrics

### `business-reporting`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| revenue mix | infographic, vega | T0 | 4.7 | `business-reporting/regional-revenue-split.md`<br>`business-reporting/product-mix-donut-badges.md`<br>`business-reporting/subscription-tiers-wheel.md`<br>`business-reporting/quarterly-share-normalized-stack.md` |
| periodic results | echarts, infographic | T0 | 4.4 | `business-reporting/quarterly-results-columns.md`<br>`business-reporting/revenue-staircase-plan.md`<br>`business-reporting/candlestick-quarterly-price-range.md` |
| category comparison | echarts, infographic | T0 | 4.1 | `business-reporting/comparison-bars.md`<br>`business-reporting/channel-performance-comparison.md` |
| revenue concentration | vega | T1 | 3.65 | `business-reporting/revenue-concentration-topk-others.md` |
| goal progress | infographic | T1 | 3.45 | `business-reporting/sustainability-goals-progress.md` |

### `delivery-throughput`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| team capacity | echarts, infographic, vega | T0 | 4.7 | `delivery-throughput/pictorialbar-capacity-symbols.md`<br>`delivery-throughput/support-capacity-units.md`<br>`delivery-throughput/team-capacity-ramp.md`<br>`delivery-throughput/team-throughput-bars.md` |
| release packet profile | vega | T0 | 4.55 | `delivery-throughput/release-duration-distribution.md`<br>`delivery-throughput/release-size-violin.md`<br>`delivery-throughput/build-time-candles.md`<br>`delivery-throughput/request-size-distribution.md`<br>`delivery-throughput/asset-size-packing.md`<br>`delivery-throughput/release-time-split-donut.md` |
| rank movement | echarts, vega | T0 | 4.1 | `delivery-throughput/team-rank-bump-chart.md`<br>`delivery-throughput/rank-movement-over-time.md`<br>`delivery-throughput/adoption-shift-slope.md` |
| backlog flow | echarts, vega | T1 | 3.8 | `delivery-throughput/backlog-ranking-dataset.md`<br>`delivery-throughput/demand-overview-detail.md` |
| throughput vs cycle | echarts, vega | T1 | 3.8 | `delivery-throughput/growth-vs-efficiency-path.md`<br>`delivery-throughput/throughput-band-range-area.md` |
| plan vs actual | vega | T1 | 3.65 | `delivery-throughput/plan-to-actual-bridge.md` |
| work mix | echarts | T1 | 3.65 | `delivery-throughput/engineering-time-100pct-bars.md` |

### `cost-and-budget`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| budget split | echarts, infographic | T0 | 4.4 | `cost-and-budget/pie-budget-share.md`<br>`cost-and-budget/budget-allocation-donut.md`<br>`cost-and-budget/cost-structure-split.md` |
| cost walk | echarts, infographic | T0 | 4.4 | `cost-and-budget/run-rate-waterfall.md`<br>`cost-and-budget/cost-reduction-waterfall.md`<br>`cost-and-budget/budget-drawdown-waterfall.md` |
| spend hierarchy | echarts, vega | T0 | 4.1 | `cost-and-budget/treemap-portfolio-breakdown.md`<br>`cost-and-budget/sunburst-lifecycle-share.md`<br>`cost-and-budget/cost-center-treemap.md` |
| cost vs capacity | vega | T1 | 3.65 | `cost-and-budget/capacity-cost-dual-axis.md` |
| spend by scope | echarts | T1 | 3.65 | `cost-and-budget/cloud-spend-nested-pie.md` |
| variance vs plan | echarts | T1 | 3.65 | `cost-and-budget/headcount-variance-diverging-bars.md` |

### `go-to-market`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| acquisition mix | echarts, infographic | T0 | 4.4 | `go-to-market/donut-channel-mix.md`<br>`go-to-market/lead-source-rose.md`<br>`go-to-market/traffic-source-mix-split.md` |
| market entry | infographic | T1 | 3.45 | `go-to-market/market-entry-swot.md` |
| partner onboarding | infographic | T1 | 3.45 | `go-to-market/partner-onboarding-timeline.md` |
| partner tiers | infographic | T1 | 3.45 | `go-to-market/partner-tiers-pyramid.md` |
| sales pipeline | infographic | T1 | 3.45 | `go-to-market/sales-qualification-gates.md` |

### `product-metrics`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| conversion funnel | echarts, infographic | T0 | 4.4 | `product-metrics/funnel-stage-conversion.md`<br>`product-metrics/conversion-funnel-journey.md`<br>`product-metrics/claims-pipeline-funnel.md` |
| channel flow | echarts | T1 | 3.65 | `product-metrics/sankey-channel-to-fulfilment.md` |
| adoption trend | infographic | T1 | 3.45 | `product-metrics/feature-adoption-trend.md` |
| customer journey | infographic | T1 | 3.45 | `product-metrics/customer-health-journey.md` |
| experiment loop | infographic | T1 | 3.45 | `product-metrics/growth-experiment-loop.md` |
| onboarding journey | infographic | T1 | 3.45 | `product-metrics/customer-onboarding-journey.md` |

### `service-reliability`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| latency profile | echarts, vega | T0 | 4.4 | `service-reliability/boxplot-latency-distribution.md`<br>`service-reliability/latency-beeswarm-regions.md`<br>`service-reliability/service-latency-density.md`<br>`service-reliability/before-after-latency-gap.md`<br>`service-reliability/service-drift-lasagna.md` |
| forecast band | vega | T1 | 3.95 | `service-reliability/forecast-range-band.md`<br>`service-reliability/team-variance-interval.md` |
| error budget | vega | T1 | 3.65 | `service-reliability/error-budget-burn-trail.md` |
| slo attainment | echarts | T1 | 3.65 | `service-reliability/gauge-sla-attainment.md` |
| threshold monitoring | vega | T1 | 3.65 | `service-reliability/threshold-breach-annotation.md` |
| reliability maturity | infographic | T1 | 3.45 | `service-reliability/reliability-maturity-ladder.md` |

### `goal-and-status-reporting`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| goal attainment | echarts, vega | T0 | 4.1 | `goal-and-status-reporting/goal-attainment-background-bars.md`<br>`goal-and-status-reporting/target-attainment-bullet.md`<br>`goal-and-status-reporting/delivery-score-threshold-bands.md` |
| kpi dashboard | echarts | T1 | 3.65 | `goal-and-status-reporting/kpi-dashboard.md` |
| leadership board | infographic | T1 | 3.45 | `goal-and-status-reporting/leadership-metric-board.md` |
| metric board | html-css | T1 | 3.45 | `goal-and-status-reporting/metric-snapshot-board.md` |
| programme status | infographic | T1 | 3.45 | `goal-and-status-reporting/program-status-ribbons.md` |

### `ops-monitoring`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| incident load | echarts, vega | T0 | 4.1 | `ops-monitoring/heatmap-incident-load.md`<br>`ops-monitoring/alert-density-contours.md`<br>`ops-monitoring/incident-rate-stripes.md` |
| service profile | echarts, vega | T0 | 4.1 | `ops-monitoring/radar-capability-profile.md`<br>`ops-monitoring/capability-comparison-radar.md`<br>`ops-monitoring/risk-profile-parallel.md` |
| support load | echarts, infographic | T0 | 4.1 | `ops-monitoring/support-volume-radial-bars.md`<br>`ops-monitoring/support-ticket-mix-pie.md` |
| anomaly scan | echarts | T1 | 3.65 | `ops-monitoring/effectscatter-outlier-alerts.md` |
| incident trend | echarts | T1 | 3.65 | `ops-monitoring/incident-trend-stacked-area.md` |
| metric trend | echarts | T1 | 3.65 | `ops-monitoring/trend-line-multi-series.md` |
| service scorecard | echarts | T1 | 3.65 | `ops-monitoring/matrix-service-scorecards.md` |

### `data-exploration`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| distribution comparison | vega | T1 | 3.95 | `data-exploration/metric-distribution-small-multiples.md`<br>`data-exploration/stripplot-region-spread.md` |
| correlation | echarts, vega | T1 | 3.8 | `data-exploration/metric-correlation-matrix.md`<br>`data-exploration/scatter-segment-correlation.md` |
| composition over time | vega | T1 | 3.65 | `data-exploration/streamgraph-topic-composition.md` |
| deviation analysis | vega | T1 | 3.65 | `data-exploration/deviation-from-average.md` |
| missing data | vega | T1 | 3.65 | `data-exploration/imputed-gap-trend.md` |
| multi metric screen | echarts | T1 | 3.65 | `data-exploration/parallel-risk-screen.md` |
| regression fit | vega | T1 | 3.65 | `data-exploration/regression-trend-fit.md` |
| small multiples | vega | T1 | 3.65 | `data-exploration/segment-pattern-small-multiples.md` |

## B — process & systems

### `dependencies-and-relations`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| service dependencies | echarts, infographic, vega | T0 | 4.7 | `dependencies-and-relations/platform-dependency-graph.md`<br>`dependencies-and-relations/service-dependency-network.md`<br>`dependencies-and-relations/service-call-force-map.md`<br>`dependencies-and-relations/graph-platform-dependencies.md` |
| dependency graph | plantuml | T1 | 3.75 | `dependencies-and-relations/dependency-graph.md`<br>`dependencies-and-relations/clustered-architecture.md` |
| import coupling | vega | T1 | 3.65 | `dependencies-and-relations/module-import-arcs.md` |
| ownership graph | echarts | T1 | 3.65 | `dependencies-and-relations/service-ownership-circle-graph.md` |
| causal tree | plantuml | T1 | 3.45 | `dependencies-and-relations/fishbone-causal-tree.md` |
| relationship network | plantuml | T1 | 3.45 | `dependencies-and-relations/relationship-network-neato.md` |
| tabular nodes | plantuml | T1 | 3.45 | `dependencies-and-relations/table-node-structures.md` |

### `incident-management`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| escalation path | echarts, infographic | T0 | 4.7 | `incident-management/incident-escalation-path.md`<br>`incident-management/support-escalation-pyramid.md`<br>`incident-management/release-blockers-escalation.md`<br>`incident-management/tree-support-routing.md` |
| change control | infographic | T1 | 3.45 | `incident-management/change-request-columns.md` |
| field playbook | infographic | T1 | 3.45 | `incident-management/field-ops-playbook.md` |
| incident review | html-css | T1 | 3.45 | `incident-management/incident-review-card.md` |
| incident runbook | infographic | T1 | 3.45 | `incident-management/incident-response-runbook.md` |
| triage filters | infographic | T1 | 3.45 | `incident-management/bug-triage-filters.md` |

### `engineering-operations`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| deploy rhythm | vega | T1 | 3.95 | `engineering-operations/deploy-frequency-calendar.md`<br>`engineering-operations/deploy-punchcard-weekday-hour.md` |
| ops rhythm | infographic | T1 | 3.75 | `engineering-operations/quarterly-business-rhythm.md`<br>`engineering-operations/operating-cycle-loop.md` |
| shift handover | infographic | T1 | 3.75 | `engineering-operations/support-shift-handover.md`<br>`engineering-operations/shift-handover-timeline.md` |
| release pace | echarts | T1 | 3.65 | `engineering-operations/calendar-release-pace.md` |
| launch readiness | infographic | T1 | 3.45 | `engineering-operations/launch-readiness-checklist.md` |
| oncall coverage | infographic | T1 | 3.45 | `engineering-operations/oncall-coverage-wheel.md` |
| ops checklist | infographic | T1 | 3.45 | `engineering-operations/daily-ops-checklist-columns.md` |
| standup | infographic | T1 | 3.45 | `engineering-operations/sprint-standup-talking-points.md` |

### `process-and-workflow`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| approval workflow | plantuml | T1 | 3.6 | `process-and-workflow/approval-workflow-swimlane.md` |
| cicd pipeline | plantuml | T1 | 3.6 | `process-and-workflow/cicd-pipeline.md` |
| approval path | infographic | T1 | 3.45 | `process-and-workflow/procurement-approval-path.md` |
| basic activity flow | plantuml | T1 | 3.45 | `process-and-workflow/basic-activity-flow.md` |
| returns processing | infographic | T1 | 3.45 | `process-and-workflow/returns-processing-snake.md` |

### `software-behaviour`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| api interaction sequence | plantuml | T1 | 3.6 | `software-behaviour/api-interaction-sequence.md` |
| deployment topology | plantuml | T1 | 3.6 | `software-behaviour/runtime-deployment-topology.md` |
| eip message flow | plantuml | T1 | 3.6 | `software-behaviour/eip-message-flow.md` |
| event driven flow | plantuml | T1 | 3.6 | `software-behaviour/serverless-event-driven.md` |
| state machine | plantuml | T1 | 3.6 | `software-behaviour/order-state-machine.md` |

### `software-design`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| c4 container | plantuml | T1 | 3.6 | `software-design/c4-container-diagram.md` |
| component decomposition | plantuml | T1 | 3.6 | `software-design/component-decomposition.md` |
| domain class model | plantuml | T1 | 3.6 | `software-design/domain-class-model.md` |
| object snapshot | plantuml | T1 | 3.45 | `software-design/object-snapshot.md` |
| package layering | plantuml | T1 | 3.45 | `software-design/package-layering.md` |
| sysml block definition | plantuml | T1 | 3.45 | `software-design/sysml-block-definition.md` |
| use case model | plantuml | T1 | 3.45 | `software-design/use-case-model.md` |

### `system-architecture`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| complex system blueprint | html-css | T1 | 3.45 | `system-architecture/complex-system-blueprint.md` |
| layer stack | html-css | T1 | 3.45 | `system-architecture/layer-stack.md` |
| layered with wings | html-css | T1 | 3.45 | `system-architecture/layered-with-wings.md` |
| nested zones | html-css | T1 | 3.45 | `system-architecture/nested-zones.md` |
| operations overview | html-css | T1 | 3.45 | `system-architecture/operations-overview.md` |
| pipeline stages | html-css | T1 | 3.45 | `system-architecture/pipeline-stages.md` |
| request paths | html-css | T1 | 3.45 | `system-architecture/request-paths.md` |
| service catalog | html-css | T1 | 3.45 | `system-architecture/service-catalog.md` |

## C — infrastructure & governance

### `organization-and-roles`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| org structure | infographic, vega | T0 | 4.1 | `organization-and-roles/platform-org-structure.md`<br>`organization-and-roles/team-reporting-tree.md`<br>`organization-and-roles/org-chart-radial-tree.md` |
| team handoffs | echarts | T2 | 3.35 | `organization-and-roles/chord-team-handoffs.md` |
| workforce profile | vega | T2 | 3.35 | `organization-and-roles/workforce-seniority-pyramid.md` |
| capability coverage | infographic | T2 | 3.15 | `organization-and-roles/team-capability-icon-grid.md` |
| capability maturity | infographic | T2 | 3.15 | `organization-and-roles/capability-pyramid-framework.md` |
| org update | html-css | T2 | 3.15 | `organization-and-roles/org-update-card.md` |

### `people-and-hiring`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| skills progression | infographic | T1 | 3.45 | `people-and-hiring/engineer-skill-progression.md`<br>`people-and-hiring/certification-study-roadmap.md` |
| career ladder | infographic | T2 | 3.15 | `people-and-hiring/career-growth-ladder.md` |
| hiring loop | infographic | T2 | 3.15 | `people-and-hiring/hiring-loop-checklist.md` |
| hiring plan | infographic | T2 | 3.15 | `people-and-hiring/hiring-plan-roadmap.md` |
| onboarding programme | infographic | T2 | 3.15 | `people-and-hiring/onboarding-milestone-grid.md` |
| onboarding tasks | infographic | T2 | 3.15 | `people-and-hiring/onboarding-task-progress.md` |

### `network-topology`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| route flows | echarts | T2 | 3.35 | `network-topology/lines-route-flows.md` |
| packet layout | plantuml | T2 | 3.3 | `network-topology/packet-layout-tcp-header.md` |
| enterprise network | plantuml | T2 | 3.15 | `network-topology/network-topology-enterprise.md` |
| radial network | plantuml | T2 | 3.15 | `network-topology/radial-hub-network.md` |

### `data-platform`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| entity relationships | plantuml | T2 | 3.3 | `data-platform/entity-relationships-crows-foot.md` |
| lakehouse architecture | plantuml | T2 | 3.15 | `data-platform/data-platform-lakehouse.md` |
| ml pipeline | plantuml | T2 | 3.15 | `data-platform/machine-learning-pipeline.md` |

### `cloud-architecture`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| aws serverless | plantuml | T2 | 3.15 | `cloud-architecture/aws-serverless-architecture.md` |
| iot platform | plantuml | T2 | 3.15 | `cloud-architecture/iot-platform.md` |
| kubernetes platform | plantuml | T2 | 3.15 | `cloud-architecture/kubernetes-platform.md` |
| migration options | infographic | T2 | 3.15 | `cloud-architecture/cloud-migration-approaches.md` |
| observability stack | plantuml | T2 | 3.15 | `cloud-architecture/operations-observability-aws.md` |

### `enterprise-architecture`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| archimate layered model | plantuml | T2 | 3.15 | `enterprise-architecture/archimate-layered-model.md` |
| capability map | plantuml | T2 | 3.15 | `enterprise-architecture/capability-map.md` |
| stakeholder map | infographic | T2 | 3.15 | `enterprise-architecture/stakeholder-circle-wheel.md` |

### `security-and-compliance`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| audit trail | infographic | T2 | 3.15 | `security-and-compliance/audit-trail-checkpoints.md` |
| compliance audit | html-css | T2 | 3.15 | `security-and-compliance/compliance-audit-card.md` |
| compliance evidence | infographic | T2 | 3.15 | `security-and-compliance/compliance-evidence-zigzag.md` |
| hardening sprint | infographic | T2 | 3.15 | `security-and-compliance/security-hardening-sprint.md` |
| risk register | html-css | T2 | 3.15 | `security-and-compliance/risk-register-card.md` |
| security baseline | plantuml | T2 | 3.15 | `security-and-compliance/security-baseline-aws.md` |
| threat model | plantuml | T2 | 3.15 | `security-and-compliance/threat-model-trust-boundaries.md` |
| zero trust access | plantuml | T2 | 3.15 | `security-and-compliance/zero-trust-access.md` |

## D — knowledge & expression

### `knowledge-and-outline`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| keyword cloud | infographic, vega | T0 | 4.1 | `knowledge-and-outline/topic-emphasis-wordcloud.md`<br>`knowledge-and-outline/survey-themes-rotated-cloud.md`<br>`knowledge-and-outline/topic-landscape-wordcloud.md` |
| content mix | vega | T2 | 3.35 | `knowledge-and-outline/catalog-sunburst-share.md` |
| topic flow | echarts | T2 | 3.35 | `knowledge-and-outline/themeriver-topic-attention.md` |
| concept relations | infographic | T2 | 3.15 | `knowledge-and-outline/capability-relationship-map.md` |
| knowledge map | infographic | T2 | 3.15 | `knowledge-and-outline/enterprise-knowledge-map.md` |
| knowledge tree | infographic | T2 | 3.15 | `knowledge-and-outline/department-capability-tree.md` |
| topic mindmap | plantuml | T2 | 3.15 | `knowledge-and-outline/topic-mindmap.md` |

### `comparison-and-selection`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| priority quadrant | infographic | T1 | 3.75 | `comparison-and-selection/backlog-priority-quadrant.md`<br>`comparison-and-selection/scenario-planning-quadrant.md`<br>`comparison-and-selection/test-automation-quadrant.md` |
| architecture options | infographic | T2 | 3.15 | `comparison-and-selection/monolith-vs-modular.md` |
| build or buy | infographic | T2 | 3.15 | `comparison-and-selection/buy-vs-build-comparison.md` |
| decision record | html-css | T2 | 3.15 | `comparison-and-selection/decision-comparison-card.md` |
| operating model | infographic | T2 | 3.15 | `comparison-and-selection/operating-model-option-map.md` |
| packaging options | infographic | T2 | 3.15 | `comparison-and-selection/packaging-choice-cards.md` |
| release tradeoffs | infographic | T2 | 3.15 | `comparison-and-selection/release-plan-tradeoff-fold.md` |
| vendor scorecard | infographic | T2 | 3.15 | `comparison-and-selection/vendor-selection-scorecard.md` |

### `planning-and-roadmap`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| release schedule | vega | T2 | 3.35 | `planning-and-roadmap/release-window-schedule.md` |
| milestones | infographic | T2 | 3.15 | `planning-and-roadmap/platform-milestone-timeline.md` |
| planning cycle | infographic | T2 | 3.15 | `planning-and-roadmap/quarterly-planning-cycle.md` |
| product roadmap | infographic | T2 | 3.15 | `planning-and-roadmap/product-roadmap-sequence.md` |
| release gantt | plantuml | T2 | 3.15 | `planning-and-roadmap/release-gantt-plan.md` |
| roadmap board | html-css | T2 | 3.15 | `planning-and-roadmap/delivery-roadmap-board.md` |
| strategy focus | infographic | T2 | 3.15 | `planning-and-roadmap/strategy-focus-wheel.md` |

### `theme-and-tone`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| vivid launch share | echarts | T2 | 3.35 | `theme-and-tone/vivid-launch-share.md` |
| accessible service mix | infographic | T2 | 3.15 | `theme-and-tone/accessible-service-mix.md` |
| editorial policy flow | plantuml | T2 | 3.15 | `theme-and-tone/editorial-policy-flow.md` |
| print handout graph | plantuml | T2 | 3.15 | `theme-and-tone/print-handout-graph.md` |

### `migration-and-rollout`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| migration programme | plantuml | T2 | 3.3 | `migration-and-rollout/cloud-migration-programme.md` |
| work breakdown | plantuml | T2 | 3.3 | `migration-and-rollout/work-breakdown-structure.md` |
| cutover window | infographic | T2 | 3.15 | `migration-and-rollout/migration-cutover-window.md` |
| launch effort | infographic | T2 | 3.15 | `migration-and-rollout/launch-effort-curve.md` |
| migration waves | infographic | T2 | 3.15 | `migration-and-rollout/data-platform-migration-waves.md` |
| rollout phases | infographic | T2 | 3.15 | `migration-and-rollout/device-rollout-phases.md` |
| service lifecycle | infographic | T2 | 3.15 | `migration-and-rollout/service-lifecycle-wheel.md` |

### `catalogues-and-inventories`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| service catalogue | infographic | T2 | 3.15 | `catalogues-and-inventories/service-offerings-grid.md` |
| support tiers | infographic | T2 | 3.15 | `catalogues-and-inventories/support-tier-entitlements.md` |
| tooling inventory | infographic | T2 | 3.15 | `catalogues-and-inventories/tooling-standard-inventory.md` |

### `customer-and-partner-comms`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| customer story | html-css | T2 | 3.15 | `customer-and-partner-comms/customer-story-card.md` |
| education module | html-css | T2 | 3.15 | `customer-and-partner-comms/education-module-card.md` |
| news bulletin | html-css | T2 | 3.15 | `customer-and-partner-comms/news-bulletin-card.md` |
| partner brief | html-css | T2 | 3.15 | `customer-and-partner-comms/partner-brief-card.md` |
| sales brief | html-css | T2 | 3.15 | `customer-and-partner-comms/sales-brief-card.md` |

### `internal-documents`

| Scenario | Engines | Tier | W | Example |
|---|---|---|---|---|
| committee charter | infographic | T2 | 3.15 | `internal-documents/board-committee-charter.md` |
| executive brief | html-css | T2 | 3.15 | `internal-documents/executive-brief-summary.md` |
| key quote | html-css | T2 | 3.15 | `internal-documents/key-quote-card.md` |
| policy memo | html-css | T2 | 3.15 | `internal-documents/policy-memo-card.md` |
| principles checklist | infographic | T2 | 3.15 | `internal-documents/culture-principles-checklist.md` |
| research abstract | html-css | T2 | 3.15 | `internal-documents/research-abstract-card.md` |
