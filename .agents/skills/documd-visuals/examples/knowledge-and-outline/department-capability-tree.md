# Department Capability Tree — Three Levels (Infographic)

**Best for**: showing how a department decomposes into teams and the capabilities each one owns
**Avoid when**: you need reporting lines and owners (use an org chart)
**Answers**: what the department actually does, and which team owns which part of it

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
  structure hierarchy-tree
  item rounded-rect-node
data
  title Platform Department Capabilities
  desc Three levels: department, team, capability
  root
    label Platform Engineering
    children
      - label Data Platform
        children
          - label Ingestion
      - label Developer Experience
        children
          - label CI Pipelines
      - label Reliability
        children
          - label Observability
```

## Data Shape

`root` plus nested `children`, three levels deep. The tree lays itself out vertically, so keep each node to
one short noun phrase. Capability names should be things a team could own, not projects.

## Key Options

| Option | Effect |
|---|---|
| `design structure hierarchy-tree` | Classic top-down tree rendered by the in-tree hierarchy layout |
| `design item rounded-rect-node` | Boxed nodes; swap for `pill-badge` or `plain-text` for lighter looks |
| `hierarchy-structure` (template) | Built-in template variant with its own styling |

## Pitfalls

- ❌ `infographic hierarchy-tree` as an entry line → ✅ there is no such template; declare
  `structure hierarchy-tree` inside a `design` block
- ❌ Three leaves per team → ✅ the tree spends roughly **365 px per leaf node** (measured: 3 leaves → 1074 px,
  6 leaves → 2212 px wide), so keep the leaf count at three or four and move longer lists to a list layout
- ❌ Four levels of nesting → ✅ at this width three levels is the readable limit

## Alternatives

| Variant | Use instead |
|---|---|
| Reporting lines with names | `platform-org-structure.md` |
| Free-form knowledge map | `enterprise-knowledge-map.md` |
| Capability dependencies between services | `platform-dependency-graph.md` |

<!-- source: AntV Infographic syntax docs + structure registry (`hierarchy-tree`) -->
