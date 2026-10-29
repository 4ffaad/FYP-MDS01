# Regression Fit — Observed vs Estimated Trend (Vega-Lite)

**Best for**: showing a cloud of observations plus an estimated fitted relationship without leaving the spec grammar
**Avoid when**: the reader needs causal proof, or the sample is too small for a meaningful fit
**Answers**: whether the relationship is roughly linear, and how the fitted trend compares with the actual points

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 460,
  "height": 260,
  "title": {"text": "Observed vs Fitted Trend", "subtitle": "Scatter points with linear regression overlay", "anchor": "start"},
  "data": {"values": [
    {"load": 18, "latency": 108}, {"load": 22, "latency": 116}, {"load": 29, "latency": 129},
    {"load": 33, "latency": 138}, {"load": 39, "latency": 151}, {"load": 45, "latency": 168},
    {"load": 52, "latency": 182}, {"load": 58, "latency": 194}
  ]},
  "layer": [
    {
      "mark": {"type": "point", "filled": true, "size": 85, "color": "#2b66c4"},
      "encoding": {
        "x": {"field": "load", "type": "quantitative", "title": "System load"},
        "y": {"field": "latency", "type": "quantitative", "title": "Latency (ms)"}
      }
    },
    {
      "transform": [{"regression": "latency", "on": "load"}],
      "mark": {"type": "line", "strokeWidth": 2.5, "color": "#f3a33c"},
      "encoding": {
        "x": {"field": "load", "type": "quantitative"},
        "y": {"field": "latency", "type": "quantitative"}
      }
    }
  ]
}
```

## Data Shape

One row per observation with one independent variable and one dependent variable.

## Key Options

| Option | Effect |
|---|---|
| Point layer | Preserves the original observations |
| `regression` transform | Computes the fitted line inside the spec |
| Line overlay | Shows the estimated relationship without hiding the raw points |
| Shared quantitative axes | Keeps observation and fit on the same coordinate frame |

## Pitfalls

- ❌ Treating regression as proof of causation → ✅ the line shows fit, not mechanism
- ❌ Tiny or highly irregular samples → ✅ a fit line can overstate structure when the data is sparse
- ❌ Hiding the raw points | ✅ the fit means little without the actual observations |

## Alternatives

| Variant | Use instead |
|---|---|
| Segment-separated scatter panels | `segment-pattern-small-multiples.md` |
| Threshold breach on a time trend | `threshold-breach-annotation.md` |
| Distribution shape only | `request-size-distribution.md` |

<!-- source: Vega-Lite docs (regression transform) + examples gallery Scatter / regression -->