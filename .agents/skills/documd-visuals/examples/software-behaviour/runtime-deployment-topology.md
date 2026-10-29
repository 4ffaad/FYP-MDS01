# Runtime Deployment Topology

**Best for**: where the software actually runs — nodes, regions/zones, containers and execution environments
**Avoid when**: the reader needs the logical component structure (use a component diagram)
**Answers**: which artifacts run on which node, and how the nodes relate (region, zone, network)

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
title Production Deployment — Runtime Topology

node "Region: eu-central-1" {
  node "Availability Zone A" {
    node "Public Subnet" {
      artifact "ALB" as albA
    }
    node "Private Subnet" {
      artifact "app-server-1\n(JVM 21, 4 vCPU)" as app1
      database "primary DB\n(PostgreSQL 16)" as dbPrimary
    }
  }

  node "Availability Zone B" {
    node "Public Subnet" {
      artifact "ALB (standby)" as albB
    }
    node "Private Subnet" {
      artifact "app-server-2\n(JVM 21, 4 vCPU)" as app2
      database "read replica" as dbReplica
    }
  }

  node "Managed Services" {
    artifact "object storage" as s3
    artifact "secrets store" as secrets
    artifact "metrics + logs" as obs
  }
}

node "Region: us-east-1 (DR)" {
  node "Warm Standby" {
    artifact "app-server-dr\n(scaled to 10%)" as appDr
    database "replicated DB" as dbDr
  }
}

artifact "CDN edge cache" as cdn

cdn --> albA : HTTPS
cdn --> albB : HTTPS
albA --> app1
albB --> app2
app1 --> dbPrimary : JDBC
app2 --> dbPrimary : JDBC
app2 --> dbReplica : read-only
app1 --> s3 : objects
app1 --> secrets : credentials
app1 --> obs : telemetry
dbPrimary ..> dbDr : streaming replication
app1 ..> appDr : failover target

note bottom of dbDr
  RPO 5 min / RTO 15 min
end note
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `node "X" { ... }` | Execution environment; nesting expresses region → zone → subnet |
| `artifact "X"` | Deployable unit (the thing you ship) |
| `database "X"` | Managed storage (do not draw databases as artifacts) |
| `A ..> B` | Replication / failover relationships (logical, not request-path) |
| Nesting depth | Three levels is usually the useful maximum; deeper nesting hides the story |

## Data Shape

A **containment tree** (region → zone → subnet → artifact) plus cross-node edges for the request path and replication.
Reader question: "what runs where, and what happens if a node dies".

## Pitfalls

- ❌ Drawing every environment (dev/stage/prod) in one diagram → ✅ one environment per diagram; environments differ
- ❌ Missing the failure story → ✅ include replicas/standby and label RPO/RTO in a note
- ❌ Using components where nodes belong → ✅ components are logical units; nodes are places that fail
- ❌ Sizing details in every box → ✅ put CPU/memory only where capacity is the question being discussed

## Alternatives

| Variant | Use instead |
|---|---|
| Logical structure and interfaces | `component-decomposition.md` |
| Cloud-provider architecture with service icons | `aws-serverless-architecture.md` |
| Network device/zone topology | `network-topology-enterprise.md` |

<!-- source: draw-uml deployment parser (L1, 59 fixtures) -->
