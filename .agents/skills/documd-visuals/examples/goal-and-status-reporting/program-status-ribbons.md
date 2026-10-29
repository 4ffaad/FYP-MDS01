# Programme Status Ribbons — One Card Per Workstream (Infographic)

**Best for**: a steering-committee view of several workstreams on one screen
**Avoid when**: workstreams need full status reports (link them instead)
**Answers**: which workstreams are healthy, which are at risk, and which are blocked

```infographic
infographic list-grid-ribbon-card
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
  title Programme Health — Q3
  desc Five workstreams, status in the description
  lists
    - label Identity migration
      desc On track — 62% complete
    - label Billing split
      desc At risk — waiting on legal
    - label Data residency
      desc On track — EU region live
    - label Mobile release
      desc Blocked — store review
    - label Support tooling
      desc On track — pilot running
```

## Data Shape

One `lists` item per workstream; `desc` carries the status word first so the eye can scan the column. Keep to
six items maximum.

## Key Options

| Option | Effect |
|---|---|
| `infographic list-grid-ribbon-card` | Ribbon styling; each card reads as a titled lane |
| `list-grid-badge-card` | Lighter cards when status colour is unnecessary |
| `list-grid-compact-card` | Denser grid for seven or more workstreams |

## Pitfalls

- ❌ Status buried at the end of a sentence → ✅ start `desc` with On track / At risk / Blocked
- ❌ Equal detail for every workstream → ✅ expand only the ones with a decision attached
- ❌ Using it as a status archive → ✅ this is the current picture; history belongs in the tracker

## Alternatives

| Variant | Use instead |
|---|---|
| Headline numbers only | `leadership-metric-board.md` |
| Milestone dates on one line | `platform-milestone-timeline.md` |
| Stage counts across accounts | `onboarding-milestone-grid.md` |

<!-- source: AntV Infographic syntax docs + template list (`list-grid-ribbon-card`) -->
