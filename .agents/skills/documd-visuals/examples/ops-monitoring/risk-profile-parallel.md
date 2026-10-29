# Parallel Coordinates — Service Risk Profiles (Vega)

**Best for**: scanning several measures at once to find the *one* service that is an outlier on some axis
**Avoid when**: fewer than three measures, or the audience needs a summary rather than an inspection
**Answers**: which service is atypical, and on which dimension it breaks the pattern

```vega
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "width": 520,
  "height": 280,
  "padding": 10,
  "title": {"text": "Service Risk Profiles", "subtitle": "Five normalised axes — one line per service, crossing where rankings disagree", "anchor": "start"},
  "data": [
    {
      "name": "axes",
      "values": [
        {"axis": "latency", "label": "p95 latency", "range": "400–900 ms"},
        {"axis": "error", "label": "Error rate", "range": "0–4 %"},
        {"axis": "deploy", "label": "Deploys / week", "range": "0–20"},
        {"axis": "coverage", "label": "Test coverage", "range": "60–95 %"},
        {"axis": "failure", "label": "Change failure", "range": "0–25 %"}
      ]
    },
    {
      "name": "services",
      "values": [
        {"service": "checkout", "latency": 0.82, "error": 0.61, "deploy": 0.35, "coverage": 0.42, "failure": 0.71},
        {"service": "search", "latency": 0.44, "error": 0.22, "deploy": 0.72, "coverage": 0.81, "failure": 0.28},
        {"service": "catalog", "latency": 0.21, "error": 0.12, "deploy": 0.88, "coverage": 0.74, "failure": 0.15},
        {"service": "profile", "latency": 0.12, "error": 0.35, "deploy": 0.55, "coverage": 0.62, "failure": 0.44}
      ]
    },
    {
      "name": "folded",
      "source": "services",
      "transform": [
        {"type": "fold", "fields": ["latency", "error", "deploy", "coverage", "failure"], "as": ["axis", "score"]}
      ]
    }
  ],
  "scales": [
    {"name": "x", "type": "point", "range": "width", "padding": 0.5, "domain": {"data": "axes", "field": "axis"}},
    {"name": "y", "type": "linear", "range": "height", "domain": [0, 1], "nice": false},
    {"name": "color", "type": "ordinal", "domain": {"data": "services", "field": "service"}, "range": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"]}
  ],
  "axes": [
    {"orient": "bottom", "scale": "x", "title": null, "labels": false, "ticks": false},
    {"orient": "left", "scale": "y", "title": "normalised score (0 = best)", "grid": true, "tickCount": 5}
  ],
  "legends": [
    {"stroke": "color", "symbolType": "stroke", "title": "Service", "orient": "right"}
  ],
  "marks": [
    {
      "type": "rule",
      "from": {"data": "axes"},
      "interactive": false,
      "encode": {
        "update": {
          "x": {"scale": "x", "field": "axis"},
          "y": {"value": 0},
          "y2": {"signal": "height"},
          "stroke": {"value": "#6b7280"},
          "strokeWidth": {"value": 1.5}
        }
      }
    },
    {
      "type": "text",
      "from": {"data": "axes"},
      "interactive": false,
      "encode": {
        "update": {
          "x": {"scale": "x", "field": "axis"},
          "y": {"value": -22},
          "text": {"field": "label"},
          "fontSize": {"value": 10},
          "align": {"value": "center"}
        }
      }
    },
    {
      "type": "text",
      "from": {"data": "axes"},
      "interactive": false,
      "encode": {
        "update": {
          "x": {"scale": "x", "field": "axis"},
          "y": {"value": -9},
          "text": {"field": "range"},
          "fontSize": {"value": 9},
          "fill": {"value": "#2b66c4"},
          "align": {"value": "center"}
        }
      }
    },
    {
      "type": "group",
      "from": {"facet": {"name": "series", "data": "folded", "groupby": "service"}},
      "marks": [
        {
          "type": "line",
          "from": {"data": "series"},
          "encode": {
            "update": {
              "x": {"scale": "x", "field": "axis"},
              "y": {"scale": "y", "field": "score"},
              "stroke": {"scale": "color", "field": "service"},
              "strokeWidth": {"value": 2.4},
              "strokeOpacity": {"value": 0.85}
            }
          }
        }
      ]
    }
  ]
}


```

## Data Shape

The trick is **folded wide data**:

| Dataset | Contents |
|---|---|
| `axes` | One row per axis: the **key** the folded data uses, its display label, and a human-readable range |
| `services` | One row per entity, with one **already normalised** column per axis — the column names are the `axes` keys |
| `folded` | `fold` turns each service row into one row per axis (`axis`, `score`) |

The `axis` key is what the x scale's domain and the folded data must agree on; the label is only ever
painted by a text mark. Fold emits the *column names*, so a label like `p95 latency` in the domain and a
column named `latency` in the data put every line at x = 0 — the failure looks like an empty plot, not an
error.

Normalise upstream: parallel coordinates compare shapes, so every axis is scaled to 0–1 before it reaches the spec.

## Key Options

| Option | Effect |
|---|---|
| `fold` transform | Turns wide entity rows into long rows — the shape parallel coordinates need. It emits the **column names**, so the axis keys, the folded field list and the x domain must be the same five strings |
| `point` scale on the axis names | Evenly spaces the vertical axes, with `padding` keeping the outermost clear of the edges |
| `y` domain fixed to `[0, 1]` | Every axis shares one normalised scale; this is what makes crossing lines meaningful |
| `group` + `facet` with `groupby` | One `<line>` per service, drawn from a single folded dataset |
| `axes` rules | Draws the vertical guide rails independently of the data |
| `labels: false` + `ticks: false` on the bottom axis | The axis names are painted by the text marks instead, so the axis itself stays bare — without this every name appears twice, once as the display label and once as the raw key |
| Range labels as text marks | A real parallel-coordinates axis has per-axis ticks — one range label per axis is the honest minimum |

## Pitfalls

- ❌ Mixing raw units on one y scale → ✅ a parallel-coordinates plot only works on normalised axes; state the original ranges (hence the range labels)
- ❌ Unstated normalisation direction → ✅ readers cannot tell if high is good; label the axis ("0 = best") or flip the data
- ❌ Axis keys that do not match the folded column names → ✅ `fold` emits column names, so a display label in the x domain silently puts every line at x = 0
- ❌ Letting the bottom axis label itself while text marks repeat the names above → ✅ turn its `labels` off; the domain values are the keys, not what the reader should read
- ❌ Too many lines → ✅ past ~15 series the plot becomes a mesh; highlight two or three and grey the rest
- ❌ Reading a crossing as a change over time → ✅ each axis is a different measure; crossings mean the ranking differs between measures

## Alternatives

| Variant | Use instead |
|---|---|
| Every measure shown on its own axis | `radar-capability-profile.md` (ECharts) |
| One measure against a normalised baseline | `deviation-from-average.md` |
| Pairwise measure relationships | `metric-correlation-matrix.md` |

<!-- source: Vega docs (fold transform, facet groups, point and linear scales, rule marks) + the parallel-coordinates gallery example -->
