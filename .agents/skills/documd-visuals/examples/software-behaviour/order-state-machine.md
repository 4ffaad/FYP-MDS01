# Entity State Machine

**Best for**: the lifecycle of one entity — allowed states, allowed transitions, and who may trigger them
**Avoid when**: the reader needs the interaction between multiple actors (use a sequence diagram)
**Answers**: which states exist, how an entity moves between them, and which transitions are illegal

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
title Order Lifecycle — State Machine

[*] --> Draft : create()
Draft --> PendingPayment : submit()
Draft --> Cancelled : cancel()

PendingPayment --> Paid : paymentSettled()
PendingPayment --> PaymentFailed : paymentDeclined()
PendingPayment --> Cancelled : cancel() or expire(24h)

Paid --> Allocated : stockReserved()
Paid --> RefundPending : refundRequested()

Allocated --> Shipped : dispatch(trackingNo)
Allocated --> Paid : stockUnavailable() [partial]

Shipped --> Delivered : carrierConfirmed()
Shipped --> Lost : noScan(72h)

Delivered --> ReturnRequested : returnRequested()
Delivered --> Closed : afterReturnWindow(30d)

ReturnRequested --> RefundPending : returnAccepted()
ReturnRequested --> Delivered : returnRejected()

RefundPending --> Refunded : refundSettled()
PaymentFailed --> PendingPayment : retryPayment()
PaymentFailed --> Cancelled : giveUp()

Refunded --> [*]
Closed --> [*]
Cancelled --> [*]
Lost --> [*]

note right of Paid
  states with side effects on the
  event bus: Paid, Shipped, Refunded
end note
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `[*] --> First` / `Last --> [*]` | Initial and final states |
| `A --> B : trigger()` | Transition label = the event that causes it; use parentheses for calls |
| `[guard]` | Square-bracket guard conditions (`[partial]`, `[amount > 1000]`) |
| `state X { ... }` | Composite/nested state when a sub-lifecycle exists |
| `note right of X` | Cross-cutting remark (side effects, SLAs) |

## Data Shape

A directed graph of states with labelled transitions. The value is in the **negative space**: transitions that are
*not* drawn are the ones the domain forbids — mention that in the surrounding prose.

## Pitfalls

- ❌ Drawing every possible transition → ✅ model the allowed ones; forbidden transitions are the contract
- ❌ Using state names as transition labels → ✅ labels are **events** (`paymentDeclined()`), states are nouns
- ❌ No final states → ✅ every branch should terminate in `[*]` (or an explicit terminal state like `Lost`)
- ❌ Hiding timers → ✅ time-based transitions (`expire(24h)`, `noScan(72h)`) belong in the label

## Alternatives

| Variant | Use instead |
|---|---|
| Flow of work across roles (not one entity) | `approval-workflow-swimlane.md` |
| Data model of the entity | `domain-class-model.md` |
| Runtime message sequence | `api-interaction-sequence.md` |

<!-- source: draw-uml state parser (L1, 32 fixtures) -->
