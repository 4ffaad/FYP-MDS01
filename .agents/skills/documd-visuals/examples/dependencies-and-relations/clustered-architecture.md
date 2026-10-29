# Clustered Architecture with Cluster-to-Cluster Edges (PlantUML)

**Best for**: architecture overviews where edges should connect *groups* rather than individual boxes
**Avoid when**: the reader needs service icons (use a PlantUML cloud/network example)
**Answers**: how bounded contexts or planes relate, without drawing every internal edge

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

package "Edge plane" as edge #dfe5fb {
  rectangle "CDN" as cdn
  rectangle "WAF" as waf
  rectangle "API Gateway" as gw
}

package "Core services" as core {
  rectangle "Identity" as identity
  rectangle "Orders" as orders
  rectangle "Payments" as payments
  rectangle "Inventory" as inventory
}

package "Data plane" as data {
  rectangle "Orders DB" as ordersdb
  rectangle "Event Stream" as stream
  rectangle "Search Index" as search
}

package "Ops" as ops #f8fafc {
  rectangle "Metrics" as metrics
  rectangle "Logs" as logs
  rectangle "Secrets" as secrets
}

' internal edges (kept minimal on purpose)
cdn --> waf
waf --> gw
identity --> orders
orders --> payments
payments --> ordersdb
orders --> stream
inventory --> search

' plane-to-plane edges: the arrow is clipped to the package boundary
edge --> core : authenticated traffic
core --> data : domain events
core -[#6b7280,dashed]-> ops : telemetry
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `package "name" as alias { … }` | A plane. The alias is what a plane-to-plane edge references |
| `package "Ops" as ops #f8fafc { … }` | Per-plane fill, so the planes are told apart by surface as well as by title |
| `edge --> core : label` | **Plane-to-plane edge** — the arrow is clipped to the package boundary, so the edge speaks about the group, with no `compound=true` to remember |
| `-[#6b7280,dashed]->` | Dashed cross-plane edge in a second colour |
| `rectangle "label" as alias` | A node inside a plane; the alias keeps the internal edges short |
| `left to right direction` | Planes side by side; drop the line to stack them |

## Data Shape

Clusters = **planes or bounded contexts**; internal edges = the few relationships worth showing inside a plane;
plane-to-plane edges = the cross-plane contract. Reader question: "what are the planes and how do they talk".

## Pitfalls

- ❌ `compound=true` + `lhead` / `ltail` → ✅ there is nothing to enable: a PlantUML edge between two package aliases is clipped to the boundary on its own
- ❌ Drawing every internal call → ✅ show the 1–3 edges per plane that define the plane's role
- ❌ Cross-plane edges landed on a random node → ✅ draw the edge between the package aliases, not between members
- ❌ Different fill for every cluster with no meaning → ✅ three planes maximum in practice; the fill *is* the grouping

## Alternatives

| Variant | Use instead |
|---|---|
| Vendor icons for cloud services | `aws-serverless-architecture.md` (plantuml + awslib or mxgraph icons) |
| Deployment/zone topology | `runtime-deployment-topology.md` |
| Dependency direction analysis | `dependency-graph.md` |

<!-- source: draw-uml 1.5.2 — package-to-package edges (`package "x" as p { }` then `p --> q`), per-package fill, verified with documd -->
