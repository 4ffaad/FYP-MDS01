# Swarm Plot — Latency Spread by Region (Vega-Lite)

**Best for**: a small sample where every observation should stay visible, without overlapping dots
**Avoid when**: there are hundreds of points, or the distribution shape matters more than the individual values
**Answers**: how tight or wide each region's latency cluster is, and where the stragglers sit

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 460,
  "height": 220,
  "title": {"text": "Checkout Latency by Region", "subtitle": "Eight sampled requests per region, offset in five deterministic lanes", "anchor": "start"},
  "data": {
    "values": [
      {"region": "us-east", "p95": 268}, {"region": "us-east", "p95": 291},
      {"region": "us-east", "p95": 305}, {"region": "us-east", "p95": 318},
      {"region": "us-east", "p95": 332}, {"region": "us-east", "p95": 349},
      {"region": "us-east", "p95": 361}, {"region": "us-east", "p95": 402},
      {"region": "eu-west", "p95": 244}, {"region": "eu-west", "p95": 252},
      {"region": "eu-west", "p95": 266}, {"region": "eu-west", "p95": 279},
      {"region": "eu-west", "p95": 288}, {"region": "eu-west", "p95": 301},
      {"region": "eu-west", "p95": 315}, {"region": "eu-west", "p95": 338},
      {"region": "ap-south", "p95": 312}, {"region": "ap-south", "p95": 330},
      {"region": "ap-south", "p95": 356}, {"region": "ap-south", "p95": 378},
      {"region": "ap-south", "p95": 395}, {"region": "ap-south", "p95": 421},
      {"region": "ap-south", "p95": 448}, {"region": "ap-south", "p95": 502}
    ]
  },
  "transform": [
    {"window": [{"op": "rank", "as": "idx"}], "groupby": ["region"]},
    {"calculate": "((datum.idx - 1) % 5) - 2", "as": "lane"}
  ],
  "mark": {"type": "point", "filled": true, "size": 65, "opacity": 0.85},
  "encoding": {
    "x": {"field": "p95", "type": "quantitative", "title": "p95 latency (ms)"},
    "y": {"field": "region", "type": "ordinal", "title": null},
    "yOffset": {
      "field": "lane",
      "type": "quantitative",
      "scale": {"domain": [-2, 2], "range": [-15, 15]}
    },
    "color": {"field": "region", "type": "nominal", "legend": null}
  }
}
```

## Data Shape

One row per observation plus two derived fields:

| Transform | Output |
|---|---|
| `window` with `op: "rank"` grouped by `region` | `idx` — a stable position within each row |
| `calculate ((idx - 1) % 5) - 2` | `lane` — the values −2 … +2 that spread the dots |

## Key Options

| Option | Effect |
|---|---|
| `yOffset` with a **fixed** domain and range | Deterministic jitter: identical input gives an identical picture, unlike a random offset |
| `window..op.rank` | Provides the per-row ordering the lane formula needs; `rank` is stable for equal values |
| `scale.range: [-15, 15]` | The vertical spread in pixels — widen it until dots stop touching, not further |
| `size: 65` + `opacity: 0.85` | Small translucent discs, so accidental overlap is still readable |
| `color.legend: null` | The y-axis labels already name the groups |

## Pitfalls

- ❌ Random jitter → ✅ the same data would render differently on every build, which breaks diffing and screenshots; the rank-based lane is reproducible
- ❌ Lanes narrower than the marker → ✅ dots merge back into a line; set the range from the marker size
- ❌ A row with 40+ observations → ✅ switch to a density curve (`service-latency-density.md`) or a box plot
- ❌ Reading the lane position as data → ✅ the offset is only there to stop overlap; say so when the chart is presented

## Alternatives

| Variant | Use instead |
|---|---|
| Distribution shape, many samples | `service-latency-density.md` |
| Summary statistics per group | `release-duration-distribution.md` (box plot) |
| Spread as a strip of ticks | `stripplot-region-spread.md` |

<!-- source: Vega-Lite docs (window rank transform, yOffset channel with a quantitative scale, point marks) + the beeswarm entry in the distribution gallery section -->
