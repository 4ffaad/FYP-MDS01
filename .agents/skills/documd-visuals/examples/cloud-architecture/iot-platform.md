# IoT Platform (AWS, portable icons)

**Best for**: showing the device → edge → cloud path with fleet management and analytics in one view
**Avoid when**: the reader needs firmware internals or a pure network topology
**Answers**: how devices connect, where data is processed, and how the fleet is managed and updated

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
!include <awslib/InternetOfThings/all.puml>
!include <awslib/Analytics/all.puml>
!include <awslib/Storage/all.puml>
!include <awslib/MachineLearning/all.puml>
!include <awslib/ManagementGovernance/all.puml>

hide stereotype
left to right direction
title IoT Platform — Fleet, Edge, Ingestion, Analytics

' ── Devices ──
FreeRTOS(sensorFleet, "Sensor fleet\n(FreeRTOS)", " ")
IoTDeviceGateway(deviceGateway, "Device Gateway\n(MQTT / TLS)", " ")

' ── Edge ──
IoTGreengrass(edgeRuntime, "Greengrass\n(edge runtime)", " ")
IoTGreengrassComponent(edgeComponents, "Edge components\n(local ML, filtering)", " ")

' ── Cloud ingestion ──
IoTCore(iotCore, "IoT Core\n(rules engine)", " ")
IoTEvents(iotEvents, "IoT Events\n(alarm detectors)", " ")
IoTDeviceManagement(deviceMgmt, "Device Management\n(jobs, fleets)", " ")
IoTDeviceDefender(defender, "Device Defender\n(anomaly audit)", " ")

' ── Storage & analytics ──
SimpleStorageServiceBucket(telemetry, "S3 telemetry\n(partitioned)", " ")
GlueCrawler(crawler, "Glue Crawler", " ")
GlueDataCatalog(catalog, "Glue Data Catalog", " ")
Athena(athena, "Athena\n(fleet queries)", " ")
SageMakerTrain(model, "SageMaker\n(predictive maintenance)", " ")

' ── Ops ──
CloudWatch(metrics, "CloudWatch\nmetrics", " ")
CloudTrail(audit, "CloudTrail\n(API audit)", " ")

' ── Flow ──
sensorFleet --> deviceGateway : MQTT publish
deviceGateway --> iotCore : telemetry
iotCore --> edgeRuntime : commands (downlink)
edgeRuntime --> edgeComponents
edgeComponents --> iotCore : filtered telemetry
iotCore --> telemetry : rules action
iotCore --> iotEvents : state input
iotEvents --> metrics : alarm
telemetry --> crawler
crawler --> catalog : schemas
catalog --> athena : query tables
telemetry --> model : training data
model --> iotCore : inference endpoint
deviceMgmt --> sensorFleet : OTA jobs
defender --> metrics : security findings
iotCore --> audit : control-plane API calls

note right of edgeRuntime
  edge keeps working through connectivity loss:
  buffer locally, forward on reconnect
end note
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `!include <awslib/InternetOfThings/all.puml>` | `IoTCore`, `IoTEvents`, `IoTDeviceManagement`, `IoTDeviceDefender`, `IoTGreengrass*`, `FreeRTOS`, `IoTButton`, `IoTAnalytics*` |
| `!include <awslib/Analytics/all.puml>` | `Glue*`, `Athena`, `Kinesis*`, `Redshift`, `QuickSight` |
| `!include <awslib/MachineLearning/all.puml>` | `SageMaker*` — the ML step of a predictive-maintenance pipeline |
| `left to right direction` | Device → edge → cloud → analytics reads naturally |
| Two-way edges | Uplink telemetry and downlink commands are separate labelled edges — do not merge them |

## Data Shape

Five stages: **devices → edge → cloud ingestion → storage/analytics → operations**. Management is a cross-cutting
band (fleet jobs, security audit) that touches devices and ingestion without being on the data path.

## Pitfalls

- ❌ One-way telemetry only → ✅ show the downlink (commands, OTA jobs); IoT without control is telemetry, not IoT
- ❌ Skipping the edge runtime → ✅ edge processing answers the latency/connectivity story — it is the interesting part
- ❌ Raw telemetry queried directly → ✅ land in S3 then catalog it; that is why Athena appears downstream of Glue
- ❌ No device identity/certificates → ✅ mention certificates (edge/device) in a note; reviewers ask for the trust model

## Alternatives

| Variant | Use instead |
|---|---|
| Fleet analytics only | `data-platform-lakehouse.md` |
| Edge site network layout | `network-topology-enterprise.md` |
| Device lifecycle states | A state machine diagram |

<!-- source: draw-uml-dev fixtures/plantuml/stdlib/aws/019/020/021/022 (InternetOfThings) + 001 (Analytics) + 023 (MachineLearning) macro lists -->
