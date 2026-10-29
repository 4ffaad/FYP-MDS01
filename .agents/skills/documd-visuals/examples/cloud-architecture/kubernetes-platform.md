# Kubernetes Platform Layout

**Best for**: showing control plane vs worker nodes, and which workloads land where
**Avoid when**: the reader needs application-level flows rather than platform topology (use a cloud or EIP example)
**Answers**: what runs in the cluster, what is managed by the control plane, and how traffic enters

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
title Kubernetes Cluster — Control Plane, Nodes, Traffic Entry
left to right direction

' ── Control plane ──
rectangle "Control Plane" {
  mxgraph.kubernetes.api "API Server" as api
  mxgraph.kubernetes.etcd "etcd\n(cluster state)" as etcd
  mxgraph.kubernetes.sched "Scheduler" as sched
  mxgraph.kubernetes.c_m "Controller\nManager" as cm
}

' ── Traffic entry ──
rectangle "Traffic Entry" {
  mxgraph.kubernetes.ing "Ingress\n(NGINX)" as ing
  mxgraph.kubernetes.svc "Service\n(ClusterIP)" as svc
}

' ── Worker node ──
rectangle "Worker Node" {
  mxgraph.kubernetes.kubelet "kubelet" as kubelet
  mxgraph.kubernetes.pod "Pod: API\n(2 replicas)" as podApi
  mxgraph.kubernetes.pod "Pod: Worker\n(3 replicas)" as podWorker
  mxgraph.kubernetes.pvc "PVC\n(data volume)" as pvc
}

' ── Config / secrets / storage ──
rectangle "Config / Secrets" {
  mxgraph.kubernetes.cm "ConfigMap" as cfg
  mxgraph.kubernetes.secret "Secret" as sec
}

rectangle "Storage" {
  mxgraph.kubernetes.pv "Persistent\nVolume" as pv
}

' ── Wiring ──
ing --> svc : route
svc --> podApi : load balance
api --> sched : schedule
api --> etcd : read/write state
cm --> api : reconcile
kubelet --> podApi : manage
kubelet --> podWorker : manage
podApi --> cfg : mount
podApi --> sec : mount
podApi --> podWorker : enqueue job
podWorker --> pvc : write
pvc --> pv : bind
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `rectangle "Control Plane" { ... }` | Containers express boundaries/nodes (the K8s icon family has no node container — a rectangle is the clearest option) |
| `mxgraph.kubernetes.<icon>` | Common: `api` `etcd` `sched` `c_m` `kubelet` `pod` `svc` `ing` `cm` `secret` `pvc` `pv` `deploy` `sts` `ds` `job` `cronjob` |
| `"Pod: API\n(2 replicas)"` | Put the replica count on the second line — cheaper than drawing two pods |
| Direction | Platform diagrams read better top-to-bottom (default TB) with the entry point at the top |

## Data Shape

Three blocks: **control plane / worker node / external service**. Edges fall into three kinds — scheduling and
management (`api → sched`, `kubelet → pod`), traffic (`ing → svc → pod`), and config/storage (`configmap`, `secret`, `pvc → pv`).

## Pitfalls

- ❌ Drawing a Deployment as if it were the running Pods → ✅ `pod` for running instances, `deploy`/`sts` for controllers (pick one level, do not mix)
- ❌ Skipping the Ingress → Service entry chain → ✅ the entry path is `ing` → `svc` → `pod`
- ❌ Inventing icon names (`replica_set`) → ✅ use the short names from `stencils/kubernetes.md` (`rs`) and verify first
- ❌ Conflating PVC and PV → ✅ storage reads `pod → pvc → pv`

## Alternatives

| Variant | Use instead |
|---|---|
| Application-level architecture only | The AWS/Azure cloud architecture examples |
| Precise network segmentation | `network-topology-enterprise.md` with container rectangles for namespaces/VPCs |
| CI/CD pipeline view | An activity swimlane diagram (`process-and-workflow`) |

<!-- source: mxgraph.kubernetes.* / mxgraph.kubernetes2.* stencil lists (skills/uml/stencils/kubernetes.md) -->
