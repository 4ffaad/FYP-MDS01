# API Interaction Sequence

**Best for**: showing the exact order of calls between components, including retries and failure branches
**Avoid when**: the reader only needs the static structure (use a class or component diagram)
**Answers**: who calls whom, in what order, and what happens when a step fails

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
autonumber
title Checkout API — Request Sequence

actor "Customer" as user
participant "Web App" as web
participant "API Gateway" as gw
participant "Order Service" as order
participant "Payment Service" as pay
database "Orders DB" as db
queue "Event Bus" as bus

user -> web : Click "Place order"
web -> gw : POST /orders
activate gw
gw -> order : createOrder(items)
activate order

order -> db : insert order(status=pending)
db --> order : orderId

order -> pay : authorize(orderId, amount)
activate pay

alt payment authorized
  pay --> order : approvalCode
  order -> db : update status=paid
  order -> bus : publish OrderPaid
  order --> gw : 201 Created
else payment declined
  pay --> order : declineReason
  order -> db : update status=failed
  order --> gw : 402 Payment Required
else gateway timeout
  pay --> order : timeout
  order -> order : retry (max 2, backoff)
  order --> gw : 504 Gateway Timeout
end

deactivate pay
deactivate order

gw --> web : response
deactivate gw
web --> user : Confirmation screen
note over order, db : Idempotency key prevents\nduplicate orders on retry
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `actor` / `participant` / `database` / `queue` | Lifeline kinds — the icon tells the reader what the box is |
| `autonumber` | Numbers every message; essential once a diagram passes ~8 arrows |
| `->` vs `-->` | Call vs return — keep the convention consistent across the diagram |
| `activate` / `deactivate` | Shows the span during which a component is busy |
| `alt` / `else` / `end` | Failure and branching paths (this is where sequence diagrams earn their keep) |
| `note over A, B` | Cross-cutting remark (idempotency, retries, timeouts) |

## Data Shape

Ordered messages between named lifelines, one path per outcome. Group by **success / business failure /
infrastructure failure** — readers scan for the branch they care about.

## Pitfalls

- ❌ Only drawing the success path → ✅ at least one failure branch; retries and timeouts are the interesting part
- ❌ Using `participant` for everything → ✅ `actor` for humans, `database` for storage, `queue` for async hops
- ❌ Unbounded `alt` nesting → ✅ more than two levels means the flow should be split into two diagrams
- ❌ Forgetting activation bars → ✅ they make concurrency and blocking visible at a glance

## Alternatives

| Variant | Use instead |
|---|---|
| Async, no reply expected | Arrow `->>` and no return edge |
| Multiple participants in parallel | `par` fragments |
| State of one entity over time | A state machine diagram (`order-state-machine.md`) |

<!-- source: PlantUML sequence syntax (draw-uml L1); legacy skills/uml/examples/sequence-diagram.md renders 15/15 -->
