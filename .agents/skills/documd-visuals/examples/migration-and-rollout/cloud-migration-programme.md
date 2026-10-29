# Cloud Migration Programme (AWS, portable icons)

**Best for**: migration planning — what moves, in which wave, and with which tool
**Avoid when**: the reader needs the target architecture (use a cloud architecture example) or a dated schedule (use a Gantt)
**Answers**: which workloads migrate with which mechanism, and where the blockers are

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
!include <awslib/AWSCommon>
!include <awslib/MigrationTransfer/all.puml>
!include <awslib/Storage/all.puml>
!include <awslib/Database/all.puml>
!include <awslib/Compute/all.puml>
!include <awslib/ManagementGovernance/all.puml>

hide stereotype
left to right direction
title Migration Programme — Assessment, Moves, Cutover

' ── Assessment ──
rectangle "Assess" {
  ApplicationDiscoveryService(discovery, "Application\nDiscovery", " ")
  MigrationEvaluator(evaluator, "Migration\nEvaluator", " ")
  MigrationHub(hub, "Migration Hub\n(single pane)", " ")
}

' ── Move mechanisms ──
rectangle "Move (by workload type)" {
  ApplicationMigrationService(mgn, "Application Migration\n(rehost)", " ")
  ServerMigrationService(sms, "Server Migration\n(legacy VMs)", " ")
  DatabaseMigrationService(dms, "DMS\n(DB replication)", " ")
  DataSync(datasync, "DataSync\n(file/NFS)", " ")
  Snowball(snowball, "Snowball Edge\n(bulk data)", " ")
  TransferFamily(transfer, "Transfer Family\n(SFTP partners)", " ")
}

' ── Target platform ──
rectangle "Target (AWS)" {
  EC2(landingZone, "Landing zone\n(accounts, guardrails)", " ")
  Aurora(coreDb, "Aurora\n(core database)", " ")
  SimpleStorageServiceBucket(dataLake, "S3\n(data lake)", " ")
  CloudFormation(iac, "CloudFormation\n(landing zone as code)", " ")
}

' ── Flow ──
discovery --> hub : inventory
evaluator --> hub : business case
discovery --> evaluator : dependency map

hub --> mgn : wave 1 (rehost)
hub --> sms : wave 1 (legacy)
hub --> dms : wave 2 (databases)
hub --> datasync : wave 2 (file shares)
hub --> snowball : wave 2 (bulk archive)
hub --> transfer : wave 3 (partner interfaces)

mgn --> landingZone
sms --> landingZone
dms --> coreDb : continuous replication
datasync --> dataLake
snowball --> dataLake
transfer --> dataLake
iac --> landingZone : provision

note right of hub
  cutover order matters: databases replicate
  first, applications follow in short windows
end note
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `!include <awslib/MigrationTransfer/all.puml>` | `MigrationHub`, `MigrationHubRefactorSpaces*`, `ApplicationDiscoveryService`, `ApplicationMigrationService`, `ServerMigrationService`, `MigrationEvaluator`, `DataSync`, `TransferFamily*`, `MainframeModernization*` |
| `!include <awslib/Storage/all.puml>` | `Snowball`, `SnowballEdge`, `StorageGateway*`, S3 family |
| `!include <awslib/Database/all.puml>` | `DatabaseMigrationService`, `Aurora*`, `DynamoDB` |
| `rectangle "Assess" { … }` | Grouping by **phase** (assess / move / target) instead of by service family |
| Edge labels | Put the wave (`wave 1`) on the edge — that is the migration plan in one word |

## Data Shape

Three bands — **assess → move → target** — with the move band split by mechanism (rehost / database / data / partner
interface). Every mechanism edge should end at a concrete target resource, otherwise the plan has nowhere to land.

## Pitfalls

- ❌ Nothing about assessment → ✅ discovery + evaluator are what justify the move; start the diagram there
- ❌ A single "migrate" arrow → ✅ split by mechanism; each has different cutover behaviour and downtime
- ❌ Bulk data on the network path → ✅ use Snowball for large archives; showing it prevents an unrealistic estimate
- ❌ Ignoring partner interfaces → ✅ SFTP/AS2 partners need their own migration path (Transfer Family)

## Alternatives

| Variant | Use instead |
|---|---|
| Migration plan with dates and owners | `release-gantt-plan.md` or a programme WBS |
| Target-state architecture | Cloud architecture examples (`awslib` or `mxgraph.aws4`) |
| Application-level dependency analysis | A dependency graph (`dependencies-and-relations/dependency-graph.md`) |

<!-- source: draw-uml-dev fixtures/plantuml/stdlib/aws/028 (MigrationTransfer) + 034/035 (Storage) + 012 (Database) macro lists -->
