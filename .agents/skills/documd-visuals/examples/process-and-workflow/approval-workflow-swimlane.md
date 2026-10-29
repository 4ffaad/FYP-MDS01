# Approval Workflow (Swimlane Activity)

**Best for**: cross-role business processes where you must see *who* does *what* and where hand-offs happen
**Avoid when**: the process is single-role (a plain activity diagram is simpler) or message-based (use EIP)
**Answers**: the steps, the responsible role for each, and the decision points that branch the flow

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
title Purchase Approval — Swimlane Activity

|#LightBlue|Requester|
start
:Raise purchase request;
:Attach quotes and budget code;

|#LightGreen|Manager|
:Review request;
if (Within budget?) then (yes)
  :Approve request;
else (no)
  :Request revision;
  |Requester|
  :Revise request;
  |Manager|
  :Review request;
endif

|#LightYellow|Finance|
:Validate cost centre;
if (Amount > 10k?) then (yes)
  :Escalate to CFO;
  |#LightPink|CFO|
  :Approve or reject;
  |Finance|
  :Record decision;
else (no)
  :Record decision;
endif

|#LightBlue|Requester|
:Receive outcome;
note right
  every decision is written to the
  audit trail with a timestamp
end note
stop
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `\|Role\|` | Start a lane; subsequent `:step;` statements belong to it |
| `\|#LightBlue\|Role\|` | Coloured lane header — colour the **role**, not the step |
| `start` / `stop` | Explicit begin and end markers |
| `if (cond?) then (yes)` / `else (no)` / `endif` | Decision with both branches labelled |
| `\|Role\|` in the middle of a branch | Hand-off — the reader literally sees the work change hands |
| `note right` … `end note` | **Activity diagrams attach notes to the previous step** — `note right of <name>` is rejected by PlantUML here; use `note right` or `floating note right: …` instead |

## Data Shape

Sequential steps partitioned by **actor**. Branches must return to a lane before handing off, otherwise the lane
structure becomes ambiguous in the rendered diagram.

## Pitfalls

- ❌ Lanes named after systems instead of roles → ✅ lanes are *responsibility*; systems belong in a component diagram
- ❌ Branching without returning to a lane → ✅ always re-enter a lane after `else` so the hand-off is explicit
- ❌ Encoding every rule in the diagram → ✅ keep policies in a note; diagrams show flow, not the rulebook
- ❌ Unlabelled decision outcomes → ✅ `then (yes)` / `else (no)` — never leave a branch anonymous
- ❌ `note right of <lane-or-step-name>` → ✅ not valid in activity/swimlane diagrams (PlantUML errors); use `note right` after the step, or `floating note right: …`

## Alternatives

| Variant | Use instead |
|---|---|
| Single-role procedure | Activity diagram without lanes |
| BPMN-compliant notation with events/gateways | `mxgraph.bpmn.*` icons + activity diagram |
| System-to-system orchestration | `eip-message-flow.md` or a sequence diagram |

<!-- source: draw-uml L1 `activity-diagram-lane` fixtures (13 cases) -->
