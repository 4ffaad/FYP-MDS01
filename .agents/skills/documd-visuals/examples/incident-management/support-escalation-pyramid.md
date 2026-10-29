# Support Escalation Pyramid — From Self-Serve To Engineering (Infographic)

**Best for**: explaining a support model where cost per contact rises as cases climb
**Avoid when**: you need volumes per tier (add the numbers to `desc`)
**Answers**: which tier handles a case, and what is expected to be resolved at each level

```infographic
infographic sequence-pyramid-simple
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
  title Support Escalation Model
  desc Narrowest tier handles the hardest cases
  sequences
    - label Engineering
      desc Defects needing code changes
    - label Product support
      desc Configuration and data issues
    - label Specialist
      desc Billing, security, compliance
    - label Self-serve
      desc Help centre and in-app guides
```

## Data Shape

`sequences` ordered from the top of the pyramid down. Because the shape narrows upward, the **serialised
case** belongs at the top and the volume tier at the bottom.

## Key Options

| Option | Effect |
|---|---|
| `infographic sequence-pyramid-simple` | Flat pyramid layers in sequence order |
| `list-pyramid-compact-card` | Use when tiers need richer descriptions |
| `relation-dagre-flow` design block | Use when cases can skip tiers |

## Pitfalls

- ❌ Contact volumes omitted → ✅ the pyramid implies scarcity; if engineering absorbs 40% of cases, say so
- ❌ Tiers without entry criteria → ✅ each `desc` should tell a support agent when to escalate
- ❌ Confusing it with hierarchy → ✅ this is a flow of cases, not a reporting structure

## Alternatives

| Variant | Use instead |
|---|---|
| Escalation as a directed path | `incident-escalation-path.md` |
| Support tiers as a maturity model | `reliability-maturity-ladder.md` |
| Daily support rhythm | `support-shift-handover.md` |

<!-- source: AntV Infographic syntax docs + template list (`sequence-pyramid-simple`) -->
