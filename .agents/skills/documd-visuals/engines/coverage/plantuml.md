# plantuml coverage ledger

> Generated from `catalog/scenarios.json` plus the curated unit table for this engine.
> Runtime: `@markdown-viewer/draw-uml` 1.5.2 → `@markdown-viewer/drawio2svg` 1.5.5. Last generated: 2026-09-25.

**Units** record what this engine does with each unit of its official documentation — kept, or
excluded with the reason. **Examples by goal** is collected from the catalog, so every link below is
resolvable from this file.

## UML diagrams (9)

| Official type | Level | Disposition | Evidence / example |
|---|---|---|---|
| Class | L1 | kept | 82 fixtures · `software-design/domain-class-model.md` |
| Sequence | L1 | kept | 99 fixtures (12 with `autonumber`) · `software-design/api-interaction-sequence.md` |
| Activity | L1 | kept | 56 fixtures + 13 swimlane + 19 legacy · `process-and-workflow/basic-activity-flow.md`, `approval-workflow-swimlane.md` |
| State | L1 | kept | 32 fixtures · `software-behaviour/order-state-machine.md` |
| Use case | L1 | kept | 25 fixtures · `software-design/use-case-model.md` |
| Component | L1 | kept | 32 fixtures · `software-design/component-decomposition.md` |
| Deployment | L1 | kept | 59 fixtures · `software-behaviour/runtime-deployment-topology.md` |
| Object / Map | L1 | kept | 14 fixtures · `software-design/object-snapshot.md` |
| Timing | **L2** | excluded | Parsed, then passed through as text — no drawing. Use a `sequence` diagram for timing |

## Non-UML diagrams (18)

