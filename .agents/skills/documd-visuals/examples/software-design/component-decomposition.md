# Component Decomposition

**Best for**: showing which services/components exist and their provided/required interfaces
**Avoid when**: the reader wants the class-level detail inside a component (use a class diagram)
**Answers**: what the system is made of, and which interfaces connect the parts

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
title Checkout Platform — Component View

package "Frontend" {
  component [Web App] as web
  component [Mobile App] as mobile
}

package "Edge" {
  component [API Gateway] as gw
  component [BFF] as bff
}

package "Core Services" {
  component [Order Service] as order
  component [Payment Service] as pay
  component [Inventory Service] as inv
  component [Notification Service] as notify
}

package "Data & Platform" {
  database "Orders DB" as db
  component [Event Bus] as bus
  component [Secrets Store] as secrets
}

interface "REST /orders" as iOrders
interface "REST /payments" as iPay
interface "gRPC Inventory" as iInv

web --> gw
mobile --> gw
gw --> bff : aggregate
bff --> order : REST
bff --> pay : REST
bff --> inv : gRPC

order -up- iOrders
iOrders -up- gw
pay -- iPay
inv -- iInv

order --> db : JDBC
order --> bus : publish OrderPaid
pay --> bus : publish PaymentSettled
notify --> bus : subscribe
order --> secrets : credentials

note bottom of bus
  asynchronous contract between services:
  schema in the registry, at-least-once delivery
end note
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `component [Name] as alias` | Component box (the classic UML component shape) |
| `interface "Name" as i` + `--` / `-up-` | Provided/required interface with a ball-and-socket edge |
| `package "Layer" { ... }` | Deployment-independent grouping (frontend / edge / services / platform) |
| `database "X"` | Storage is not a component — give it the database shape |
| Direction | `left to right direction` helps wide component diagrams; default TB works for layered ones |

## Data Shape

Components grouped by **responsibility layer**, connected either directly (call) or through an explicit interface.
Async channels (event bus) should be a component of their own, with publisher/subscriber edges.

## Pitfalls

- ❌ Every arrow pointing straight at a service, no interfaces → ✅ declare the interface when the contract matters
- ❌ Hiding the message broker → ✅ the bus is the contract between services; draw it and label publish/subscribe
- ❌ Mixing components with deployment nodes (`node`, `cloud`) → ✅ components are logical; use a deployment diagram for physical placement
- ❌ Layers with no meaning → ✅ name layers by responsibility, not by team org chart

## Alternatives

| Variant | Use instead |
|---|---|
| Physical deployment (nodes, regions, containers) | `runtime-deployment-topology.md` |
| Class-level detail of one service | `domain-class-model.md` |
| Message-level integration patterns | `eip-message-flow.md` |

<!-- source: draw-uml component parser (L1, 32 fixtures) -->
