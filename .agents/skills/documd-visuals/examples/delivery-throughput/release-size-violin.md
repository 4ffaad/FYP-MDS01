# Violin Plot — Release Size Per Service (Vega)

**Best for**: comparing a distribution's *shape* across a few groups, not just its summary numbers
**Avoid when**: groups have fewer than ~15 observations, or only the median matters
**Answers**: whether one service ships much heavier releases, and how bimodal each service's releases are

```vega
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "width": 460,
  "height": 260,
  "padding": 6,
  "title": {"text": "Release Size by Service", "subtitle": "Kernel density per service, with the median as a bar", "anchor": "start"},
  "data": [
    {
      "name": "releases",
      "values": [
        {"service": "checkout", "mb": 420}, {"service": "checkout", "mb": 455},
        {"service": "checkout", "mb": 468}, {"service": "checkout", "mb": 502},
        {"service": "checkout", "mb": 530}, {"service": "checkout", "mb": 588},
        {"service": "checkout", "mb": 640}, {"service": "checkout", "mb": 720},
        {"service": "search", "mb": 310}, {"service": "search", "mb": 334},
        {"service": "search", "mb": 352}, {"service": "search", "mb": 366},
        {"service": "search", "mb": 388}, {"service": "search", "mb": 402},
        {"service": "search", "mb": 428}, {"service": "search", "mb": 470},
        {"service": "catalog", "mb": 240}, {"service": "catalog", "mb": 258},
        {"service": "catalog", "mb": 266}, {"service": "catalog", "mb": 281},
        {"service": "catalog", "mb": 295}, {"service": "catalog", "mb": 310},
        {"service": "catalog", "mb": 326}, {"service": "catalog", "mb": 352}
      ]
    },
    {
      "name": "density",
      "source": "releases",
      "transform": [
        {
          "type": "kde",
          "field": "mb",
          "groupby": ["service"],
          "bandwidth": 42,
          "extent": [200, 800]
        }
      ]
    },
    {
      "name": "stats",
      "source": "releases",
      "transform": [
        {
          "type": "aggregate",
          "groupby": ["service"],
          "fields": ["mb", "mb"],
          "ops": ["median", "q1"],
          "as": ["median", "q1"]
        }
      ]
    }
  ],
  "signals": [{"name": "plotWidth", "value": 46}],
  "scales": [
    {"name": "layout", "type": "band", "range": "height", "domain": {"data": "releases", "field": "service"}},
    {"name": "x", "type": "linear", "range": "width", "nice": true, "zero": false, "domain": {"data": "releases", "field": "mb"}},
    {"name": "hscale", "type": "linear", "range": [0, {"signal": "plotWidth"}], "domain": {"data": "density", "field": "density"}}
  ],
  "axes": [
    {"orient": "bottom", "scale": "x", "title": "release size (MB)", "grid": true},
    {"orient": "left", "scale": "layout", "tickCount": 3}
  ],
  "marks": [
    {
      "type": "group",
      "from": {"facet": {"name": "serviceFacet", "data": "density", "groupby": "service"}},
      "marks": [
        {
          "type": "area",
          "from": {"data": "serviceFacet"},
          "encode": {
            "update": {
              "x": {"scale": "x", "field": "value"},
              "yc": {"scale": "layout", "field": "service", "band": 0.5},
              "height": {"scale": "hscale", "field": "density"},
              "fill": {"value": "#2b66c4"},
              "fillOpacity": {"value": 0.45}
            }
          }
        }
      ]
    },
    {
      "type": "rect",
      "from": {"data": "stats"},
      "encode": {
        "update": {
          "x": {"scale": "x", "field": "q1"},
          "x2": {"scale": "x", "field": "median"},
          "yc": {"scale": "layout", "field": "service", "band": 0.5},
          "height": {"value": 3},
          "fill": {"value": "#7048e8"}
        }
      }
    },
    {
      "type": "symbol",
      "from": {"data": "releases"},
      "encode": {
        "update": {
          "x": {"scale": "x", "field": "mb"},
          "yc": {"scale": "layout", "field": "service", "band": 0.5},
          "size": {"value": 16},
          "fill": {"value": "#0f9b9b"},
          "fillOpacity": {"value": 0.55}
        }
      }
    }
  ]
}

```

## Data Shape

Three datasets from one source table:

| Dataset | Transform | Role |
|---|---|---|
| `releases` | — | The sample points, also drawn so the reader can judge the sample size |
| `density` | `kde` grouped by `service` | Emits `value` (position) and `density` (half-height of the violin) |
| `stats` | `aggregate` with `median` / `q1` | Draws the summary bar inside each violin |

## Key Options

| Option | Effect |
|---|---|
| `kde.groupby` | One density curve per group without writing a separate dataset for each |
| `kde.extent` | Pins the evaluation range so every violin is smoothed over the same span |
| `bandwidth: 42` | Smoothing: too small produces a spiky outline, too large flattens bimodality |
| `yc` + `height` on an `area` mark | Vega's way of drawing a horizontal ribbon: `height` is doubled around `yc` |
| `hscale` with domain from `density` | All violins share one width scale, so their widths remain comparable |
| Points overlaid | Makes the sample size visible; a smooth violin over four points is misleading |

## Pitfalls

- ❌ Violins for small samples → ✅ the kernel invents a smooth curve from very little data; show the points instead
- ❌ A separate width scale per group → ✅ each violin would look equally wide; the shared `hscale` is what preserves the comparison
- ❌ Reading the outline as a count → ✅ density is normalised per group, so height compares shape, not volume
- ❌ Very high bandwidth → ✅ two real peaks merge into one hump and the interesting structure disappears

## Alternatives

| Variant | Use instead |
|---|---|
| Box plot summary | `release-duration-distribution.md` |
| One distribution only | `service-latency-density.md` |
| Every point, no smoothing | `latency-beeswarm-regions.md` |

<!-- source: Vega docs (kde transform with groupby/extent, aggregate transform, area marks with yc+height) + the violin-plot gallery example -->
