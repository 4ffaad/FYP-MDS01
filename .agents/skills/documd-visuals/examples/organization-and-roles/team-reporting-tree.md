# Team Tree — Reporting Structure (Infographic)

**Best for**: a small reporting or responsibility tree where the reader needs a recognizable top-down hierarchy
**Avoid when**: the structure is deeper than a few levels or relationships cross between branches
**Answers**: who reports into which branch, and how the team is grouped structurally

```infographic
infographic hierarchy-structure-mirror
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
  title Team Structure
  desc Product, engineering, and operations grouped under one platform lead
  root
    label Platform Lead
    children
      - label Product
        children
          - label Growth PM
          - label Core PM
      - label Engineering
        children
          - label API Team
          - label Billing Team
      - label Operations
        children
          - label SRE
          - label Security Ops
```

## Data Shape

Use one `root` with recursive `children`. Keep labels short and the tree shallow enough to fit cleanly.

## Key Options

| Option | Effect |
|---|---|
| `hierarchy-structure-mirror` | Tree layout with a more balanced mirrored presentation |
| `root` + `children` | Recursive hierarchy data model |
| Short labels | Preserves visual balance in the tree |

## Pitfalls

- ❌ Mixing hierarchy and network semantics → ✅ use this only when parent/child structure is the point
- ❌ Very deep organization charts → ✅ break the tree into smaller focused slices
- ❌ Long node descriptions in every branch → ✅ keep nodes terse and use surrounding text for extra detail

## Alternatives

| Variant | Use instead |
|---|---|
| Generic hierarchy view | `platform-org-structure.md` |
| Relation network | `service-dependency-network.md` |
| Rich narrative team update | `org-update` style HTML/CSS card |

<!-- source: AntV Infographic template reference (`hierarchy-structure-mirror`) + syntax docs for root/children -->