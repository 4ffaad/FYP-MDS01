# Rank Change — Category Position Over Time (Vega-Lite)

**Best for**: showing how the relative ranking of categories changes across ordered periods when the position matters more than the raw measure
**Avoid when**: the reader needs exact numeric magnitude or there are too many categories for a legible rank plot
**Answers**: who moved up, who fell back, and whether leadership is stable or volatile across time

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 500,
  "height": 260,
  "title": {"text": "Rank Change Over Time", "subtitle": "Quarterly leader-board movement by category", "anchor": "start"},
  "data": {
    "values": [
      {"quarter": "Q1", "group": "Platform", "value": 42},
      {"quarter": "Q1", "group": "Security", "value": 18},
      {"quarter": "Q1", "group": "Data", "value": 12},
      {"quarter": "Q2", "group": "Platform", "value": 39},
      {"quarter": "Q2", "group": "Security", "value": 25},
      {"quarter": "Q2", "group": "Data", "value": 16},
      {"quarter": "Q3", "group": "Platform", "value": 34},
      {"quarter": "Q3", "group": "Security", "value": 36},
      {"quarter": "Q3", "group": "Data", "value": 21},
      {"quarter": "Q4", "group": "Platform", "value": 31},
      {"quarter": "Q4", "group": "Security", "value": 38},
      {"quarter": "Q4", "group": "Data", "value": 33}
    ]
  },
  "transform": [
    {"window": [{"op": "rank", "as": "rank"}], "sort": [{"field": "value", "order": "descending"}], "groupby": ["quarter"]}
  ],
  "mark": {"type": "line", "point": true, "strokeWidth": 2.5},
  "encoding": {
    "x": {"field": "quarter", "type": "ordinal", "title": null},
    "y": {"field": "rank", "type": "ordinal", "sort": "ascending", "title": "Rank"},
    "color": {"field": "group", "type": "nominal"}
  }
}
```

## Data Shape

One row per period/category pair with a measure to rank. The transform computes rank within each period before drawing the lines. ⚠️ **Check that the order actually changes**: if one category leads in every period the ranks are constant, every line is flat, and the figure says nothing — it has become a value trend drawn the hard way.

## Key Options

| Option | Effect |
|---|---|
| `window` rank grouped by period | Computes ordinal position from raw values inside the spec |
| Ordinal y rank scale | Turns the chart into a ranking movement view |
| Line with points | Makes both path and discrete rank positions readable |
| Shared period axis | Preserves the ordered sequence of rank changes |

## Pitfalls

- ❌ Flat lines → ✅ they mean the ranking never changed; either find the periods where it did, or use `trend-line-multi-series.md`
- ❌ Reading bump charts as magnitude charts → ✅ they show position change, not raw value distance
- ❌ Too many categories → ✅ crossed lines quickly become unreadable
- ❌ Forgetting per-period group ranking → ✅ global rank is not the same as rank within each period |

## Alternatives

| Variant | Use instead |
|---|---|
| Exact value trend | `trend-line-multi-series.md` |
| Top-k concentration | `revenue-concentration-topk-others.md` |
| Normalized share comparison | `quarterly-share-normalized-stack.md` |

<!-- source: Vega-Lite docs (window rank / line) + examples gallery bump/rank change patterns -->