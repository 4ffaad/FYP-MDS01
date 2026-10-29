# Platform Dependency Graph — Services With Icon Nodes (Infographic)

**Best for**: a topology view where services are recognisable by icon rather than name alone
**Avoid when**: an acyclic flow with conditions is needed (use the dagre layout)
**Answers**: which services talk to which, and where the shared foundations sit

```infographic
infographic relation-network-icon-badge
theme
  colorPrimary #2b66c4
  palette
    - #2b66c4
    - #2f9e44
    - #f3a33c
    - #d1242f
    - #7048e8
    - #0f9b9b
    - #c16f8a
    - #7c5a3d
data
  title Service Dependencies — Core Platform
  desc Badges number the dependency depth from the gateway
  nodes
    - id gateway
      label API Gateway
      icon mdi/door-open
      value 1
    - id auth
      label Identity
      icon mdi/shield-account
      value 2
    - id events
      label Event Bus
      icon mdi/source-branch
      value 3
    - id warehouse
      label Warehouse
      icon mdi/database
      value 4
    - id billing
      label Billing
      icon mdi/receipt-text
      value 2
  relations
    - from gateway
      to auth
    - from gateway
      to billing
    - from billing
      to events
    - from events
      to warehouse
```

## Data Shape

`nodes` with `id`, `label`, `icon` and a numeric `value`; `relations` as plain edges (this layout does not
label edges well — put the protocol in the surrounding text). ⚠️ The badge is drawn for **every** node, so
a node without a `value` shows a `0` — here the value is the hop count from the entry point, and the `desc`
says so.

## Key Options

| Option | Effect |
|---|---|
| `infographic relation-network-icon-badge` | Icon and count badge for each service |
| `value 2` | The badge number — the item prints it unconditionally, so it must mean something |
| `relation-network-simple-circle-node` | Plain circles with no badge; best when names are long (the names become tooltips, so keep the figure small) |
| `relation-dagre-flow` design block | Use for directed flows with ranked ordering |

## Pitfalls

- ❌ A node with no `value` → ✅ the badge prints `0`; give it the hop count or switch template
- ❌ Every edge labelled → ✅ this layout crowds quickly; label only the critical path
- ❌ Icons that repeat → ✅ distinct icons make the network scannable
- ❌ Showing all services → ✅ pick the dependency chain being discussed

## Alternatives

| Variant | Use instead |
|---|---|
| Direct dependency chain | `service-dependency-network.md` |
| Escalation with conditions | `incident-escalation-path.md` |
| Capability relationships | `capability-relationship-map.md` |

<!-- source: AntV Infographic syntax docs + template list (`relation-network-icon-badge`) -->
