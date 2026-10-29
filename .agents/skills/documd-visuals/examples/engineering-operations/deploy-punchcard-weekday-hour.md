# Punch Card — Deploy Activity by Weekday and Hour (Vega-Lite)

**Best for**: a two-dimensional grid of counts where the pattern (not the exact value) is the message
**Avoid when**: the counts must be read exactly, or a cell can legitimately be blank
**Answers**: when deploys actually happen — the working-hours ridge and the quiet bands

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 470,
  "height": 190,
  "title": {"text": "Deploys by Weekday and Hour", "subtitle": "Last 12 weeks, four-hour buckets, marker area = deploy count", "anchor": "start"},
  "data": {
    "values": [
      {"d": "Mon", "h": "00", "count": 1}, {"d": "Mon", "h": "04", "count": 2}, {"d": "Mon", "h": "08", "count": 9},
      {"d": "Mon", "h": "12", "count": 11}, {"d": "Mon", "h": "16", "count": 7}, {"d": "Mon", "h": "20", "count": 2},
      {"d": "Tue", "h": "00", "count": 1}, {"d": "Tue", "h": "04", "count": 3}, {"d": "Tue", "h": "08", "count": 10},
      {"d": "Tue", "h": "12", "count": 12}, {"d": "Tue", "h": "16", "count": 8}, {"d": "Tue", "h": "20", "count": 2},
      {"d": "Wed", "h": "00", "count": 1}, {"d": "Wed", "h": "04", "count": 2}, {"d": "Wed", "h": "08", "count": 11},
      {"d": "Wed", "h": "12", "count": 13}, {"d": "Wed", "h": "16", "count": 9}, {"d": "Wed", "h": "20", "count": 3},
      {"d": "Thu", "h": "00", "count": 0}, {"d": "Thu", "h": "04", "count": 2}, {"d": "Thu", "h": "08", "count": 8},
      {"d": "Thu", "h": "12", "count": 10}, {"d": "Thu", "h": "16", "count": 7}, {"d": "Thu", "h": "20", "count": 2},
      {"d": "Fri", "h": "00", "count": 1}, {"d": "Fri", "h": "04", "count": 2}, {"d": "Fri", "h": "08", "count": 7},
      {"d": "Fri", "h": "12", "count": 8}, {"d": "Fri", "h": "16", "count": 5}, {"d": "Fri", "h": "20", "count": 1},
      {"d": "Sat", "h": "00", "count": 0}, {"d": "Sat", "h": "04", "count": 0}, {"d": "Sat", "h": "08", "count": 1},
      {"d": "Sat", "h": "12", "count": 2}, {"d": "Sat", "h": "16", "count": 1}, {"d": "Sat", "h": "20", "count": 0},
      {"d": "Sun", "h": "00", "count": 0}, {"d": "Sun", "h": "04", "count": 0}, {"d": "Sun", "h": "08", "count": 1},
      {"d": "Sun", "h": "12", "count": 1}, {"d": "Sun", "h": "16", "count": 1}, {"d": "Sun", "h": "20", "count": 0}
    ]
  },
  "mark": {"type": "point", "filled": true, "shape": "circle"},
  "encoding": {
    "x": {"field": "h", "type": "ordinal", "title": "hour bucket", "sort": ["00", "04", "08", "12", "16", "20"], "axis": {"labelAngle": 0}},
    "y": {"field": "d", "type": "ordinal", "title": null, "sort": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]},
    "size": {
      "field": "count",
      "type": "quantitative",
      "scale": {"range": [8, 420]},
      "legend": {"title": "deploys"}
    }
  }
}
```

## Data Shape

One row per grid cell: a weekday, an hour bucket and a count. Zero is a legitimate value — it renders as a
near-invisible dot, which is exactly the "quiet band" reading the chart is for.

| Field | Role |
|---|---|
| `d` / `h` | Ordinal positions; both need explicit `sort` because automatic sorting is disabled |
| `count` | Marker **area**, driven by a size scale with a fixed pixel range |

## Key Options

| Option | Effect |
|---|---|
| `scale.range: [8, 420]` | Pins marker area in pixels²; without it a single large value squashes the whole grid |
| `mark.shape: "circle"` | Discs read as bubbles; squares read as a grid of blocks — pick deliberately |
| `axes` at the edges only | The grid carries the reading; inner gridlines would compete with the markers |
| Explicit `sort` on both axes | Keeps weekdays in calendar order and hour buckets in clock order |
| `legend.title: "deploys"` | Area legends must be labelled, or readers guess whether the size is time or count |

## Pitfalls

- ❌ Area-encoding a value with a huge outlier → ✅ pin the range or switch to colour; one runaway cell hides every other difference
- ❌ Sizes that differ by less than ~30% → ✅ the eye cannot rank similar discs; use colour instead
- ❌ Blank cells where the count is zero → ✅ keep the row: a missing cell and a zero cell look the same, but only one is true
- ❌ Reading exact counts from the legend → ✅ area legends are approximate by design; label the values you will be quoted on

## Alternatives

| Variant | Use instead |
|---|---|
| A calendar-shaped grid over weeks | `deploy-frequency-calendar.md` |
| The same counts as a ranked bar chart | `comparison-bars.md` (ECharts) |
| Cyclic totals around a ring | `support-volume-radial-bars.md` (ECharts) |

<!-- source: Vega-Lite docs (point marks, size channel with an explicit scale range, ordinal sort) + the GitHub punch-card entry in the table-based gallery section -->
