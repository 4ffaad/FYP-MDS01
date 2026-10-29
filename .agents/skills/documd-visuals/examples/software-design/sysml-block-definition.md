# SysML Block Definition — System Elements and Their Properties (PlantUML)

**Best for**: systems engineering vocabulary — blocks, their value properties and the relationships between them
**Avoid when**: the audience expects UML classes, or the system is pure software (use a class diagram)
**Answers**: what the system is made of, and which quantities each block owns

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
skinparam stereotypeCBackgroundColor #d9e3f4

class "Vehicle" <<block>> as veh {
  + mass : kg
  + maxPayload : kg
}

class "Powertrain" <<block>> as pt {
  + peakPower : kW
  + efficiency : %
}

class "Battery Pack" <<block>> as batt {
  + capacity : kWh
  + stateOfHealth : %
}

class "Chassis" <<block>> as chassis {
  + wheelbase : mm
}

veh *-- pt
veh *-- chassis : 1
pt *-- "1..8" batt
veh --> batt : requires
@enduml
```

## Data Shape

Blocks are `class` elements stereotyped `<<block>>`; value properties are attributes with a unit. Composition
(`*--`) is used for structural decomposition, association (`-->`) for weaker dependencies, and multiplicities
sit on the part end of the line.

## Key Options

| Option | Effect |
|---|---|
| `<<block>>` stereotype | Marks the SysML reading; the SysML stencil family adds real block notation when icons are wanted |
| Units in the attribute type | `mass : kg` — a property without a unit is not a property in systems engineering
| Multiplicity on the part end | `"1..8"` states how many parts a whole can own |
| `skinparam stereotypeCBackgroundColor` | One colour for all blocks keeps the stereotype readable at a glance |

## Pitfalls

- ❌ Mixing software classes and SysML blocks in one diagram → ✅ pick the vocabulary the audience owns
- ❌ Value properties without units → ✅ every quantity carries its unit; that is the point of the notation
- ❌ Modelling behaviour as blocks → ✅ blocks are structure; behaviour needs an activity or sequence diagram
- ❌ Drawing the full Modelica-grade model → ✅ show the two or three interfaces under discussion

## Alternatives

| Variant | Use instead |
|---|---|
| Software domain model | `domain-class-model.md` |
| Physical placement on hardware | `runtime-deployment-topology.md` |
| Interfaces with icons per subsystem | `component-decomposition.md` |

<!-- source: SysML block-definition usage with the PlantUML SysML stencil family (draw-uml stencil index, 60 families) -->
