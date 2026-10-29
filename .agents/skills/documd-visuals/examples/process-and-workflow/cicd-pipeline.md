# CI/CD Pipeline (AWS Developer Tools)

**Best for**: platform/DevOps audiences — how a commit becomes a running container in production
**Avoid when**: the process spans multiple vendors or includes manual approvals as the main topic (use a swimlane activity)
**Answers**: the stages a change passes through, what gates it, and where artifacts are stored

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
!include <awslib/DeveloperTools/all.puml>
!include <awslib/ApplicationIntegration/all.puml>
!include <awslib/Containers/all.puml>
!include <awslib/Storage/all.puml>
!include <awslib/Compute/all.puml>
!include <awslib/SecurityIdentityCompliance/all.puml>
!include <awslib/ManagementGovernance/all.puml>

hide stereotype
left to right direction
title Delivery Pipeline — Commit to Production

' ── Source ──
CodeCommit(repo, "CodeCommit\n(monorepo)", " ")

' ── Build ──
CodeBuild(unitBuild, "CodeBuild\nunit + lint", " ")
CodeArtifact(artifactRepo, "CodeArtifact\n(shared libs)", " ")
ElasticContainerRegistry(imageRepo, "ECR\n(image + scan)", " ")

' ── Security gates ──
Inspector(scan, "Inspector\n(image findings)", " ")
IdentityAccessManagementRole(deployRole, "IAM deploy role\n(OIDC, no keys)", " ")

' ── Deploy ──
CodeDeploy(deploy, "CodeDeploy\n(blue/green)", " ")
ElasticContainerService(ecsService, "ECS service\n(prod)", " ")
SimpleStorageServiceBucket(artifacts, "S3 artifacts\n+ reports", " ")

' ── Orchestration & observability ──
CodePipeline(pipeline, "CodePipeline", " ")
CloudWatch(alarms, "CloudWatch\nalarms", " ")
SimpleNotificationService(notify, "SNS\n(deploy notices)", " ")

' ── Flow ──
repo --> pipeline : webhook
pipeline --> unitBuild : stage 1
unitBuild --> artifacts : test reports
unitBuild --> artifactRepo : publish shared libs
pipeline --> imageRepo : stage 2
imageRepo --> scan : scan on push
scan --> pipeline : gate result
pipeline --> deploy : stage 3 (approval)
deployRole --> deploy : assume role
deploy --> ecsService : shift traffic
ecsService --> alarms : metrics
alarms --> notify : breach
deploy --> notify : result
artifacts --> pipeline : provenance

note right of deploy
  blue/green shift is reversible:
  rollback = shift traffic back,
  no rebuild
end note
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `!include <awslib/DeveloperTools/all.puml>` | `CodeCommit`, `CodeBuild`, `CodeDeploy`, `CodePipeline`, `CodeArtifact`, `CodeStar` |
| `!include <awslib/ApplicationIntegration/all.puml>` | Required for `SimpleNotificationService(...)` / `SimpleQueueService(...)` style messaging macros |
| `!include <awslib/SecurityIdentityCompliance/all.puml>` | `IdentityAccessManagementRole`, `Inspector`, `KeyManagementService`, `SecretsManager` |
| `!include <awslib/Compute/all.puml>` | `Lambda`, `EC2*`, `AutoScalingGroup`, `Batch` |
| Portable | awslib is official PlantUML stdlib — this diagram works outside Markdown Viewer too |
| `note right of X` outside activity diagrams | Valid here (node-edge diagram); inside activity/swimlane diagrams use `note right` instead |

## Data Shape

A left-to-right chain with **gates**: source → build → artifact store → image registry → security scan →
deploy → runtime, plus an observability branch. Gaps between stages are the approvals.

## Pitfalls

- ❌ Drawing only the happy path → ✅ a pipeline diagram without the security gate and rollback story is misleading
- ❌ Long-lived credentials → ✅ model the deploy role/identity as an explicit node; it explains the trust model
- ❌ One giant "build & deploy" box → ✅ separate build, scan and deploy so failures have a visible location
- ❌ Forgetting a category include → ✅ `SimpleNotificationService(...)` belongs to `ApplicationIntegration/all.puml`
- ❌ Forgetting artifact provenance → ✅ connect the artifact store to the pipeline; auditors ask for it

## Alternatives

| Variant | Use instead |
|---|---|
| Process view with approvers and hand-offs | `approval-workflow-swimlane.md` |
| Runtime topology after deploy | `runtime-deployment-topology.md` |
| Multi-environment promotion matrix | A GFM table or an infocard matrix card |

<!-- source: draw-uml-dev fixtures/plantuml/stdlib/aws/014 (DeveloperTools) + 010/032/035 macro lists (names verified verbatim) -->
