# Org Structure — Three-Level Team Tree (Infographic)

**Best for**: a compact organization or responsibility tree with only a few levels
**Avoid when**: the hierarchy is deep, highly cross-linked, or needs formal architecture semantics
**Answers**: who sits under whom, and how the team is grouped at a glance

```infographic
infographic hierarchy-structure
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
  title Platform Organization
  desc Product, engineering, and reliability grouped in one tree
  root
    label Platform Group
    children
      - label Product
        children
          - label Growth PM
          - label Core PM
      - label Engineering
        children
          - label API Team
          - label Billing Team
      - label Reliability
        children
          - label SRE
          - label Security Ops
```

## Data Shape

Use one `root` object with nested `children`. Keep it shallow and compact; this template is best for a readable 2–3 level tree.

## Key Options

| Option | Effect |
|---|---|
| `hierarchy-structure` | Generic hierarchy layout |
| `root` + `children` | Recursive tree structure |
| Short `label` values | Keeps the hierarchy readable in one export |

## Pitfalls

- ❌ Deep or wide trees in one frame → ✅ split into multiple focused hierarchies before it turns unreadable
- ❌ Cross-links between branches → ✅ this family is for trees, not networks
- ❌ Putting role descriptions in every node → ✅ keep node labels short; move extra detail into a different artifact

## Alternatives

| Variant | Use instead |
|---|---|
| Network of relationships | `service-dependency-network.md` |
| Formal enterprise structure | PlantUML or ArchiMate examples |
| Responsibility matrix | HTML/CSS or tabular view |

<!-- source: AntV Infographic syntax docs (`root` + `children`) + template list (`hierarchy-structure`) -->