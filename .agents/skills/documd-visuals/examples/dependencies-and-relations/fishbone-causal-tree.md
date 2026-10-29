# Causal Tree / Cause Categories (PlantUML)

**Best for**: root-cause analysis where causes group into categories and converge on one observed effect
**Avoid when**: you need weighted or probabilistic analysis (use a table) or a solution tree rather than causes
**Answers**: which candidate causes exist for one effect, grouped by category

```plantuml
@startuml
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
skinparam DefaultFontColor #1f2937
skinparam ArrowColor #5b6b8c
skinparam ArrowFontColor #1f2937
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
left to right direction

' the effect is the sink: every category points at it
rectangle "Effect: late deliveries" as effect #dfe5fb;line:5b6b8c

rectangle "People" as people
rectangle "Process" as process
rectangle "Platform" as platform
rectangle "Partners" as partners

rectangle "on-call rotation gaps" as people1
rectangle "single owner for two services" as people2
rectangle "manual release approval" as process1
rectangle "no rollback rehearsal" as process2
rectangle "queue backlog at peak" as platform1
rectangle "cold-start latency" as platform2
rectangle "label printing lead time" as partners1
rectangle "carrier API outage" as partners2

people1 --> people
people2 --> people
process1 --> process
process2 --> process
platform1 --> platform
platform2 --> platform
partners1 --> partners
partners2 --> partners

people --> effect
process --> effect
platform --> effect
partners --> effect
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `rectangle "cause" as alias` | One box per cause; aliases keep the arrow lines short and readable |
| `left to right direction` | Causes read left→right into the effect; drop the line to read top→down |
| `#dfe5fb;line:5b6b8c` on the effect | Give the sink a second surface so it is not mistaken for another cause |
| Category nodes between causes and effect | Two levels only: cause → category → effect. Adding a third level turns the figure into a tree nobody reads |
| One arrow per cause | Direction is the message — resist drawing causes as a chain |

## Data Shape

One effect, 4–6 cause categories, 2–4 causes each. The diagram is for **hypothesis generation**: after the
discussion, highlight the shortlisted causes (colour) so the diagram becomes a record of the analysis.

## Pitfalls

- ❌ Expecting the classic Ishikawa spine → ✅ this is a *cause tree*; a horizontal spine needs rank control this engine does not expose. If the bone shape is the point, say so in the copy instead of forcing it
- ❌ More than six categories → ✅ six is the practical limit; merge or drop
- ❌ Causes stated as solutions ("add more servers") → ✅ keep causes descriptive; solutions belong in a separate list
- ❌ No prioritisation → ✅ highlight the agreed candidates, otherwise the exercise has no output

## Alternatives

| Variant | Use instead |
|---|---|
| Weighted/prioritised causes | A GFM table or a risk register card |
| Decision tree with outcomes | `module-import-arcs.md`, or a labelled-edge tree in the same rectangle syntax |
| Process flow with responsible roles | `approval-workflow-swimlane.md` |

<!-- source: draw-uml 1.5.2 — rectangle tree converging on one sink, per-node `#fill;line:border`; verified with documd -->
