# Stakeholder Handover Ring — Who Passes What To Whom (Infographic)

**Best for**: showing the stakeholder ring around a decision, where each party hands off to the next
**Avoid when**: the connections are one-directional dependencies (use a dependency graph)
**Answers**: what each party passes on, and in which order the decision travels

```infographic
infographic sequence-circle-arrows-indexed-card
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
  title Launch Decision Handovers
  desc What each party passes on, in order
  sequences
    - label Scope
      desc Product → Design
    - label Flows
      desc Design → Engineering
    - label Threat model
      desc Engineering → Security
    - label Runbook gaps
      desc Security → Support
    - label Field feedback
      desc Support → Product
```

## Data Shape

`sequences` — one step per handover, in ring order. `label` is the artefact that travels (keep it to one
line: the card draws a rule under the label, and a wrapped label sits on top of it), `desc` names the two
parties. The structure closes the loop with a return arrow, so the last step must hand back to the first.

## Key Options

| Option | Effect |
|---|---|
| `infographic sequence-circle-arrows-indexed-card` | Numbered cards around a ring, with the return arrow |
| `label` / `desc` | The artefact, then the parties — both are drawn, unlike a relation label |
| `sequences` | Step order is the array order; the ring is closed for you |
| `relation-circle-*` | Use only when a **number** per node is the story: both variants print one, and neither draws relation labels |

## Pitfalls

- ❌ A ring that is really a chain → ✅ if it does not loop, use a plain `sequence-*` or dagre layout
- ❌ Handover artefacts written as `relations[].label` → ✅ the relation structures draw no edge labels; the words vanish. Use a sequence, where `label` and `desc` are rendered
- ❌ Nine steps → ✅ six is the practical maximum around a 900×600 circle
- ❌ A `relation-circle-circular-progress` wheel with no numbers → ✅ its rings print `0%`; only use it when each node has a real percentage

## Alternatives

| Variant | Use instead |
|---|---|
| Concept relationship map | `capability-relationship-map.md` |
| Platform dependency topology | `platform-dependency-graph.md` |
| Escalation ladder | `incident-escalation-path.md` |

<!-- source: AntV Infographic syntax docs + template list (`sequence-circle-arrows-indexed-card`, item `indexed-card`: `label` + `desc`) -->
