# Activity Flow — A Process With Decisions (PlantUML)

**Best for**: the plainest process diagram: ordered steps, one or two decisions, and the paths they create
**Avoid when**: the process has roles to separate (use the swimlane variant) or it is a message exchange (sequence)
**Answers**: what happens next, and what happens when a check fails

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
start
:Receive request;
:Validate payload;
if (Valid?) then (yes)
  :Reserve inventory;
  if (In stock?) then (yes)
    :Create order;
    :Charge payment;
    if (Payment authorised?) then (yes)
      :Confirm order;
    else (no)
      :Release stock;
      :Notify customer;
    endif
  else (no)
    :Offer backorder;
  endif
else (no)
  :Return validation errors;
endif
stop
@enduml
```

## Data Shape

Linear statements with `:` … `;` are actions; `if (…) then (…) / else (…) / endif` is a decision. `start` and
`stop` are explicit — an activity diagram with no end state invites "and then what?".

## Key Options

| Option | Effect |
|---|---|
| `if/else/endif` | The only decision construct; nest them to express a real branch tree |
| `repeat` / `while` | Loops, with `repeat while (…) is (yes)` for the exit condition |
| `fork` / `fork again` / `end fork` | Parallel work, joined before continuing |
| `swimlane` per role | Move to the lane variant when *who does it* matters |
| `:action;` with `<<stereotype>>` | Marks automated vs manual steps |

## Pitfalls

- ❌ A diagram with twenty actions → ✅ split at the first major decision; readers lose the thread after ~12 nodes
- ❌ Decisions whose else branch is "end" → ✅ name the failure path, it is usually the interesting one
- ❌ Drawing responsibilities without lanes → ✅ if the reader will ask "who does this?", switch to the swimlane variant
- ❌ No start or stop → ✅ every activity diagram needs both, or it reads as a fragment

## Alternatives

| Variant | Use instead |
|---|---|
| Roles in columns | `approval-workflow-swimlane.md` |
| Message exchange over time | `api-interaction-sequence.md` (software-design) |
| A straight path with owners and no branches | `procurement-approval-path.md` (infographic) |

<!-- source: PlantUML activity diagram (beta) reference + draw-uml fixture corpus (activity-diagram, 56 cases) -->
