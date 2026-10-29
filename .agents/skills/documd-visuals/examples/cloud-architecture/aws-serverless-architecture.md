# AWS Serverless Platform Architecture

**Best for**: showing an end-to-end AWS request path — client → edge → compute → data → messaging
**Avoid when**: you need precise network hops or device-level detail (use `network-topology-enterprise.md` instead)
**Answers**: which services are involved, and in what order a request flows through them

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
title E-Commerce Serverless Platform — AWS Architecture
left to right direction

' ── Client tier ──
rectangle "Client" {
	mxgraph.aws4.mobile_client "Mobile App" as mobile
	mxgraph.aws4.client "Web Browser" as web
}

' ── Edge / Security ──
rectangle "Edge / Security" {
	mxgraph.aws4.internet "Internet" as internet
	mxgraph.aws4.shield2 "WAF / Shield" as waf
	mxgraph.aws4.application_load_balancer "API Load Balancer" as alb
	mxgraph.aws4.endpoint "API Gateway" as apigw
}

' ── Compute ──
rectangle "Compute" {
	mxgraph.aws4.lambda_function "Auth Lambda\n(JWT verify)" as authLambda
	mxgraph.aws4.lambda_function "Order Lambda\n(business logic)" as orderLambda
	mxgraph.aws4.lambda_function "Worker Lambda\n(async processor)" as workerLambda
}

' ── Data ──
rectangle "Data" {
	mxgraph.aws4.generic_database "DynamoDB\n(orders table)" as dynamo
	mxgraph.aws4.dynamodb_dax "DAX Cache\n(read-through)" as dax
	mxgraph.aws4.rds_instance "RDS Aurora\n(reports)" as rds
}

' ── Messaging ──
rectangle "Messaging / Observability" {
	mxgraph.aws4.queue "SQS Order Queue" as sqs
	mxgraph.aws4.topic "SNS Notify Topic" as sns
	mxgraph.aws4.logs "CloudWatch Logs" as cwlogs
}

' ── Flow ──
mobile --> internet
web --> internet
internet --> waf
waf --> alb
alb --> apigw

apigw --> authLambda : authenticate
apigw --> orderLambda : route request

orderLambda --> dax : cache read
dax --> dynamo : cache miss
orderLambda --> dynamo : write
orderLambda --> sqs : enqueue event

sqs --> workerLambda : trigger
workerLambda --> rds : persist report
workerLambda --> sns : notify
workerLambda --> cwlogs : audit log
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `mxgraph.aws4.<icon> "Label" as alias` | Reference an AWS4 icon (**names must be exact** — see `stencils/aws4.md`) |
| `"Label\n(second line)"` | Second line under the icon (purpose, spec, or scope) |
| `A --> B : label` | Data or call flow (label the protocol or the action) |
| `title` | Diagram title; travels with the diagram into exports |
| `' comment` | Apostrophe starts a comment; it never reaches the rendered diagram |

## Data Shape

A **directed path**: client → edge → compute → data/messaging. Keep synchronous and asynchronous flows in separate
line groups so readers can tell "what the user waits for" from "what runs in the background".

## Pitfalls

- ❌ Guessing icon names (`mxgraph.aws4.sqs`) → ✅ check `stencils/aws4.md` first (the real name is `queue`)
- ❌ Lining every service up in one row → ✅ group by tier (client / edge / compute / data / messaging) and stack within a tier
- ❌ Unlabelled edges → ✅ label the key edges (`authenticate`, `enqueue event`) so the flow is readable
- ❌ Mixing awslib macros (`EC2(...)`) with `mxgraph.*` icons → ✅ pick one icon system per diagram

## Alternatives

| Variant | Use instead |
|---|---|
| Need VPC / subnet / NAT detail | Same icon family + nested `rectangle "VPC" { ... }` containers |
| Non-AWS cloud | `mxgraph.azure.*` / `mxgraph.gcp.*` / `mxgraph.alibaba_cloud.*` |
| Message semantics only, no deployment | `eip-message-flow.md` (EIP icons) |

<!-- source: draw-uml-dev fixtures/plantuml/mxgraph/001-aws-serverless.puml (adapted) -->
