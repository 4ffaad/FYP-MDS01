# Serverless Event-Driven Platform (AWS, portable icons)

**Best for**: showing a modern serverless system end to end — synchronous API path plus asynchronous event fan-out
**Avoid when**: the runtime placement matters (use a deployment topology) or the message semantics dominate (use an EIP diagram)
**Answers**: how a request is served, what happens after the response returns, and where state lives

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
!include <awslib/ApplicationIntegration/all.puml>
!include <awslib/Compute/all.puml>
!include <awslib/Database/all.puml>
!include <awslib/Storage/all.puml>
!include <awslib/SecurityIdentityCompliance/all.puml>
!include <awslib/ManagementGovernance/all.puml>
!include <awslib/GroupIcons/all.puml>
!include <awslib/general/all.puml>

hide stereotype
left to right direction
title Serverless Order Platform — Sync Path and Event Fan-Out

' ── Identity & edge ──
Cognito(userPool, "Cognito\n(user pool)", " ")
APIGateway(api, "API Gateway\n(REST + auth)", " ")

' ── Synchronous compute ──
Lambda(orderFn, "Order function\n(idempotent writes)", " ")

' ── State ──
DynamoDB(ordersTable, "DynamoDB\n(orders, TTL)", " ")
SimpleStorageServiceBucket(receipts, "S3\n(receipts)", " ")

' ── Asynchronous backbone ──
EventBridge(bus, "EventBridge\n(domain events)", " ")
SimpleQueueService(fulfilQueue, "SQS\n(fulfilment)", " ")
SimpleNotificationService(topic, "SNS\n(notifications)", " ")
StepFunction(saga, "Step Functions\n(saga)", " ")

' ── Consumers ──
Lambda(fulfilFn, "Fulfilment\nfunction", " ")
Lambda(notifyFn, "Notification\nfunction", " ")

' ── Observability ──
CloudWatch(metrics, "CloudWatch\nmetrics", " ")
CloudWatchLogs(logs, "CloudWatch\nLogs", " ")

' ── Sync path ──
userPool --> api : JWT
api --> orderFn : POST /orders
orderFn --> ordersTable : conditional put
orderFn --> receipts : write receipt
orderFn --> bus : publish OrderPlaced
orderFn --> metrics : EMF metrics

' ── Async path ──
bus --> fulfilQueue : routing rule
bus --> saga : start saga
fulfilQueue --> fulfilFn : batch trigger
saga --> notifyFn : notify step
topic --> notifyFn : subscription
fulfilFn --> ordersTable : status update
notifyFn --> topic : fan-out
fulfilFn --> logs : structured logs

note right of saga
  compensation steps run only when
  fulfilment reports a failure
end note
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `!include <awslib/GroupIcons/all.puml>` | Group/edge icons **and** `StepFunction`, `VPCSubnet*`, `AutoScalingGroup`, `Cloud` |
| `!include <awslib/general/all.puml>` | Generic icons: `User(s)`, `Server(s)`, `Firewall`, `Internet`, `Gear`, `Document` … |
| `Semaphore(alias, "Label", " ")` | Third argument is the resource/secondary line — a single space keeps it empty |
| `hide stereotype` | Removes the `<<stereotype>>` labels the awslib macros attach |
| `left to right direction` | Request path reads left→right; async consumers sit below |
| Portability | awslib is official PlantUML stdlib — renders in any PlantUML tool |

## Data Shape

Two layers of flow: **synchronous** (identity → gateway → function → state) and **asynchronous**
(bus → queue/saga → consumers → state). State nodes appear once and are written by several functions —
that makes ownership of the data obvious.

## Pitfalls

- ❌ Fan-out drawn as a chain → ✅ a bus with several subscribers; otherwise the diagram implies ordering that does not exist
- ❌ Hiding idempotency → ✅ note or label it on the write edge; retries are guaranteed in this architecture
- ❌ No dead-letter path → ✅ at-least-once delivery needs a DLQ or an explicit drop policy
- ❌ Forgetting the auth hop → ✅ `Cognito → API Gateway` is the security boundary reviewers look for first

## Alternatives

| Variant | Use instead |
|---|---|
| Message semantics (routing, filtering, DLQ patterns) | `eip-message-flow.md` |
| Full AWS service map with vendor-style icons | `aws-serverless-architecture.md` (`mxgraph.aws4` extension) |
| Cost/scale analysis of the same design | An infocard metric grid or a table |

<!-- source: draw-uml-dev fixtures/plantuml/stdlib/aws/002 (ApplicationIntegration) + 006/007 (Compute) + 012 (Database) + 032 (Security) + 025 (ManagementGovernance) macro lists -->
