# Density Contours — Where Alerts Cluster (Vega)

**Best for**: two-dimensional density where the shape of the cluster matters more than any single point
**Avoid when**: the number of points is small, or the reader needs per-point detail
**Answers**: how alert concentration moves across the day, and whether the morning peak is one cluster or two

```vega
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "width": 520,
  "height": 340,
  "padding": 8,
  "title": {"text": "Alert Density Across the Day", "subtitle": "Points are alert bursts; lines are 4 iso-density contours", "anchor": "start"},
  "data": [
    {
      "name": "alerts",
      "values": [
        {"hour": 9, "load": 12}, {"hour": 9.5, "load": 18}, {"hour": 10, "load": 26},
        {"hour": 10.5, "load": 31}, {"hour": 11, "load": 34}, {"hour": 11.5, "load": 29},
        {"hour": 12, "load": 22}, {"hour": 12.5, "load": 15}, {"hour": 10, "load": 20},
        {"hour": 10.8, "load": 24}, {"hour": 11.4, "load": 27}, {"hour": 9.8, "load": 14},
        {"hour": 12.2, "load": 18}, {"hour": 14, "load": 16}, {"hour": 14.5, "load": 21},
        {"hour": 15, "load": 25}, {"hour": 15.5, "load": 28}, {"hour": 16, "load": 23},
        {"hour": 16.5, "load": 17}, {"hour": 17, "load": 12}, {"hour": 15.2, "load": 19},
        {"hour": 14.8, "load": 14}, {"hour": 16.2, "load": 15}, {"hour": 20, "load": 8},
        {"hour": 20.5, "load": 11}, {"hour": 21, "load": 7}, {"hour": 3, "load": 4},
        {"hour": 3.5, "load": 6}
      ]
    },
    {
      "name": "density",
      "source": "alerts",
      "transform": [
        {
          "type": "kde2d",
          "size": [{"signal": "width"}, {"signal": "height"}],
          "x": {"expr": "scale('x', datum.hour)"},
          "y": {"expr": "scale('y', datum.load)"},
          "bandwidth": {"signal": "[30, 42]"},
          "cellSize": 4
        }
      ]
    },
    {
      "name": "contours",
      "source": "density",
      "transform": [
        {"type": "isocontour", "field": "grid", "levels": 4}
      ]
    }
  ],
  "scales": [
    {"name": "x", "type": "linear", "domain": {"data": "alerts", "field": "hour"}, "range": "width", "nice": true},
    {"name": "y", "type": "linear", "domain": {"data": "alerts", "field": "load"}, "range": "height", "nice": true}
  ],
  "axes": [
    {"orient": "bottom", "scale": "x", "title": "hour of day", "grid": true, "tickCount": 8},
    {"orient": "left", "scale": "y", "title": "alert bursts", "grid": true}
  ],
  "marks": [
    {
      "type": "symbol",
      "from": {"data": "alerts"},
      "encode": {
        "update": {
          "x": {"scale": "x", "field": "hour"},
          "y": {"scale": "y", "field": "load"},
          "size": {"value": 14},
          "fill": {"value": "#2b66c4"},
          "fillOpacity": {"value": 0.55}
        }
      }
    },
    {
      "type": "path",
      "from": {"data": "contours"},
      "clip": true,
      "interactive": false,
      "transform": [
        {"type": "geopath", "field": "datum.contour"}
      ],
      "encode": {
        "update": {
          "stroke": {"value": "#d1242f"},
          "strokeWidth": {"value": 1.4},
          "strokeOpacity": {"value": 0.9},
          "fill": {"value": "transparent"}
        }
      }
    }
  ]
}

```

## Data Shape

A plain point table plus two derived datasets:

| Dataset | Produced by | Contents |
|---|---|---|
| `density` | `kde2d` over **pixel** coordinates (`scale('x', …)`) | A `grid` field — a rasterised 2-D kernel estimate per cell |
| `contours` | `isocontour` on `grid` | One row per contour level, each with a `contour` polygon |

## Key Options

| Option | Effect |
|---|---|
| `x` / `y` as scale expressions | The kernel is computed in pixel space, which is what makes `size` and `bandwidth` comparable to the view |
| `bandwidth: [30, 42]` | Separate smoothing per axis — hours are the coarse dimension here, so it is smoothed less |
| `cellSize: 4` | Raster resolution: smaller is more precise but slower and heavier |
| `levels: 4` | Number of iso-lines; more lines show more structure but converge on a heatmap |
| `geopath` on `datum.contour` | Converts each contour polygon into a drawable path |
| `clip: true` + transparent fill | Keeps contours inside the plot and stops them from filling the whole canvas |

## Pitfalls

- ❌ Computing the density in data units while the scales differ → ✅ use scaled pixel coordinates, otherwise the kernel is elliptic in the wrong direction
- ❌ Contours without the underlying points → ✅ lines alone hide how thin the evidence is; points make the sample size visible
- ❌ Very low bandwidth → ✅ the estimate turns into a "confetti" of blobs around each observation
- ❌ Treating contour levels as confidence intervals → ✅ they are density thresholds, not probability bounds

## Alternatives

| Variant | Use instead |
|---|---|
| A gridded heatmap | `metric-correlation-matrix.md` |
| One-dimensional smoothing of a single measure | `service-latency-density.md` |
| Correlation of two measures without density | `scatter-segment-correlation.md` (ECharts) |

<!-- source: Vega docs (kde2d, isocontour and geopath transforms; heatmap raster) + the contour-plot gallery example -->
