# C4 Container Diagram

**Best for**: communicating a system's shape to mixed audiences without teaching a notation first
**Avoid when**: you need deployment detail (use a deployment diagram) or class-level design
**Answers**: which containers exist, who uses them, and how they talk (with technology labels)

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
!include <c4/C4_Container>

title Checkout Platform — Container Diagram

Person(customer, "Customer", "Buys products online")
Person_Ext(ops, "Support Agent", "Handles refunds and escalations")

System_Boundary(platform, "Checkout Platform") {
  Container(spa, "Web App", "React, TypeScript", "Product browsing and checkout")
  Container(api, "Checkout API", "Node.js, Fastify", "Order orchestration, REST")
  Container(worker, "Async Worker", "Node.js", "Payments, fulfilment, notifications")
  ContainerDb(orders, "Orders DB", "PostgreSQL", "Orders, payments, audit trail")
  ContainerQueue(bus, "Event Bus", "Kafka", "Order lifecycle events")
}

System_Ext(payment, "Payment Provider", "Stripe API")
System_Ext(email, "Email Service", "SendGrid")

Rel(customer, spa, "Uses", "HTTPS")
Rel(ops, api, "Uses admin endpoints", "HTTPS")
Rel(spa, api, "Calls", "JSON/HTTPS")
Rel(api, orders, "Reads/Writes", "SQL")
Rel(api, bus, "Publishes OrderPlaced", "Kafka protocol")
Rel(bus, worker, "Delivers events", "Kafka protocol")
Rel(worker, payment, "Authorizes payments", "HTTPS")
Rel(worker, email, "Sends receipts", "HTTPS")
Rel(worker, orders, "Updates status", "SQL")
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `!include <c4/C4_Container>` | Loads the container-level macros (use `C4_Context` for the higher-level view) |
| `Person` / `Person_Ext` | Internal vs external actor — the suffix is the trust distinction |
| `System_Boundary(alias, "Name") { … }` | Draws the system boundary around your own containers |
| `Container` / `ContainerDb` / `ContainerQueue` | Container shapes by kind: service, datastore, message queue |
| `System_Ext(...)` | External system outside your boundary |
| `Rel(from, to, "description", "technology")` | The 4th argument (technology) is the reason to use C4 — always fill it |
| `title` | Diagram title in C4 style ("Container Diagram — …") |

## Data Shape

Actors outside, one `System_Boundary` around your containers, external systems at the edge, and `Rel()` edges
carrying both intent and technology. Reader question: "what are the moving parts and what are they built with".

## Pitfalls

- ❌ Skipping the technology argument → ✅ `Rel(..., "HTTPS")` / `"SQL"` is C4's main value; without it the diagram is a bubble chart
- ❌ Using components inside a container diagram → ✅ containers only; components belong to the next C4 level
- ❌ No boundary → ✅ external systems must sit outside `System_Boundary`, otherwise ownership is ambiguous
- ❌ Bypassing containers (person → database) → ✅ model the real path; shortcuts hide the missing component

## Alternatives

| Variant | Use instead |
|---|---|
| High-level view for non-technical stakeholders | The same file with `!include <c4/C4_Context>` and `System()` instead of `Container()` |
| Deployment/runtime placement | `runtime-deployment-topology.md` |
| Message-level detail | `api-interaction-sequence.md` or `eip-message-flow.md` |

<!-- source: draw-uml-dev fixtures/plantuml/stdlib/c4/001/002.puml (C4_Context / C4_Container macros) -->
