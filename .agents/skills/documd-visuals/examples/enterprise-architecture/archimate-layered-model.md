# ArchiMate Layered Model

**Best for**: enterprise architecture where business, application and technology layers must be shown together
**Avoid when**: the audience only needs one system (use a component or cloud example)
**Answers**: which business services exist, which applications realise them, and which technology supports those

```plantuml
@startuml
skinparam DefaultFontColor #1f2937
skinparam ArrowColor #5b6b8c
skinparam ArrowFontColor #1f2937
skinparam RectangleBackgroundColor #eef2fb
skinparam RectangleBorderColor #5b6b8c
skinparam RectangleFontColor #1f2937
skinparam ComponentBackgroundColor #eef2fb
skinparam ComponentBorderColor #5b6b8c
skinparam ComponentFontColor #1f2937
skinparam ClassBackgroundColor #eef2fb
skinparam ClassBorderColor #5b6b8c
skinparam ClassFontColor #1f2937
skinparam UsecaseBackgroundColor #eef2fb
skinparam UsecaseBorderColor #5b6b8c
skinparam UsecaseFontColor #1f2937
skinparam DatabaseBackgroundColor #eef2fb
skinparam DatabaseBorderColor #5b6b8c
skinparam DatabaseFontColor #1f2937
skinparam NodeBackgroundColor #eef2fb
skinparam NodeBorderColor #5b6b8c
skinparam NodeFontColor #1f2937
skinparam ActorBackgroundColor #eef2fb
skinparam ActorBorderColor #5b6b8c
skinparam ActorFontColor #1f2937
skinparam StateBackgroundColor #eef2fb
skinparam StateBorderColor #5b6b8c
skinparam StateFontColor #1f2937
skinparam ArtifactBackgroundColor #eef2fb
skinparam ArtifactBorderColor #5b6b8c
skinparam ArtifactFontColor #1f2937
skinparam CloudBackgroundColor #eef2fb
skinparam CloudBorderColor #5b6b8c
skinparam CloudFontColor #1f2937
skinparam FolderBackgroundColor #eef2fb
skinparam FolderBorderColor #5b6b8c
skinparam FolderFontColor #1f2937
skinparam PackageBackgroundColor #eef2fb
skinparam PackageBorderColor #5b6b8c
skinparam NoteBackgroundColor #dfe5fb
skinparam NoteBorderColor #5b6b8c
skinparam NoteFontColor #1f2937
skinparam stereotypeABackgroundColor #d9e3f4
skinparam stereotypeABorderColor #5b6b8c
skinparam stereotypeCBackgroundColor #d9e3f4
skinparam stereotypeCBorderColor #5b6b8c
skinparam stereotypeEBackgroundColor #d9e3f4
skinparam stereotypeEBorderColor #5b6b8c
skinparam stereotypeIBackgroundColor #d9e3f4
skinparam stereotypeIBorderColor #5b6b8c
!include <archimate/Archimate>
title Payments Platform — ArchiMate Layers

' ── Motivation ──
Motivation_Driver(regulatoryDriver, "Instant payment regulation")
Motivation_Goal(cutoffGoal, "Settle 24/7 in under 10 seconds")
Motivation_Requirement(req24x7, "Continuous availability")
Rel_Influence(regulatoryDriver, cutoffGoal)
Rel_Realization(cutoffGoal, req24x7)

' ── Business layer ──
Business_Actor(customer, "Payer")
Business_Service(payService, "Payment Initiation Service")
Business_Process(initProcess, "Initiate payment")
Business_Object(payInstruction, "Payment instruction")
Business_Role(opsRole, "Payment Operations")

Rel_Assignment(customer, initProcess)
Rel_Serving(initProcess, payService)
Rel_Access(initProcess, payInstruction)

' ── Application layer ──
Application_Component(apiGateway, "Payment API Gateway")
Application_Component(paymentEngine, "Payment Engine")
Application_Service(settlementSvc, "Instant settlement")
Application_DataObject(ledger, "Ledger entry")
Application_Interface(apiInterface, "REST /payments")

Rel_Realization(apiGateway, apiInterface)
Rel_Serving(apiInterface, payService)
Rel_Flow(apiGateway, paymentEngine)
Rel_Realization(paymentEngine, settlementSvc)
Rel_Access(paymentEngine, ledger)

' ── Technology layer ──
Technology_Node(k8sCluster, "Container platform")
Technology_SystemSoftware(runtime, "JVM runtime")
Technology_CommunicationNetwork(network, "Private network")

Rel_Serving(k8sCluster, runtime)
Rel_Realization(runtime, paymentEngine)
Rel_Serving(network, k8sCluster)

' ── Governance/cross-cutting ──
Grouping(securityGroup, "Security controls")
Technology_Service(hsm, "Key management")
Rel_Serving(hsm, securityGroup)
Rel_Association(securityGroup, paymentEngine)

note right of paymentEngine
  layers read top-down:
  WHY (motivation) -> WHAT (business)
  -> HOW (application) -> WITH WHAT (technology)
end note
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `!include <archimate/Archimate>` | Loads the ArchiMate stdlib macros (**required** before any macro call) |
| `Business_*` / `Application_*` / `Technology_*` | Layer element macros — elements: `_Actor` `_Role` `_Service` `_Process` `_Component` `_Interface` `_Function` `_Event` `_Object` `_Node` `_Device` `_SystemSoftware` `_CommunicationNetwork` |
| `Motivation_*` / `Strategy_*` / `Implementation_*` | Why-layer and transformation elements (`_Driver` `_Goal` `_Requirement` `_Capability` `_ValueStream` `_WorkPackage` `_Deliverable` `_Plateau` `_Gap`) |
| `Rel_*` | Relationships: `Rel_Serving` `Rel_Realization` `Rel_Access` `Rel_Flow` `Rel_Composition` `Rel_Aggregation` `Rel_Assignment` `Rel_Triggering` `Rel_Specialization` `Rel_Association` `Rel_Influence` |
| `Grouping(alias, "Name")` | ArchiMate grouping (use for cross-cutting concerns) |
| Layer order | Draw motivation on top, business → application → technology downward; the nesting *is* the model |

## Data Shape

Four layers of nodes plus relationship edges. Every application element should realise exactly one business service
(via `Rel_Serving`), and every technology element should serve an application element — gaps in those chains are the
findings an EA review looks for.

## Pitfalls

- ❌ Forgetting `!include <archimate/Archimate>` → ✅ nothing renders correctly without it
- ❌ Using `-->` for ArchiMate relationships → ✅ use `Rel_*`: the relationship *type* carries the meaning
- ❌ Putting every element in one flat line → ✅ group by layer (rectangles or ordering) so the model reads as a stack
- ❌ Modelling the org chart instead of capabilities → ✅ ArchiMate is about services and realisation, not reporting lines

## Alternatives

| Variant | Use instead |
|---|---|
| Capability heat map / value stream only | `capability-map.md` |
| Solution architecture with cloud icons | `aws-serverless-architecture.md` |
| Migration planning (plateaus, gaps, work packages) | Same macros with `Implementation_*` + `Rel_Triggering` |

<!-- source: draw-uml archimate macro parser (L1, 11 fixtures; macros verified against parsers/archimate-macros.ts) -->
