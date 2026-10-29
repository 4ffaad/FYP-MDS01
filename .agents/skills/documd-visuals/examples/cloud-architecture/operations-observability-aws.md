# Operations and Observability (AWS, portable icons)

**Best for**: SRE/platform audiences — what is measured, what alerts, and how an incident is handled
**Avoid when**: the audience needs the application flow (use the serverless or deployment example)
**Answers**: which signals exist, what turns them into alerts, and who acts on them

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
!include <awslib/ManagementGovernance/all.puml>
!include <awslib/DeveloperTools/all.puml>
!include <awslib/ApplicationIntegration/all.puml>
!include <awslib/Containers/all.puml>
!include <awslib/Compute/all.puml>

hide stereotype
left to right direction
title Operations Stack — Signals, Alerts, Response

' ── Workloads (signal sources) ──
ElasticContainerService(app, "ECS service\n(app)", " ")
Lambda(workers, "Lambda\n(async workers)", " ")
AutoScaling(asg, "Auto Scaling\n(floor + ceiling)", " ")

' ── Signals ──
CloudWatch(metrics, "CloudWatch\nmetrics", " ")
CloudWatchLogs(logs, "CloudWatch\nLogs (structured)", " ")
CloudWatchAlarm(alarms, "CloudWatch\nAlarms (SLO burn)", " ")
CloudWatchSynthetics(synthetics, "Synthetics\n(canaries)", " ")
XRay(tracing, "X-Ray\ntraces", " ")

' ── Analysis / dashboards ──
ManagedGrafana(grafana, "Managed Grafana\n(service dashboards)", " ")
ManagedServiceforPrometheus(prometheus, "Managed Prometheus\n(high-cardinality)", " ")

' ── Response ──
SimpleNotificationService(pager, "SNS\n(pager topic)", " ")
SystemsManagerOpsCenter(opsCenter, "Systems Manager\nOpsCenter", " ")
SystemsManagerIncidentManager(incidents, "Incident Manager\n(on-call)", " ")

' ── Governance ──
TrustedAdvisor(advisor, "Trusted Advisor\n(checks)", " ")

' ── Flow ──
app --> metrics
app --> logs
app --> tracing
workers --> metrics
workers --> logs
asg --> metrics : scaling events
synthetics --> alarms : canary failures
metrics --> alarms : threshold / burn rate
logs --> alarms : metric filters
metrics --> grafana : query
prometheus --> grafana : query
tracing --> grafana : traces to exemplars
alarms --> pager : page (sev1/2)
alarms --> opsCenter : open ops item
pager --> incidents : engage on-call
incidents --> opsCenter : link runbook
advisor --> opsCenter : hygiene findings

note right of alarms
  alert on SLO burn rate, not on
  single-threshold spikes
end note
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `!include <awslib/ManagementGovernance/all.puml>` | `CloudWatch`, `CloudWatchLogs`, `CloudWatchAlarm`, `CloudWatchSynthetics`, `ManagedGrafana`, `ManagedServiceforPrometheus`, `SystemsManager*`, `TrustedAdvisor` |
| `!include <awslib/DeveloperTools/all.puml>` | `XRay`, `Code*` family — tracing belongs to this family in awslib |
| `!include <awslib/ApplicationIntegration/all.puml>` | `SimpleNotificationService` (paging topic) |
| `hide stereotype` | Keeps the picture clean when many families are mixed |
| Note placement | `note right of X` works in node-edge diagrams; in activity/swimlane diagrams use `note right` |

## Data Shape

Three bands: **workloads → signals → analysis**, with a response chain that turns alerts into owned incidents.
Every alerting edge should end at a human-facing object (page / ops item), otherwise the diagram has no owner.

## Pitfalls

- ❌ Paging on every threshold → ✅ alert on SLO burn rate; note it, because it is the design decision being reviewed
- ❌ Metrics without logs/traces → ✅ all three signals, because each answers a different failure question
- ❌ No runbook link → ✅ connect incidents to OpsCenter/runbooks; an alert without an action is noise
- ❌ Trusted Advisor as decoration → ✅ wire its findings into the ops queue, or leave it out

## Alternatives

| Variant | Use instead |
|---|---|
| Runtime topology (nodes, zones, replicas) | `runtime-deployment-topology.md` |
| Delivery pipeline signals | `cicd-pipeline.md` |
| SLO summary for stakeholders | An infocard metric card |

<!-- source: draw-uml-dev fixtures/plantuml/stdlib/aws/024/025/026 (ManagementGovernance) + 014 (DeveloperTools) + 010 (Containers) macro lists -->
