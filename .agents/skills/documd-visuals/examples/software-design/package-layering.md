# Package Layering — Enforcing the Dependency Direction (PlantUML)

**Best for**: showing the intended layering of a codebase and which layers may depend on which
**Avoid when**: the reader needs the actual current dependencies (use `dependency-graph.md` on the real import graph)
**Answers**: what the layering is supposed to be, and where an illegal dependency would show up

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
skinparam packageStyle rectangle
skinparam arrowColor #334155

package "API layer" as api {
  [HTTP handlers]
  [DTO mapping]
}

package "Domain layer" as domain {
  [Entities]
  [Use cases]
  [Ports]
}

package "Infrastructure layer" as infra {
  [Repositories]
  [Queue adapters]
  [External clients]
}

api --> domain : calls
infra ..> domain : implements ports
api ..> infra : wiring only (composition root)
@enduml
```

## Data Shape

One `package` per layer, each holding its components as `[Name]`. Dependency arrows carry the rule being
asserted — this diagram is a *contract*, not a map of reality.

## Key Options

| Option | Effect |
|---|---|
| `skinparam packageStyle rectangle` | Turns folders into plain rectangles; easier to read as layers |
| Solid vs dashed arrows | Solid = compile-time call, dashed = implements / runtime wiring |
| Arrow labels | Name the relationship ("calls", "implements ports") — unlabelled arrows are guesses |
| `!pragma layout elk` | Keeps layers stacked when arrows cross |
| One package per layer | A package holding two layers destroys the reading |

## Pitfalls

- ❌ Drawing the current state and calling it the design → ✅ say whether this is the rule or the reality
- ❌ A "shared utilities" package everyone may depend on → ✅ name the allowed direction from it, or split it
- ❌ Layers implying a runtime call order → ✅ layering is a compile-time rule; runtime flow is a sequence diagram
- ❌ Ten components per package → ✅ the diagram argues about *layers*; keep the contents to what matters

## Alternatives

| Variant | Use instead |
|---|---|
| The real dependency graph with cycles | `dependency-graph.md` |
| Components and their interfaces | `component-decomposition.md` |
| Runtime deployment units | `runtime-deployment-topology.md` |

<!-- source: PlantUML package diagram reference + draw-uml fixture corpus (class-diagram packages, 82 cases) -->
