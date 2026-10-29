# Enterprise Integration Message Flow (EIP)

**Best for**: message-driven integration where routing, filtering, aggregation and dead-lettering matter
**Avoid when**: the audience cares about deployed infrastructure rather than message semantics (use a cloud architecture example)
**Answers**: how a message travels, where it can be routed/filtered, and what happens when it fails

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
title Order Integration Bus — Enterprise Integration Patterns
left to right direction

' ── Producers ──
rectangle "Producers" {
	rectangle "OrderService\n(Producer)" as orderSvc
	rectangle "ReturnService\n(Producer)" as returnSvc
}

' ── Entry channel & wire tap ──
rectangle "Entry / Audit" {
	mxgraph.eip.messageChannel "Inbound\nOrder Channel" as inboundCh
	mxgraph.eip.wire_tap "Audit\nWire Tap" as auditTap
	mxgraph.eip.message_store "Audit\nMessage Store" as auditStore
}

' ── Routing ──
rectangle "Routing" {
	mxgraph.eip.content_based_router "Order Type\nRouter" as router
}

' ── Downstream channels ──
rectangle "Channels" {
	mxgraph.eip.messageChannel "Fulfillment\nChannel" as fulfillCh
	mxgraph.eip.messageChannel "Payment\nChannel" as paymentCh
	mxgraph.eip.messageChannel "Notification\nChannel" as notifyCh
}

' ── Payment pipeline ──
rectangle "Payment Review" {
	mxgraph.eip.message_filter "Fraud\nFilter" as fraudFilter
	mxgraph.eip.aggregator "Auth + Fraud\nAggregator" as aggregator
}

' ── Dead-letter ──
rectangle "Dead-Letter" {
	mxgraph.eip.deadLetterChannel "Dead Letter\nQueue" as dlq
	mxgraph.eip.message_store "DLQ\nInspection Store" as dlqStore
}

' ── Consumers ──
rectangle "Consumers" {
	mxgraph.eip.service_activator "Fulfillment\nService" as fulfillSvc
	mxgraph.eip.service_activator "Payment\nService" as paymentSvc
	mxgraph.eip.event_driven_consumer "Notification\nConsumer" as notifyConsumer
}

' ── Flow ──
orderSvc --> inboundCh : publish
returnSvc --> inboundCh : publish

inboundCh --> auditTap
auditTap --> router : pass-through
auditTap --> auditStore : record copy

router --> fulfillCh : type=product
router --> paymentCh : type=payment
router --> notifyCh : type=email/sms

fulfillCh --> fulfillSvc
paymentCh --> fraudFilter
fraudFilter --> aggregator : score < threshold
fraudFilter --> dlq : suspicious
aggregator --> paymentSvc : both checks passed
notifyCh --> notifyConsumer

dlq --> dlqStore : persist for review
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `mxgraph.eip.<icon>` | EIP pattern icons: `messageChannel` `content_based_router` `message_filter` `aggregator` `wire_tap` `message_store` `deadLetterChannel` `service_activator` `event_driven_consumer` |
| `rectangle "A\n(B)"` | Producers/services when no matching icon exists |
| `A --> B : condition` | Put the routing predicate on the edge (`type=payment`) |
| Dashed `..>` | Optional for audit/bypass paths — this example keeps solid lines for the main chain; pick one convention per diagram |

## Data Shape

**Producer → channel → router → channel → consumer**, plus two side paths: audit (wire tap → store) and failure
(filter → DLQ → store). The reader question is "how does the message travel, where does it branch, where does it go on failure".

## Pitfalls

- ❌ Drawing only the happy path → ✅ always include the dead-letter/retry path — that is what an EIP diagram is for
- ❌ Representing channels and components with the same shape → ✅ channels use `messageChannel`, components use `service_activator` or a plain rectangle
- ❌ Omitting the routing predicate → ✅ label every outbound edge, otherwise the routing logic is unreadable
- ❌ Giving audit edges the same visual weight as the main chain → ✅ mark them in the label (`record copy`)

## Alternatives

| Variant | Use instead |
|---|---|
| Service orchestration (who calls whom) | A `sequence` diagram (the `interfaces-and-interactions` scenario) |
| Event-driven deployment shape | A cloud architecture example with `mxgraph.aws4.eventbridge*` / `topic` / `queue` |
| Human/business process (approvals) | The `bpmn` icon family with activity swimlanes |

<!-- source: draw-uml-dev fixtures/plantuml/mxgraph/002-eip-messaging.puml (adapted) -->
