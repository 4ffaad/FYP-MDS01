# Entity Relationships (Information Engineering notation)

**Best for**: data models where cardinality is the message — one-to-many, optional, mandatory
**Avoid when**: you need entity attributes in the same diagram (use a class diagram for attributes, or a separate data dictionary)
**Answers**: which entities exist and how many of each relate to each other

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
title Order Data Model — IE (crow's foot) Notation

Customer }|..o{ Order
Order ||--|{ OrderLine
Order ||--o| Invoice
OrderLine }o--|| Product

Product }o--|| Category
Product ||--o{ StockLevel
Invoice ||--|{ PaymentAllocation
Supplier ||--o{ Product

note right of Order
  |  = exactly one
  o  = zero or one
  {  = many (crow's foot)
  .. = optional relationship
  -- = mandatory relationship
end note
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `A }|..|| B` | Crow's-foot on A's side, single bar on B's side (many-to-one), optional (`..`) vs mandatory (`--`) |
| `\|` / `o` / `{` / `}` | Cardinality markers: bar = one, circle = zero (optional), crow's foot = many |
| `--` vs `..` | Mandatory vs optional relationship |
| `note right of X` | Put the notation legend here — readers of data diagrams ask about it every time |
| Entity naming | Singular nouns, no verbs (`Order`, not `Orders`) |

## Data Shape

A relationship graph of entities. Attributes are deliberately absent: in IE notation the value is the cardinality
contract, and mixing attributes in makes the diagram unreadable at more than ~8 entities.

## Pitfalls

- ❌ Using `erDiagram`-style syntax from other tools → ✅ this engine supports the PlantUML IE/crow's-foot relation syntax only
- ❌ Assuming attributes can be attached to entities → ✅ verify first; in this engine the IE fixtures are relationship-only
- ❌ Mixing IE and class diagrams in one figure → ✅ pick one notation per diagram
- ❌ Cardinality direction mistakes → ✅ read `A }|..|| B` as "many A relate to exactly one B"

## Alternatives

| Variant | Use instead |
|---|---|
| Entities with attributes and methods | `domain-class-model.md` (class diagram) |
| Data flow rather than data model | `data-platform` pipeline diagrams (plantuml + AWS analytics stencils) |
| Schema documentation for readers | A GFM table or an infocard `matrix-table` |

<!-- source: draw-uml IE fixtures (ie-diagram/ 6 cases, verified against official PlantUML baselines) -->
