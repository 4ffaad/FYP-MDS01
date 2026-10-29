# Service Mix for a Colour-Blind Audience (Infographic)

**Best for**: a chart that has to be read correctly by everyone — published material, a public
dashboard, anything where a reader may not separate red from green
**Avoid when**: the figure is decoration rather than information — the CUD hues are chosen to be
told apart, not to be pretty, and they look plain next to a vivid marketing palette
**Answers**: how the current service mix splits, using colours that stay distinguishable under every
kind of colour vision

```infographic
infographic chart-pie-simple
theme
  colorPrimary #0072b2
  palette
    - #0072b2
    - #e69f00
    - #009e73
    - #d55e00
    - #56b4e9
    - #f0e442
    - #cc79a7
    - #6e6e6e
data
  title Service mix
  values
    - label API
      value 34
    - label Web
      value 22
    - label Batch
      value 18
    - label Search
      value 14
    - label Stream
      value 8
    - label Admin
      value 4
```

## Data Shape

One row per service with a share or count. Six slices is already at the edge of what a pie can
carry — beyond that, group the tail into "other".

## Key Options

| Option | Effect |
|---|---|
| `colorPrimary` only | Drives every element of a single-colour template |
| `colorPrimary` + `palette` | Both, in one block — multi-colour templates read the ramp, mono ones ignore it |
| Fewer ramp entries | Match the number of live categories instead of shipping eight |

## Pitfalls

- ❌ Picking the colours yourself and treating this as a normal palette → ✅ these eight are the
  Okabe–Ito set; swapping one out is what breaks the guarantee
- ❌ Relying on colour alone to carry the split → ✅ CUD's own first principle is redundant coding —
  label the slices, or vary shape, position or pattern as well
- ❌ Choosing the two adjacent warm hues for the two things that must not be confused → ✅ warm/cool
  alternate in the ramp for this reason; a pair two apart is safer than a pair side by side
- ❌ Using the lighter members (sky blue, yellow) for thin lines or small text → ✅ they are
  declared fill-only; the CUD guidance prescribes the darker blue and orange for thin marks

## Alternatives

| Variant | Use instead |
|---|---|
| The same mix where colour is not critical | `support-ticket-mix-pie.md` |
| A chart for print and photocopies instead | `print-handout-graph.md` |
| A chart for a projected, glance-at-it audience | `vivid-launch-share.md` |

<!-- source: theme showcase — Accessible theme (Okabe–Ito CUD), infographic theme block -->
