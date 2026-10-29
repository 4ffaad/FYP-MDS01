# Percent of Total — Normalized Composition (Vega-Lite)

**Best for**: comparing composition across periods when every period should sum to the same baseline and the reader cares about share, not absolute total
**Avoid when**: the total size per period is itself important or the categories are too many to stack legibly
**Answers**: how each category’s share changes, and which component dominates within each period

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 460,
  "height": 260,
  "title": {"text": "Normalized Share by Quarter", "subtitle": "Category mix expressed as percent of total", "anchor": "start"},
  "data": {
    "values": [
      {"quarter": "Q1", "group": "Platform", "value": 42},
      {"quarter": "Q1", "group": "Security", "value": 18},
      {"quarter": "Q1", "group": "Data", "value": 12},
      {"quarter": "Q2", "group": "Platform", "value": 46},
      {"quarter": "Q2", "group": "Security", "value": 20},
      {"quarter": "Q2", "group": "Data", "value": 14},
      {"quarter": "Q3", "group": "Platform", "value": 44},
      {"quarter": "Q3", "group": "Security", "value": 24},
      {"quarter": "Q3", "group": "Data", "value": 16},
      {"quarter": "Q4", "group": "Platform", "value": 48},
      {"quarter": "Q4", "group": "Security", "value": 22},
      {"quarter": "Q4", "group": "Data", "value": 18}
    ]
  },
  "mark": "bar",
  "encoding": {
    "x": {"field": "quarter", "type": "nominal", "title": null},
    "y": {"field": "value", "type": "quantitative", "stack": "normalize", "axis": {"format": ".0%"}, "title": "Share of total"},
    "color": {"field": "group", "type": "nominal"}
  }
}
```

## Data Shape

One row per period/category combination. Vega-Lite normalizes the stack so every bar becomes a 100% share view.

## Key Options

| Option | Effect |
|---|---|
| `stack: "normalize"` | Converts absolute values into percent-of-total composition |
| Percent-formatted axis | Makes the normalized semantics explicit |
| Stacked color encoding | Keeps category membership readable within each period |
| Shared nominal period axis | Supports side-by-side composition comparison |

## Pitfalls

- ❌ Using a normalized stack when absolute totals matter → ✅ it hides total growth and shrinkage by design
- ❌ Too many stacked categories → ✅ small slices become unreadable quickly
- ❌ Forgetting percent axis formatting → ✅ the reader needs to know the bars sum to 100% |

## Alternatives

| Variant | Use instead |
|---|---|
| Absolute composition | `comparison-bars.md` or a non-normalized stacked bar |
| Few categories at one point in time | `product-mix-donut-badges.md` or `pie-budget-share.md` |
| Advanced top-k or long-tail share | `revenue-concentration-topk-others.md` |

<!-- source: Vega-Lite docs (stack normalize) + examples gallery percent-of-total -->