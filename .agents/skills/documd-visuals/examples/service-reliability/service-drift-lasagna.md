# Lasagna Plot — Service Drift Against Its Own Baseline (Vega-Lite)

**Best for**: spotting which service had an unusual week, when each service has a different normal
**Avoid when**: all rows share one scale and one meaning (a plain heatmap is simpler)
**Answers**: which service-weeks stand out from that service's own average

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 400,
  "height": 200,
  "title": {"text": "Latency Drift by Service", "subtitle": "Deviation from each service's own 6-week mean (ms)", "anchor": "start"},
  "data": {
    "values": [
      {"service": "checkout", "week": "W1", "p95": 410}, {"service": "checkout", "week": "W2", "p95": 398},
      {"service": "checkout", "week": "W3", "p95": 432}, {"service": "checkout", "week": "W4", "p95": 266},
      {"service": "checkout", "week": "W5", "p95": 251}, {"service": "checkout", "week": "W6", "p95": 244},
      {"service": "cart", "week": "W1", "p95": 362}, {"service": "cart", "week": "W2", "p95": 344},
      {"service": "cart", "week": "W3", "p95": 371}, {"service": "cart", "week": "W4", "p95": 352},
      {"service": "cart", "week": "W5", "p95": 338}, {"service": "cart", "week": "W6", "p95": 331},
      {"service": "search", "week": "W1", "p95": 302}, {"service": "search", "week": "W2", "p95": 318},
      {"service": "search", "week": "W3", "p95": 289}, {"service": "search", "week": "W4", "p95": 296},
      {"service": "search", "week": "W5", "p95": 274}, {"service": "search", "week": "W6", "p95": 268},
      {"service": "catalog", "week": "W1", "p95": 246}, {"service": "catalog", "week": "W2", "p95": 238},
      {"service": "catalog", "week": "W3", "p95": 251}, {"service": "catalog", "week": "W4", "p95": 229},
      {"service": "catalog", "week": "W5", "p95": 214}, {"service": "catalog", "week": "W6", "p95": 208},
      {"service": "profile", "week": "W1", "p95": 191}, {"service": "profile", "week": "W2", "p95": 186},
      {"service": "profile", "week": "W3", "p95": 204}, {"service": "profile", "week": "W4", "p95": 178},
      {"service": "profile", "week": "W5", "p95": 172}, {"service": "profile", "week": "W6", "p95": 169}
    ]
  },
  "transform": [
    {"joinaggregate": [{"op": "mean", "field": "p95", "as": "rowMean"}], "groupby": ["service"]},
    {"calculate": "datum.p95 - datum.rowMean", "as": "drift"}
  ],
  "mark": {"type": "rect", "stroke": null},
  "encoding": {
    "y": {"field": "service", "type": "ordinal", "title": null},
    "x": {"field": "week", "type": "ordinal", "title": null, "sort": ["W1", "W2", "W3", "W4", "W5", "W6"]},
    "color": {
      "field": "drift",
      "type": "quantitative",
      "scale": {"scheme": "redblue", "reverse": true, "domain": [-40, 40]},
      "legend": {"title": "ms vs own mean"}
    }
  }
}
```

## Data Shape

A complete rectangular grid — every service × week — plus a per-row baseline computed in a transform:

| Transform | Output |
|---|---|
| `joinaggregate` with `op: "mean"` grouped by `service` | `rowMean`, attached to every row of that service |
| `calculate` `p95 - rowMean` | `drift`, the value that is actually coloured |

## Key Options

| Option | Effect |
|---|---|
| `joinaggregate` + `groupby` | Per-row baselines without a separate data table |
| Diverging scheme with a **symmetric domain** | `[-40, 40]` keeps zero at the neutral colour; an auto domain would put the midpoint off-centre |
| `reverse: true` on the scheme | Cool for faster-than-usual, warm for slower — match the direction to the reading you want |
| Ordinal `sort` on the week axis | The renderer disables automatic sorting, so the week order must be given |
| `mark.stroke: null` | Cells should touch; borders would double-encode the grid |

## Pitfalls

- ❌ Colouring raw values in a lasagna → ✅ services with different baselines would just show their rank; the deviation is the whole point
- ❌ An auto-scaled diverging domain → ✅ it rarely straddles zero symmetrically, so "neutral" drifts away from the middle colour
- ❌ Missing cells in the grid → ✅ a lasagna must be complete; a missing week silently disappears
- ❌ More than ~15 rows → ✅ the plot becomes a wall; keep it to the services you will discuss

## Alternatives

| Variant | Use instead |
|---|---|
| Absolute values on one shared scale | `metric-correlation-matrix.md` |
| Weekday rhythm rather than week-over-week drift | `deploy-frequency-calendar.md` |
| One service's trend in detail | `threshold-breach-annotation.md` |

<!-- source: Vega-Lite docs (joinaggregate and calculate transforms, rect marks, quantitative colour scales) + the lasagna-plot entry in the table-based gallery section -->
