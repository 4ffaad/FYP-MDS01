# Work Breakdown Structure (engine gap — use the alternatives below)

**Best for**: deliverables and ownership in a strict hierarchy — **but not with `@startwbs` in this engine**
**Avoid when**: you need free-form idea exploration (use `topic-mindmap.md`)
**Answers**: what the work is made of and who owns each part

> ⚠️ **Engine limitation (verified 2026-09-21)**: `@startwbs … @endwbs` **parses without error but renders an empty
> diagram**. Use one of the two supported forms below instead.

## Option A — hierarchy as a mind map (recommended)

```plantuml
@startmindmap
title Platform Programme — Work Breakdown

* Platform Programme
** 1. Discovery
*** 1.1 Current-state assessment
*** 1.2 Stakeholder interviews
*** 1.3 Target architecture draft
** 2. Core Platform
*** 2.1 Identity and access
**** 2.1.1 SSO integration
**** 2.1.2 Role model
*** 2.2 Service runtime
**** 2.2.1 Container platform
**** 2.2.2 CI/CD pipelines
*** 2.3 Data layer
**** 2.3.1 Schema migration
**** 2.3.2 Reconciliation tooling
** 3. Adoption
*** 3.1 Migration playbook
*** 3.2 Team enablement
*** 3.3 Support model
** 4. Governance
*** 4.1 Architecture review board
*** 4.2 Security and compliance sign-off
*** 4.3 Cost reporting
@endmindmap
```

## Option B — hierarchy as a boxed top-down tree

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
top to bottom direction

rectangle "Platform Programme" as programme #dfe5fb;line:334155

rectangle "1. Discovery" as d1
rectangle "2. Core Platform" as c1
rectangle "3. Adoption" as a1
rectangle "4. Governance" as g1

rectangle "1.1 Assessment" as d11
rectangle "1.2 Interviews" as d12
rectangle "1.3 Target architecture" as d13
rectangle "2.1 Identity" as c11
rectangle "2.2 Runtime" as c12
rectangle "2.3 Data" as c13
rectangle "2.1.1 SSO" as c111
rectangle "2.1.2 Roles" as c112
rectangle "3.1 Playbook" as a11
rectangle "3.2 Enablement" as a12
rectangle "3.3 Support" as a13
rectangle "4.1 Review board" as g11
rectangle "4.2 Sign-off" as g12
rectangle "4.3 Cost" as g13

programme --> d1
programme --> c1
programme --> a1
programme --> g1

d1 --> d11
d1 --> d12
d1 --> d13
c1 --> c11
c1 --> c12
c1 --> c13
c11 --> c111
c11 --> c112
a1 --> a11
a1 --> a12
a1 --> a13
g1 --> g11
g1 --> g12
g1 --> g13
@enduml
```

## Key Options

| Syntax | Where it applies | Effect |
|---|---|---|
| `*` / `**` / `***` / `****` | mind map | Depth levels — indentation is expressed by asterisk count, not spaces |
| `left side` | mind map | Move the following branches to the left half |
| `top to bottom direction` | tree | Top-down tree; drop the line (or use `left to right direction`) for a wide one |
| `rectangle "2.1 Identity" as c11` | tree | Boxed nodes read as deliverables rather than concepts; the alias keeps the edge lines short |
| WBS numbering in the text | both | Number the nodes (`2.1.1`) so reviews can cite them |

## Data Shape

A pure tree, 3–4 levels deep. Each leaf should be a deliverable someone can own; if a leaf is an activity, the
structure has drifted from WBS into a project plan.

## Pitfalls

- ❌ Writing `@startwbs` → ✅ it renders empty in this engine; use Option A or B above
- ❌ Leaves that are activities ("run tests") → ✅ leaves are deliverables/artefacts
- ❌ Unnumbered nodes → ✅ WBS numbering is what makes the structure citable in plans and reviews
- ❌ More than four levels → ✅ deeper than four means it belongs in a separate sub-structure
- ❌ Option B for a 40-leaf programme → ✅ a boxed tree costs a box per leaf; the mind map in Option A carries the same structure in a quarter of the height

## Alternatives

| Variant | Use instead |
|---|---|
| Org chart with team names | Option B, or a mind map using `left side` |
| Free-form topic decomposition | `topic-mindmap.md` |
| Dated plan | `release-gantt-plan.md` |

<!-- source: gap verified via documd (342 B blank SVG), confirmed by draw-uml-dev fixtures/svg-generated/creole/036.svg (342 B) vs official baseline (4535 B); Option B verified with documd -->

