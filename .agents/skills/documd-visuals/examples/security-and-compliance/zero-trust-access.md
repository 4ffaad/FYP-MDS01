# Zero-Trust Access Path

**Best for**: showing how a request is authenticated, authorised and encrypted before it reaches data
**Avoid when**: the reader needs the zone/device layout (use the network topology example)
**Answers**: where identity is checked, what protects data at rest and in transit, and which component issues secrets

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
left to right direction
title Zero-Trust Access — Identity, Policy, Encryption

' ── Identity ──
rectangle "Identity Provider" {
  mxgraph.aws4.cognito "Cognito\n(user pool)" as idp
  mxgraph.aws4.identity_and_access_management "IAM\n(roles / policies)" as iam
  mxgraph.aws4.sts "STS\n(temporary creds)" as sts
}

' ── Policy enforcement ──
rectangle "Policy Enforcement" {
  mxgraph.cisco_safe.security_icons.ngfw "NGFW\n(inspection)" as ngfw
  mxgraph.cisco_safe.security_icons.waf "WAF\n(L7 filtering)" as waf
  mxgraph.cisco_safe.security_icons.ids "IDS / IPS\n(anomaly)" as ids
  mxgraph.cisco_safe.security_icons.nac "NAC\n(device posture)" as nac
}

' ── Key management ──
rectangle "Key Management" {
  mxgraph.aws4.key_management_service "KMS\n(CMK)" as kms
  mxgraph.aws4.secrets_manager "Secrets\nManager" as secrets
  mxgraph.aws4.private_certificate_authority "Private CA" as pca
}

' ── Protected data ──
rectangle "Protected Data" {
  mxgraph.aws4.s3 "S3 Bucket" as s3
  mxgraph.aws4.encrypted_data "Encrypted\nObjects" as encS3
  mxgraph.aws4.rds "RDS" as rds
  mxgraph.aws4.encrypted_data "Encrypted\nVolumes" as encRds
}

' ── Audit ──
rectangle "Audit / Correlation" {
  mxgraph.cisco_safe.security_icons.siem "SIEM\n(correlation)" as siem
}

' ── Flow: identity first, then policy, then data ──
idp --> sts : federate
sts --> iam : assume role
iam --> ngfw : signed request
ngfw --> waf : inspect
waf --> ids : anomaly check
nac --> ngfw : posture signal

pca --> siem : cert events
ngfw --> siem : logs
ids --> siem : alerts
waf --> siem : logs

kms --> s3 : SSE-KMS
kms --> rds : TDE
secrets --> rds : DB credentials
s3 --> encS3
rds --> encRds

ngfw --> s3 : authorised access
siem --> kms : key-use anomaly
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `rectangle "Zone" { ... }` | Trust boundary / security zone — the container *is* the message |
| `mxgraph.cisco_safe.security_icons.*` | Security control icons: `ngfw` `waf` `ids` `siem` `nac` `vpn` `ddos` `firewall` |
| `mxgraph.aws4.key_management_service` / `secrets_manager` / `private_certificate_authority` | AWS-flavoured key/cert icons |
| `mxgraph.aws4.encrypted_data` | Explicit "this is the encrypted form" node — makes encryption visible instead of implied |
| Default TB direction | Keeps the access path compact in static exports while preserving the same control sequence |

## Data Shape

Four zones — **Identity / Policy enforcement / Key management / Protected data** — plus a dedicated audit sink that every
control writes to. Edges answer "who checks what, and with which key".

## Pitfalls

- ❌ Drawing "encrypted data" as just a lock emoji → ✅ use `encrypted_data` nodes so the encrypted representation is explicit
- ❌ Auth and authz conflated → ✅ `idp` answers *who you are*, `iam`/`sts` answer *what you may do*
- ❌ No audit path → ✅ every control should have a line to SIEM; that is the zero-trust evidence trail
- ❌ Mixing vendor icon families per diagram → ✅ pick AWS4 **or** cisco_safe for controls and stay consistent

## Alternatives

| Variant | Use instead |
|---|---|
| Threat-focused view (attack surfaces, mitigations) | `threat-model-trust-boundaries.md` |
| Network/zone layering only | `network-topology-enterprise.md` |
| Compliance evidence mapping | An infocard-style matrix or `matrix-table` card |

<!-- source: draw-uml-dev fixtures/plantuml/mxgraph/010-aws-security.puml + cisco_safe stencil list (adapted) -->