| Official type | Level | Disposition | Evidence / example |
|---|---|---|---|
| ArchiMate | L1 | kept | 11 fixtures + archimate macros · `enterprise-architecture/archimate-layered-model.md` |
| MindMap | L1 | kept | 27 fixtures · `knowledge-and-outline/topic-mindmap.md` |
| Gantt | L1 | kept | 111 fixtures (largest corpus) · `planning-and-roadmap/release-gantt-plan.md` |
| packetdiag | L1 | kept | 16 fixtures · `network-topology/packet-layout-tcp-header.md` |
| ER / IE (crow's foot) | L1 | kept | 6 fixtures · `data-platform/entity-relationships-crows-foot.md` |
| **WBS** | **L2** | excluded | `@startwbs` parses, exits 0, emits a 342-byte empty SVG (official baseline 4,535 B). Use `@startmindmap` or a boxed rectangle tree |
| **Salt** | **L2** | excluded | Whole block passed through as text. Use an HTML/CSS mockup card |
| ditaa · JSON · YAML · EBNF · Regex · nwdiag · SDL · Chronology · Math · Chart diagram · Files tree | L3 | excluded | No parser rule; the block falls through to `verbatim`. Use a rectangle graph, or a code fence for the raw notation |

## Features (4 official + 5 implementation)

| Unit | Level | Disposition |
|---|---|---|
| Creole rich text (bold, lists, tables, emoji, HTML fragments) | L1 | kept — 47 fixtures |
| Preprocessing (`!include`, `!define`, `!pragma`, `!theme`, `!function`) | L1 | kept — 30 fixtures, 123 `!include` uses |
| Hyperlinks / tooltips | unverified | not used in examples — no fixture coverage |
| OpenIconic / Sprite icons | unverified | not used — icon needs go to `mxgraph.*` stencils |
| `mxgraph.<family>.<icon>` stencils | implementation | **kept — the engine's differentiator**, 9,514 icons / 60 families → `../plantuml-stencils/` |
| Inline style suffixes (`#fill`, `##stroke`, `#c;line:red`) | implementation | kept |
| Nested containers (`cloud`, `node`, `rectangle`, `database`, `package`, `frame`) | implementation | kept |
| Layout selection (`!pragma layout elk\|vizjs`) | implementation | kept; sequence diagrams ignore it (fixed grid) |
| C4 macros (`C4_*`) | implementation | kept (T2) |
| awslib macros (`!include <awslib/...>`) | implementation | kept (T2) — prefer `mxgraph.aws4` stencils for new work |
| `@startuml` type inference | implementation | discouraged — write the explicit type keyword |

## Stencil families (60)

Covered in depth: `AWS4` · `Azure` · `GCP2` · `Kubernetes` · `Networks` · `Cisco` / `Cisco19` ·
`Cisco Safe` · `BPMN` · `EIP` · `Lean Mapping` · `Archimate` / `Archimate 3` · `Mockup` / `Webicons`.
Neutral fallbacks: `Basic`, `Flowchart`. The remaining families are indexed in `../plantuml-stencils/`
and intentionally have no example — domain-specific (PID, Rack, Veeam, …) or superseded (AWS, AWS2, AWS3).

## Examples by goal

41 examples across 13 goal domains.

### [software-design](../../goals/software-design.md)

| Scenario | Tier | Example |
|---|---|---|
| c4 container | T1 | [c4-container-diagram.md](../../examples/software-design/c4-container-diagram.md) |
| component decomposition | T1 | [component-decomposition.md](../../examples/software-design/component-decomposition.md) |
| domain class model | T1 | [domain-class-model.md](../../examples/software-design/domain-class-model.md) |
| object snapshot | T1 | [object-snapshot.md](../../examples/software-design/object-snapshot.md) |
| package layering | T1 | [package-layering.md](../../examples/software-design/package-layering.md) |
| sysml block definition | T1 | [sysml-block-definition.md](../../examples/software-design/sysml-block-definition.md) |
| use case model | T1 | [use-case-model.md](../../examples/software-design/use-case-model.md) |

### [software-behaviour](../../goals/software-behaviour.md)

| Scenario | Tier | Example |
|---|---|---|
| api interaction sequence | T1 | [api-interaction-sequence.md](../../examples/software-behaviour/api-interaction-sequence.md) |
| deployment topology | T1 | [runtime-deployment-topology.md](../../examples/software-behaviour/runtime-deployment-topology.md) |
| eip message flow | T1 | [eip-message-flow.md](../../examples/software-behaviour/eip-message-flow.md) |
| event driven flow | T1 | [serverless-event-driven.md](../../examples/software-behaviour/serverless-event-driven.md) |
| state machine | T1 | [order-state-machine.md](../../examples/software-behaviour/order-state-machine.md) |

### [dependencies-and-relations](../../goals/dependencies-and-relations.md)

| Scenario | Tier | Example |
|---|---|---|
| dependency graph | T1 | [dependency-graph.md](../../examples/dependencies-and-relations/dependency-graph.md)<br>[clustered-architecture.md](../../examples/dependencies-and-relations/clustered-architecture.md) |
| causal tree | T1 | [fishbone-causal-tree.md](../../examples/dependencies-and-relations/fishbone-causal-tree.md) |
| relationship network | T1 | [relationship-network-neato.md](../../examples/dependencies-and-relations/relationship-network-neato.md) |
| tabular nodes | T1 | [table-node-structures.md](../../examples/dependencies-and-relations/table-node-structures.md) |

### [cloud-architecture](../../goals/cloud-architecture.md)

| Scenario | Tier | Example |
|---|---|---|
| aws serverless | T2 | [aws-serverless-architecture.md](../../examples/cloud-architecture/aws-serverless-architecture.md) |
| iot platform | T2 | [iot-platform.md](../../examples/cloud-architecture/iot-platform.md) |
| kubernetes platform | T2 | [kubernetes-platform.md](../../examples/cloud-architecture/kubernetes-platform.md) |
| observability stack | T2 | [operations-observability-aws.md](../../examples/cloud-architecture/operations-observability-aws.md) |

### [process-and-workflow](../../goals/process-and-workflow.md)

| Scenario | Tier | Example |
|---|---|---|
| approval workflow | T1 | [approval-workflow-swimlane.md](../../examples/process-and-workflow/approval-workflow-swimlane.md) |
| cicd pipeline | T1 | [cicd-pipeline.md](../../examples/process-and-workflow/cicd-pipeline.md) |
| basic activity flow | T1 | [basic-activity-flow.md](../../examples/process-and-workflow/basic-activity-flow.md) |

### [data-platform](../../goals/data-platform.md)

| Scenario | Tier | Example |
|---|---|---|
| entity relationships | T2 | [entity-relationships-crows-foot.md](../../examples/data-platform/entity-relationships-crows-foot.md) |
| lakehouse architecture | T2 | [data-platform-lakehouse.md](../../examples/data-platform/data-platform-lakehouse.md) |
| ml pipeline | T2 | [machine-learning-pipeline.md](../../examples/data-platform/machine-learning-pipeline.md) |

### [network-topology](../../goals/network-topology.md)

| Scenario | Tier | Example |
|---|---|---|
| packet layout | T2 | [packet-layout-tcp-header.md](../../examples/network-topology/packet-layout-tcp-header.md) |
| enterprise network | T2 | [network-topology-enterprise.md](../../examples/network-topology/network-topology-enterprise.md) |
| radial network | T2 | [radial-hub-network.md](../../examples/network-topology/radial-hub-network.md) |

### [security-and-compliance](../../goals/security-and-compliance.md)

| Scenario | Tier | Example |
|---|---|---|
| security baseline | T2 | [security-baseline-aws.md](../../examples/security-and-compliance/security-baseline-aws.md) |
| threat model | T2 | [threat-model-trust-boundaries.md](../../examples/security-and-compliance/threat-model-trust-boundaries.md) |
| zero trust access | T2 | [zero-trust-access.md](../../examples/security-and-compliance/zero-trust-access.md) |

### [migration-and-rollout](../../goals/migration-and-rollout.md)

| Scenario | Tier | Example |
|---|---|---|
| migration programme | T2 | [cloud-migration-programme.md](../../examples/migration-and-rollout/cloud-migration-programme.md) |
| work breakdown | T2 | [work-breakdown-structure.md](../../examples/migration-and-rollout/work-breakdown-structure.md) |

### [enterprise-architecture](../../goals/enterprise-architecture.md)

| Scenario | Tier | Example |
|---|---|---|
| archimate layered model | T2 | [archimate-layered-model.md](../../examples/enterprise-architecture/archimate-layered-model.md) |
| capability map | T2 | [capability-map.md](../../examples/enterprise-architecture/capability-map.md) |

### [theme-and-tone](../../goals/theme-and-tone.md)

| Scenario | Tier | Example |
|---|---|---|
| editorial policy flow | T2 | [editorial-policy-flow.md](../../examples/theme-and-tone/editorial-policy-flow.md) |
| print handout graph | T2 | [print-handout-graph.md](../../examples/theme-and-tone/print-handout-graph.md) |

### [knowledge-and-outline](../../goals/knowledge-and-outline.md)

| Scenario | Tier | Example |
|---|---|---|
| topic mindmap | T2 | [topic-mindmap.md](../../examples/knowledge-and-outline/topic-mindmap.md) |

### [planning-and-roadmap](../../goals/planning-and-roadmap.md)

| Scenario | Tier | Example |
|---|---|---|
| release gantt | T2 | [release-gantt-plan.md](../../examples/planning-and-roadmap/release-gantt-plan.md) |

## Counts

| | |
|---|---|
| Examples using this engine | 41 |
| Goal domains reached | 13 |
| Scenarios | 40 |
| T0 scenarios | 0 |

## Sources

- Engine reference: [`../plantuml.md`](../plantuml.md)
- Catalog: [`../../catalog/scenarios.md`](../../catalog/scenarios.md)
