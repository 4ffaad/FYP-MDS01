# Threat Model with Trust Boundaries

**Best for**: pairing assets with attack paths and the control that mitigates each one
**Avoid when**: the audience wants the target architecture rather than the risks (use the zero-trust or cloud example)
**Answers**: what can be attacked, from where, and what stops it

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
title Threat Model — Trust Boundaries and Mitigations
left to right direction

' ── Untrusted ──
rectangle "Untrusted Zone" {
  mxgraph.networks.users "External Users" as users
  mxgraph.networks.virus "Malware / Bots" as malware
  mxgraph.networks.unsecure "Shadow IT\n(unmanaged devices)" as shadow
}

' ── Edge boundary ──
rectangle "Edge Boundary" {
  mxgraph.cisco_safe.security_icons.waf "WAF" as waf
  mxgraph.cisco_safe.security_icons.ddos "Anti-DDoS" as ddos
  mxgraph.cisco_safe.security_icons.firewall "Perimeter FW" as fw
}

' ── Application zone ──
rectangle "Application Zone" {
  mxgraph.networks.web_server "Web / API Tier" as web
  mxgraph.aws4.lambda_function "Serverless\nFunctions" as fn
  mxgraph.cisco_safe.security_icons.vpn "Site-to-Site VPN" as vpn
}

' ── Data zone ──
rectangle "Data Zone" {
  mxgraph.aws4.generic_database "Primary DB" as db
  mxgraph.aws4.s3 "Object Storage" as s3
  mxgraph.aws4.secrets_manager "Secrets" as secrets
}

' ── Detection ──
rectangle "Detection & Response" {
  mxgraph.cisco_safe.security_icons.ids "IDS / IPS" as ids
  mxgraph.cisco_safe.security_icons.siem "SIEM" as siem
}

' ── Attack paths (dashed) ──
users ..> waf : T1190 exploit
malware ..> ddos : T1498 flood
shadow ..> vpn : T1133 external service
waf ..> web : filtered traffic
ddos ..> fw : scrubbed traffic
fw --> web : allowed flows
web --> fn : invoke
fn --> db : read/write
fn --> s3 : objects
fn --> secrets : fetch credentials

' ── Mitigation / detection edges ──
web --> ids : telemetry
db --> siem : audit logs
ids --> siem : alerts
siem --> fw : block rule
siem --> secrets : rotate key
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `rectangle "<Zone>" { ... }` | Trust boundary — put the boundary name on the box, not on an edge |
| `A ..> B : T#### threat` | Dashed edges carry the threat (MITRE-style IDs keep it short and unambiguous) |
| `A --> B` | Allowed/expected traffic (solid = in-policy path) |
| `mxgraph.networks.virus` / `unsecure` | Adversary and unmanaged-device nodes exist as icons; use them instead of hand-drawn symbols |
| Direction | Default TB works well: untrusted on top, data at the bottom |

## Data Shape

Three columns of meaning: **threat sources → boundaries/controls → assets**, with a detection block that receives
telemetry and can push back (block rule, key rotation). Reader question: "what is exposed, what stops it, who notices".

## Pitfalls

- ❌ Listing only threats without controls → ✅ every threat edge should terminate at a control, not at the asset
- ❌ Using the same line style for attacks and normal traffic → ✅ dashed for threats, solid for allowed flows
- ❌ Forgetting the feedback loop → ✅ the SIEM should push actions back (block/rotate); otherwise detection looks passive
- ❌ Overlapping zones with no visual boundary → ✅ one `rectangle` per trust level; boundary crossings are the story

## Alternatives

| Variant | Use instead |
|---|---|
| Target-state security architecture (no threats) | `zero-trust-access.md` |
| Network/device-level view | `network-topology-enterprise.md` |
| Compliance mapping to controls | An infocard `compliance-audit` / `risk-register` style card |

<!-- source: cisco_safe + networks stencil lists (security_icons.*, virus, unsecure) -->
