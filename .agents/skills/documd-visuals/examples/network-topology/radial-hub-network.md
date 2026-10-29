# Hub-and-Spoke Network (PlantUML)

**Best for**: one central node with layers of satellites — platform ecosystem, root-cause radius, network maps
**Avoid when**: there are several equally-important hubs (use `relationship-network-neato.md`) or strict hierarchy matters
**Answers**: what hangs off the centre, and how directly each thing relates to it

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

' the hub: one node, visually heavier than everything it serves
rectangle "platform" as platform #dfe5fb;line:334155

' ring 1: directly integrated capabilities
rectangle "auth" as auth
rectangle "billing" as billing
rectangle "catalog" as catalog
rectangle "notifications" as notifications
rectangle "search" as search

' ring 2: consumers of those capabilities
rectangle "mobile-app" as mobileapp
rectangle "partner-portal" as partnerportal
rectangle "finance-report" as financereport
rectangle "storefront" as storefront
rectangle "marketplace" as marketplace
rectangle "support-console" as supportconsole

' ring 3: downstream and supporting systems
rectangle "data-warehouse" as datawarehouse
rectangle "partner-onboarding" as partneronboarding
rectangle "kyc-service" as kycservice

platform --> auth
platform --> billing
platform --> catalog
platform --> notifications
platform --> search

auth --> mobileapp
auth --> partnerportal
billing --> financereport
catalog --> storefront
catalog --> marketplace
search --> storefront
notifications --> supportconsole

financereport --> datawarehouse
supportconsole --> datawarehouse
marketplace --> partneronboarding
partneronboarding --> kycservice
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| One hub, everything else pointing away | The reading is *distance from the centre*: rank 1 is the hub's own row, rank 2 the next, and so on |
| `rectangle "platform" as platform #dfe5fb;line:334155` | A second surface plus a stronger border makes the hub unmistakable at a glance |
| `platform --> auth` | Every spoke is one line; do not chain satellites together, or the ranks collapse |
| Declaration order | Declare the rings in order — the hub, then ring 1, then ring 2 — so the ranks follow the reading |
| `left to right direction` | Turns the rings into columns when the figure has to fit a page width |

## Data Shape

One hub, then layers of increasing distance: direct integrations at layer 1, consumers at layer 2, supporting
systems at layer 3. The reader question is "what is close to the platform and what is peripheral".

## Pitfalls

- ❌ Expecting concentric rings → ✅ this engine computes **ranks**, not radii; the reading is distance in *hops*, and the copy should say so. For a true ring, use `service-ownership-circle-graph.md`
- ❌ Several hubs in one figure → ✅ pick one root; a second centre flattens the whole graph into one rank
- ❌ Long chains hanging off the hub → ✅ a chain of five adds four ranks nobody asked about; hang consumers directly off their capability
- ❌ Satellite-to-satellite edges → ✅ they create short-circuits that break the layer reading

## Alternatives

| Variant | Use instead |
|---|---|
| Multiple hubs, no clear centre | `relationship-network-neato.md` |
| Strict hierarchy / org chart | The same rectangle tree with `top to bottom direction` |
| A true ring of equal nodes | `service-ownership-circle-graph.md` (echarts circular) |
| Ecosystem map with brand icons | plantuml cloud icon families (`mxgraph.aws4`, `awslib`) |

<!-- source: draw-uml 1.5.2 — one hub with layered spokes over `rectangle` nodes; per-node `#fill;line:border` on the hub; verified with documd -->
