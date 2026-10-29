# Candlestick — Price Range by Trading Day (ECharts)

**Best for**: open-high-low-close ranges where the spread and intra-period movement both matter
**Avoid when**: the reader only needs one trend line or the data is not an OHLC interval series
**Answers**: whether each period closed up or down, how volatile the session was, and where ranges widened

```echarts
{
  "color": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"],
  "width": 860,
  "height": 420,
  "title": { "text": "Price Range by Trading Day", "subtext": "Illustrative OHLC sample", "left": "left" },
  "grid": { "left": 64, "right": 32, "top": 92, "bottom": 42 },
  "xAxis": {
    "type": "category",
    "data": ["Mon", "Tue", "Wed", "Thu", "Fri", "Mon+1", "Tue+1", "Wed+1"],
    "boundaryGap": true
  },
  "yAxis": {
    "type": "value",
    "scale": true,
    "name": "$",
    "nameLocation": "end",
    "nameGap": 10
  },
  "series": [
    {
      "type": "candlestick",
      "itemStyle": {
        "color": "#2b66c4",
        "color0": "#c16f8a",
        "borderColor": "#7048e8",
        "borderColor0": "#c16f8a"
      },
      "data": [
        [102, 108, 112, 98],
        [108, 105, 111, 103],
        [105, 118, 121, 104],
        [118, 116, 122, 113],
        [116, 124, 128, 115],
        [124, 120, 126, 118],
        [120, 129, 132, 119],
        [129, 133, 136, 127]
      ]
    }
  ]
}
```

## Key Options

| Option | Effect |
|---|---|
| `series.type: "candlestick"` | Encodes open, close, low, and high in one mark |
| `data: [open, close, low, high]` | The required OHLC order for each category |
| `yAxis.scale: true` | Stops the value axis from forcing zero, which would flatten the ranges |
| `itemStyle.color` / `color0` | Distinguishes rising vs falling sessions in export |
| `grid` | Candlestick charts need room for thicker marks and readable range axes |

## Data Shape

One categorical `xAxis.data` array and one matching OHLC tuple per category. Each tuple is `[open, close, low, high]`.

## Pitfalls

- ❌ Using candlesticks for non-interval measures → ✅ this chart is specifically for OHLC-style ranges
- ❌ Forcing the y-axis to start at zero → ✅ price-range views usually need `scale: true`
- ❌ Omitting high/low extremes → ✅ if the spread matters, a simple line chart hides too much information
- ❌ Comparing too many periods in a narrow frame → ✅ reduce the time window or move to weekly aggregates

## Alternatives

| Variant | Use instead |
|---|---|
| One closing-price trend only | `trend-line-multi-series.md` |
| Distribution of ranges | `boxplot-latency-distribution.md` |
| Ranked comparisons across categories | `comparison-bars.md` |

<!-- source: ECharts option manual (series-candlestick) + examples gallery candlestick family -->