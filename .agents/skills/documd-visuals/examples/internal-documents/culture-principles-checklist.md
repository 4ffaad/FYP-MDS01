# Culture Principles Checklist — Everyday Behaviours (Infographic)

**Best for**: turning abstract values into a short list of checkable behaviours
**Avoid when**: the reader wants the values themselves (put those in the heading)
**Answers**: what "we value X" actually looks like in daily work

```infographic
infographic list-grid-done-list
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
  title How We Work — Team Principles
  desc Behaviours we hold each other to
  lists
    - label Write it down
      desc Decisions live in docs, not DMs
    - label Ask early
      desc Raise uncertainty before it becomes rework
    - label Small changes
      desc Reviewable diffs over big rewrites
    - label Own the outcome
      desc Ship, watch it, then iterate
```

## Data Shape

Four `lists` items, each pairing a short imperative with the behaviour it implies. The done-list styling reads
as a checklist, so items should be things a person can genuinely do or not do.

## Key Options

| Option | Effect |
|---|---|
| `infographic list-grid-done-list` | Checkbox-style items in a grid |
| `list-grid-badge-card` | Badge cards when each principle needs an example |
| `list-row-simple-horizontal-arrow` | Row variant for onboarding decks |

## Pitfalls

- ❌ Values as slogans ("Be excellent") → ✅ behaviours are observable; slogans are not
- ❌ Ten principles → ✅ four or five are remembered, ten are ignored
- ❌ No counter-example → ✅ pair each behaviour with what it replaces in the surrounding text

## Alternatives

| Variant | Use instead |
|---|---|
| Charter with mandates and cadence | `board-committee-charter.md` |
| Internal process requirements | `change-request-columns.md` |
| Team capability overview | `team-capability-icon-grid.md` |

<!-- source: AntV Infographic syntax docs + template list (`list-grid-done-list`) -->
