# Line Chart — Adoption Trend Snapshot (Infographic)

**Best for**: a lightweight trend summary where the reader needs directionality more than dense analytical detail
**Avoid when**: the chart needs multiple series, benchmark overlays, or statistical transforms
**Answers**: whether the metric is rising, falling, or flattening over recent periods

```infographic
infographic chart-line-plain-text
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
  title Feature Adoption Trend
  desc Monthly active usage of the new checkout path
  values
    - label Jan
      value 18
    - label Feb
      value 26
    - label Mar
      value 39
    - label Apr
      value 51
```

## Data Shape

Use `values` with ordered labels that imply a simple temporal sequence.

## Key Options

| Option | Effect |
|---|---|
| `chart-line-plain-text` | Minimal line treatment for light trend storytelling |
| Ordered `values` labels | Gives the trend its sequence |
| One measure only | Keeps the infographic chart readable and lightweight |

## Pitfalls

- ❌ Multiple competing series in a simple infographic line template → ✅ move to Vega or ECharts for richer trend work
- ❌ Unordered labels | ✅ the chart assumes a natural reading sequence |
- ❌ Expecting detailed axis interpretation → ✅ this family is for lightweight trend communication |

## Alternatives

| Variant | Use instead |
|---|---|
| Analytical multi-series trend | `trend-line-multi-series.md` or Vega line specs |
| Milestone sequence | `platform-milestone-timeline.md` |
| KPI board | `metric-snapshot-board.md` |

<!-- source: AntV Infographic template reference (`chart-line-plain-text`) + syntax docs for values -->