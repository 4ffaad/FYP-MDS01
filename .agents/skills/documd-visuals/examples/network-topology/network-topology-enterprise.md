# Enterprise Network Topology

**Best for**: physical/logical device layout — ISP edge, DMZ, server room, office floor, wireless
**Avoid when**: the reader needs application or message flows (use a cloud architecture or EIP example)
**Answers**: what devices exist, how they interconnect, and which zone each device belongs to

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
title Medium Enterprise — Network Topology
left to right direction

' ── External ──
rectangle "External" {
	mxgraph.networks.cloud "Internet\n(ISP Uplink 1Gbps)" as internet
}

' ── Edge layer ──
rectangle "Edge" {
	mxgraph.networks.modem "Fiber Modem\n(Edge CPE)" as modem
	mxgraph.networks.router "Edge Router\n(BGP / 10Gbps)\n10.0.0.1" as router
	mxgraph.networks.firewall "Next-Gen Firewall\n(NGFW / IDS)\n10.0.1.1" as fw
}

' ── DMZ ──
rectangle "DMZ" {
	mxgraph.networks.server "Web Server\n10.10.1.10\n(Nginx / TLS)" as webSrv
	mxgraph.networks.mail_server "Mail Server\n10.10.1.20\n(Postfix / SMTP)" as mailSrv
}

' ── Core ──
rectangle "Core" {
	mxgraph.networks.switch "Core Switch L3\n10.20.0.1\n(VLAN trunk)" as coreSwitch
}

' ── Server room ──
rectangle "Server Room" {
	mxgraph.networks.mainframe "ERP Mainframe\n10.20.10.5" as erp
	mxgraph.networks.server "Database Server\n10.20.10.10\n(PostgreSQL)" as dbSrv
	mxgraph.networks.server "File Server\n10.20.10.15\n(NFS / SMB)" as fileSrv
}

' ── Office floor ──
rectangle "Office Floor" {
	mxgraph.networks.hub "Office Hub\nFloor 2 (L2)" as officeHub
	mxgraph.networks.laptop "Developer Laptops\n(12 devices)" as devLaptops
	mxgraph.networks.monitor "Workstations\n(30 devices)" as workstations
	mxgraph.networks.printer "Network Printer\n10.30.1.100" as printer
}

' ── Wireless / BYOD ──
rectangle "Wireless / BYOD" {
	mxgraph.networks.mobile "BYOD & Guest WiFi\n(802.11ac)" as byod
}

' ── Links: physical links use --, directed flows use --> ──
internet -- modem
modem -- router
router -- fw

fw -- webSrv
fw -- mailSrv
fw -- coreSwitch

coreSwitch -- erp
coreSwitch -- dbSrv
coreSwitch -- fileSrv
coreSwitch -- officeHub

officeHub -- devLaptops
officeHub -- workstations
officeHub -- printer
officeHub .. byod : wireless
@enduml
```

## Key Options

| Syntax | Effect |
|---|---|
| `mxgraph.networks.<icon>` | Generic device icons: `cloud` `modem` `router` `firewall` `switch` `hub` `server` `mail_server` `web_server` `mainframe` `laptop` `monitor` `printer` `mobile` `wireless_hub` `storage` |
| `mxgraph.cisco.*` / `mxgraph.cisco19.*` | Vendor-specific icons when the audience expects them (`routers.router`, `switches.layer_3_switch`, `security.firewall`, `servers.fileserver`) |
| `A -- B` | Physical link (no arrowhead) — the right choice for cabling |
| `A --> B` | Directed traffic flow — use when direction matters |
| `A .. B` / `A ..> B` | Logical/VPN/wireless links |
| Multi-line labels | Put IP address and role on lines 2–3 — that is what network engineers look for |

## Data Shape

**Zones as horizontal groups** (external → edge → DMZ → core → server room / office / wireless), devices as icons,
links as `--` (physical) or `..` (wireless/logical). Reader question: "what sits where, and what is connected to what".

## Pitfalls

- ❌ Using `-->` for everything → ✅ reserve `--` for physical links and `..` for wireless/VPN; direction is information
- ❌ Hiding IPs → ✅ include them in the label — a topology without addresses is only decoration for this audience
- ❌ One flat row of devices → ✅ keep zones visually separated (even without explicit `rectangle` boxes)
- ❌ Mixing `networks.*` and `cisco.*` icons randomly → ✅ pick the family that matches the audience (vendor-neutral vs Cisco)

## Alternatives

| Variant | Use instead |
|---|---|
| Cloud-hosted network (VPC, subnets, security groups) | Cloud architecture example with nested containers |
| Security zones and trust boundaries | `zero-trust-access.md` / threat model example |
| Rack-level physical layout | `mxgraph.rack.*` / `mxgraph.rackGeneral.*` families |

<!-- source: draw-uml-dev fixtures/plantuml/mxgraph/005-network-topology.puml (adapted) -->
