# Incident Escalation Path — Who Picks Up Next (Infographic)

**Best for**: one page that answers "the alert fired, who is responsible now?"
**Avoid when**: the flow branches heavily (use a full flowchart in plantuml)
**Answers**: the escalation ladder, the trigger for each hop, and where the path ends

```infographic
infographic
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
design
  structure relation-dagre-flow
  item simple-circle-node
data
  title Incident Escalation Ladder
  desc Each edge names the condition that causes the hand-off
  nodes
    - id alert
      label Alert fires
    - id oncall
      label On-call engineer
    - id lead
      label Team lead
    - id vendor
      label Vendor escalation
    - id postmortem
      label Postmortem
  relations
    - from alert
      to oncall
      label paged in 5 min
    - from oncall
      to lead
      label unresolved after 1 hour
    - from lead
      to vendor
      label platform defect confirmed
    - from oncall
      to postmortem
      label service restored
```

## Data Shape

`nodes` (with `id` and human `label`) plus `relations`; each relation carries the **condition** as its
`label`. The dagre layout handles a fan-out to two different next steps, which a plain sequence cannot.

## Key Options

| Option | Effect |
|---|---|
| `design structure relation-dagre-flow` | Directed layout with automatic rank ordering |
| `design item simple-circle-node` | Circle nodes; `rounded-rect-node` suits longer labels |
| `relation-network-*` templates | Use for undirected topology instead of a directed path |

## Pitfalls

- ❌ `infographic relation-dagre-flow` as an entry line → ✅ no such template exists; declare the structure
  in a `design` block
- ❌ Unlabelled edges → ✅ the trigger condition is the most useful part of each arrow
- ❌ Drawing the whole incident process → ✅ escalation only; diagnostics belong in the runbook

## Alternatives

| Variant | Use instead |
|---|---|
| Linear response steps | `incident-response-runbook.md` |
| Service topology without direction | `service-dependency-network.md` |
| Handover across shifts | `support-shift-handover.md` |

<!-- source: AntV Infographic syntax docs + structure registry (`relation-dagre-flow`) -->
