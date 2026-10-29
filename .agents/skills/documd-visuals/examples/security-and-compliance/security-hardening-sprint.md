# Descending Zigzag — Security Hardening Sprint (Infographic)

**Best for**: an unordered-looking work list that a reader should still walk through in a set sequence
**Avoid when**: items are truly parallel, or the sequence is long enough to need dates
**Answers**: what the hardening sprint covers, in the order the team will burn it down

```infographic
infographic list-zigzag-down-simple
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
  title Security Hardening Sprint
  desc Six workstreams, ordered by blast radius reduction per hour of effort
  lists
    - label Rotate exposed credentials
      desc Every key that appeared in a build log in the last 90 days
    - label Enforce signed artifacts
      desc Pipeline refuses unsigned images at the deploy step
    - label Close public buckets
      desc Inventory, then default-deny on all object stores
    - label Patch runtime images
      desc Rebuild from patched base images and roll canaries first
    - label Add dependency scanning
      desc Block merges that introduce a known high-severity finding
    - label Rehearse key loss
      desc Restore the production database from escrow in a drill
```

## Data Shape

`lists` with one entry per workstream. The template lays the rows out on a descending zigzag, so the array
order is the burn-down order — highest urgency first.

## Key Options

| Option | Effect |
|---|---|
| `list-zigzag-down-simple` | Downward zigzag rows; the reading path is implied rather than drawn |
| `list-zigzag-up-simple` | Upward variant, which reads as an ascent or growth sequence |
| `list-waterfall-compact-card` | Steps that also carry amounts |
| Six entries | Zigzag rows alternate direction, so pairs of entries are what the eye groups — keep it even |

## Pitfalls

- ❌ Unordered items in a zigzag → ✅ the alternating layout implies a route; if the items are parallel, use a grid
- ❌ Odd entry counts → ✅ the last row points the wrong way and the rhythm breaks
- ❌ Using it where the reader must compare items → ✅ the zigzag is a walking path, not a comparison surface
- ❌ Long descriptions → ✅ each row is short by construction; move detail into the runbook itself

## Alternatives

| Variant | Use instead |
|---|---|
| Numbered ordered steps | `audit-trail-checkpoints.md` |
| Parallel work items | `tooling-standard-inventory.md` |
| Items with progress facts | `program-status-ribbons.md` |

<!-- source: AntV Infographic template registry 0.2.20 (`list-zigzag-down-simple`, structure `list-zigzag-down`) -->
