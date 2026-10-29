# Domain Class Model

**Best for**: describing entities, their attributes/operations and the relationships between them
**Avoid when**: the reader needs runtime behaviour (use a sequence diagram) or deployment layout
**Answers**: what the domain concepts are and how they relate (inheritance, composition, association)

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
title Order Domain — Class Model

package "ordering" {
  class Customer {
    +customerId: UUID
    +email: string
    +tier: Tier
    +placeOrder(): Order
  }

  class Order {
    +orderId: UUID
    +status: OrderStatus
    +total(): Money
    +cancel(reason: string): void
  }

  class OrderLine {
    +sku: string
    +quantity: int
    +amount(): Money
  }

  enum OrderStatus {
    PENDING
    PAID
    SHIPPED
    CANCELLED
  }
}

package "payment" {
  class Payment {
    +paymentId: UUID
    +provider: string
    +authorize(): Approval
  }

  interface PaymentGateway {
    +authorize(order: Order): Approval
    +refund(paymentId: UUID): void
  }

  class StripeGateway {
    +authorize(order: Order): Approval
  }
}

Customer "1" --> "0..*" Order : places >
Order "1" *-- "1..*" OrderLine : contains >
Order --> OrderStatus : has
Order "1" -- "0..1" Payment : paid by >
PaymentGateway <|.. StripeGateway
Payment ..> PaymentGateway : uses

note right of Order
  status transitions are enforced
  in the domain layer, not in SQL
end note
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `class X { +field: type  +method(): type }` | Visibility prefixes: `+` public, `-` private, `#` protected |
| `interface` / `enum` / `abstract class` | Declares the kind of type — the icon differs, which carries meaning |
| `<|--` / `<|..` | Inheritance / interface realisation |
| `*--` / `o--` | Composition / aggregation (filled vs hollow diamond) |
| `-->` / `..>` | Association / dependency |
| `"1" --> "0..*"` | Multiplicities on both ends — always add them; unlabelled arrows hide the cardinality decision |
| `package "x" { ... }` | Module boundary |

## Data Shape

Types + relationships. Keep attributes to the ones that carry domain meaning; a class model is not a schema dump.

## Pitfalls

- ❌ Listing every column of every table → ✅ model behaviour (operations) and the invariants that matter
- ❌ Omitting multiplicities → ✅ `"1" --> "0..*"` prevents a dozen follow-up questions
- ❌ Using composition (`*--`) for weak references → ✅ composition means "dies with the owner"
- ❌ Mixing package structure with runtime layering → ✅ packages are modules; deployment is a different diagram

## Alternatives

| Variant | Use instead |
|---|---|
| Runtime object snapshot | An object diagram (`object "x" as id` syntax) |
| Module dependency direction only | `dependencies-and-relations/dependency-graph.md` |
| Data model for a database | Entity boxes + crow's foot via the IE syntax (`Entity01 }|..|| Entity02`) |

<!-- source: draw-uml class parser (L1, 82 fixtures); syntax subset per draw-uml README -->
