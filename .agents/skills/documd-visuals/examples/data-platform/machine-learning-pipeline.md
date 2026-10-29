# Machine Learning Pipeline (AWS)

**Best for**: ML platform audiences — data preparation, training, model registry and inference in one view
**Avoid when**: the reader is a business stakeholder (show a KPI card instead) or the model itself is the topic
**Answers**: how data becomes a trained model, where artifacts live, and how the model reaches production

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
!include <awslib/MachineLearning/all.puml>
!include <awslib/Compute/all.puml>
!include <awslib/Storage/all.puml>
!include <awslib/Analytics/all.puml>
!include <awslib/ApplicationIntegration/all.puml>
!include <awslib/Containers/all.puml>
!include <awslib/ManagementGovernance/all.puml>

hide stereotype
left to right direction
title ML Platform — From Raw Data to Online Inference

' ── Data ──
SimpleStorageServiceBucket(rawZone, "S3 raw zone", " ")
SimpleStorageServiceBucket(featureZone, "S3 feature zone", " ")
GlueDataCatalog(catalog, "Glue Data Catalog", " ")
Glue(glueJobs, "Glue ETL jobs", " ")

' ── Experimentation ──
SageMakerNotebook(notebook, "SageMaker\nNotebook", " ")
SageMakerTrain(training, "SageMaker\nTraining jobs", " ")
SageMakerModel(modelRegistry, "SageMaker\nModel Registry", " ")
ElasticContainerRegistry(ecr, "ECR\n(custom image)", " ")

' ── Serving ──
SageMaker(endpoint, "SageMaker\nEndpoint", " ")
SimpleStorageServiceBucket(batchOut, "S3 batch\npredictions", " ")
Lambda(inferenceFn, "Lambda\nlight inference", " ")

' ── Operations ──
CloudWatch(metrics, "CloudWatch\nmetrics", " ")
CloudWatchLogs(logs, "CloudWatch\nLogs", " ")
SystemsManagerParameterStore(params, "Parameter Store\n(thresholds)", " ")
EventBridge(retrainTrigger, "EventBridge\nretraining rule", " ")

' ── Flow: data ──
rawZone --> glueJobs : read
catalog --> glueJobs : schema
glueJobs --> featureZone : write features
featureZone --> notebook : explore
featureZone --> training : train/validation split
ecr --> training : runtime image

' ── Flow: model ──
training --> modelRegistry : register artifact
modelRegistry --> endpoint : deploy approved version
modelRegistry --> batchOut : batch transform
modelRegistry --> inferenceFn : package small model

' ── Flow: operations ──
endpoint --> metrics : latency / invocations
endpoint --> logs : request logs
metrics --> retrainTrigger : drift or decay signal
retrainTrigger --> training : trigger retraining
params --> inferenceFn : cutoff thresholds

note right of modelRegistry
  promotion gate: a model reaches
  production only through the registry
end note
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `!include <awslib/MachineLearning/all.puml>` | SageMaker family macros (`SageMaker`, `SageMakerTrain`, `SageMakerModel`, `SageMakerNotebook`, `SageMakerCanvas`) |
| `!include <awslib/Compute/all.puml>` | Required for `Lambda(...)` in the serving band |
| `!include <awslib/ApplicationIntegration/all.puml>` | Required for `EventBridge(...)` and other integration/messaging macros |
| `!include <awslib/Containers/all.puml>` | `ElasticContainerRegistry`, `ElasticContainerService*` |
| `!include <awslib/ManagementGovernance/all.puml>` | `CloudWatch`, `CloudWatchLogs`, `SystemsManagerParameterStore`, `TrustedAdvisor*` |
| Portable | awslib is part of the **official PlantUML stdlib** — this diagram renders in any PlantUML tool, not only in Markdown Viewer |
| `left to right direction` | Keeps the data → model → serving progression readable |

## Data Shape

Three bands: **data** (lake + catalog + ETL) → **experimentation** (notebook → training → registry) →
**serving** (endpoint / batch / function). Operations sits below with a feedback edge back into training.

## Pitfalls

- ❌ Deploying straight from a training job → ✅ route through a model registry; it is the promotion gate
- ❌ No feedback loop → ✅ add the drift/metric edge back into training, otherwise the diagram implies a frozen model
- ❌ Mixing training and serving infrastructure → ✅ separate bands make cost and scaling decisions visible
- ❌ Forgetting a category include → ✅ every awslib macro must come from a loaded family; `Lambda(...)` needs `Compute/all.puml`
- ❌ Guessing the family for orchestration/events → ✅ `EventBridge(...)` belongs to `ApplicationIntegration/all.puml`
- ❌ Omitting the runtime image → ✅ custom training/serving images come from a registry (`ElasticContainerRegistry`)

## Alternatives

| Variant | Use instead |
|---|---|
| Data pipeline without ML | `data-platform-lakehouse.md` |
| Serving architecture only | Cloud architecture examples with `mxgraph.aws4` icons |
| Model card / metrics summary | An infocard `metric-board` style card |

<!-- source: draw-uml-dev fixtures/plantuml/stdlib/aws/023 (MachineLearning) + 010/014/025 macro lists (names verified verbatim) -->
