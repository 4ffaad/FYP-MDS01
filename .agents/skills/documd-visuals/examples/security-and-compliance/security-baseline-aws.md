# Security Baseline (AWS, portable icons)

**Best for**: compliance and security reviews — identity, encryption, detection and audit in one picture
**Avoid when**: the audience wants attack paths (use a threat model) or the runtime topology
**Answers**: which controls protect which resource, and what produces audit evidence

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
!include <awslib/SecurityIdentityCompliance/all.puml>
!include <awslib/ManagementGovernance/all.puml>
!include <awslib/Storage/all.puml>
!include <awslib/Compute/all.puml>
!include <awslib/Database/all.puml>

hide stereotype
title Security Baseline — Controls, Data Protection, Evidence

' ── Identity ──
rectangle "Identity" {
  IdentityandAccessManagement(iam, "IAM\n(policies, roles)", " ")
  IdentityAccessManagementRole(workloadRole, "Workload role\n(least privilege)", " ")
  Cognito(cognito, "Cognito\n(MFA, federation)", " ")
  CertificateManager(acm, "ACM\n(TLS certs)", " ")
}

' ── Protection ──
rectangle "Data protection" {
  KeyManagementService(kms, "KMS\n(CMKs, rotation)", " ")
  CloudHSM(hsm, "CloudHSM\n(root of trust)", " ")
  SecretsManager(secrets, "Secrets Manager\n(rotation)", " ")
  SimpleStorageServiceBucket(encryptedBucket, "S3\n(SSE-KMS)", " ")
  Aurora(encryptedDb, "RDS Aurora\n(TDE via KMS)", " ")
}

' ── Perimeter ──
rectangle "Perimeter" {
  Shield(shield, "Shield Advanced\n(DDoS)", " ")
  WAF(waf, "WAF\n(L7 rules)", " ")
  NetworkFirewall(nfw, "Network Firewall\n(egress control)", " ")
}

' ── Detection & audit ──
rectangle "Detection and audit" {
  CloudTrail(trail, "CloudTrail\n(org trail)", " ")
  Config(config, "Config\n(conformance packs)", " ")
  Inspector(inspector, "Inspector\n(vuln scanning)", " ")
  Macie(macie, "Macie\n(PII discovery)", " ")
  AuditManager(audit, "Audit Manager\n(evidence)", " ")
}

' ── Control flow ──
hsm --> kms : root key
kms --> encryptedBucket : SSE-KMS
kms --> encryptedDb : TDE
secrets --> encryptedDb : rotate credentials
iam --> workloadRole : assume
cognito --> acm : OIDC endpoints
workloadRole --> encryptedBucket : scoped access
acm --> encryptedBucket : TLS in transit

shield --> waf : scrubbed traffic
waf --> nfw : filtered traffic
nfw --> encryptedDb : allowed egress only

config --> trail : evaluate against trail
inspector --> encryptedDb : findings
macie --> encryptedBucket : PII findings
trail --> audit : evidence
config --> audit : conformance results
inspector --> audit : findings

note right of audit
  every control feeds the same evidence
  store: this is the compliance story
end note
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `!include <awslib/SecurityIdentityCompliance/all.puml>` | `IdentityandAccessManagement`, `IdentityAccessManagementRole`, `KeyManagementService`, `CloudHSM`, `SecretsManager`, `CertificateManager`, `Inspector`, `Macie`, `WAF`, `Shield`, `NetworkFirewall`, `AuditManager`, `Cognito` |
| `!include <awslib/ManagementGovernance/all.puml>` | `CloudTrail`, `Config`, `CloudFormation*`, `CloudWatch*` |
| `rectangle "<Domain>" { … }` | Security domains as containers — the grouping itself communicates the control model |
| `note right of X` | Evidence/audit remarks (avoid `note bottom of` — see the engine notes) |

## Data Shape

Four control domains — **identity / data protection / perimeter / detection & audit** — with a single evidence
sink that every detective control writes to. Protection edges are the chain root-of-trust → key → data.

## Pitfalls

- ❌ Controls listed but not connected to assets → ✅ draw the protection edge (KMS → store) so coverage is visible
- ❌ Detection without an evidence store → ✅ the audit store is what turns controls into compliance
- ❌ Mixing preventive and detective controls in one box → ✅ separate them; reviewers audit them differently
- ❌ Omitting egress control → ✅ data-exfiltration paths are an egress question, not an ingress one

## Alternatives

| Variant | Use instead |
|---|---|
| Attack paths and mitigations | `threat-model-trust-boundaries.md` |
| Zero-trust runtime access chain | `zero-trust-access.md` |
| Control matrix with owners and status | An infocard `compliance-audit` / `risk-register` card |

<!-- source: draw-uml-dev fixtures/plantuml/stdlib/aws/032/033 (SecurityIdentityCompliance) + 024/025 (ManagementGovernance) + 034 (Storage) macro lists -->
