# Bar Chart — Team Throughput Snapshot (Infographic)

**Best for**: a small category comparison where a simple template-first bar treatment is enough
**Avoid when**: the reader needs strong analytical axis control, many categories, or multiple numerical encodings
**Answers**: which team is highest or lowest, and roughly how the groups compare

```infographic
infographic chart-bar-plain-text
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
  title Team Throughput
  desc Weekly completed work items by team
  values
    - label Core
      value 84
    - label Billing
      value 73
    - label Identity
      value 61
    - label Search
      value 88
```

## Data Shape

Use `values` with one numeric measure per category. Keep category count small and labels short.

## Key Options

| Option | Effect |
|---|---|
| `chart-bar-plain-text` | Lightweight horizontal comparison treatment |
| `values` | Numeric rows for infographic chart templates |
| Plain text labels | Keeps the chart direct and compact |

## Pitfalls

- ❌ Treating this like a full analytics chart → ✅ infographic bars are presentation-first, not analysis-first
- ❌ Too many categories → ✅ the template loses clarity once the list becomes long |
- ❌ Multiple stacked/grouped measures → ✅ use echarts or vega-lite for richer chart semantics |

## Alternatives

| Variant | Use instead |
|---|---|
| Simple vertical period comparison | `quarterly-results-columns.md` |
| Exact analytical bar chart | `comparison-bars.md` or Vega bar specs |
| KPI card board | `leadership-metric-board.md` |

<!-- source: AntV Infographic template reference (`chart-bar-plain-text`) + syntax docs for values -->