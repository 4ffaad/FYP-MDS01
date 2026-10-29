# Schedule Bars — Release Window Phase Plan (Vega-Lite)

**Best for**: showing *when* each phase runs and how much the phases overlap
**Avoid when**: durations are the message rather than positions, or the phases are strictly sequential with equal length
**Answers**: what happens in parallel, where the freeze sits, and how long the tail watch runs

```vega-lite
{
  "config": { "range": { "category": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"] } },
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "width": 520,
  "height": 230,
  "title": {"text": "Release 24.10 Phase Plan", "subtitle": "Calendar windows, showing the overlap between phases", "anchor": "start"},
  "data": {
    "values": [
      {"phase": "Code freeze", "start": "2026-10-05", "end": "2026-10-09"},
      {"phase": "Staging soak", "start": "2026-10-09", "end": "2026-10-14"},
      {"phase": "Canary rollout", "start": "2026-10-14", "end": "2026-10-16"},
      {"phase": "Full rollout", "start": "2026-10-16", "end": "2026-10-21"},
      {"phase": "Post-release watch", "start": "2026-10-21", "end": "2026-10-28"}
    ]
  },
  "mark": {"type": "bar", "cornerRadius": 3, "height": 18},
  "encoding": {
    "y": {"field": "phase", "type": "ordinal", "title": null},
    "x": {"field": "start", "type": "temporal", "title": "release window", "axis": {"format": "%b %d", "labelAngle": 0}},
    "x2": {"field": "end"},
    "color": {"field": "phase", "type": "nominal", "legend": null}
  }
}
```

## Data Shape

Two temporal fields per row — `start` and `end` — bound to `x` and `x2`. Rows are listed in schedule order;
the y-axis follows that order because automatic sorting is disabled.

## Key Options

| Option | Effect |
|---|---|
| `x` + `x2` | Turns a bar into a span: both ends are positioned by data instead of by a category |
| `type: "temporal"` | Date strings parse to real time positions, so the axis can choose sensible ticks |
| `axis.format: "%b %d"` | Short date labels keep the axis from wrapping in a narrow view |
| `axis.labelAngle: 0` | Horizontal tick labels for a horizontal time axis |
| `cornerRadius: 3` + `height: 18` | Capsule-shaped phase bars — the standard look for schedule lanes |
| `color.legend: null` | One row per phase means the y labels already name the bars |

## Pitfalls

- ❌ Using a category axis for time → ✅ phases would then be evenly spaced regardless of their real duration
- ❌ Dates as non-ISO strings → ✅ `temporal` parsing expects an unambiguous format; always write `YYYY-MM-DD`
- ❌ Omitting `x2` → ✅ a bar with only `x` draws from the axis origin, which turns a schedule into a ranked bar chart
- ❌ More than ~12 lanes in one frame → ✅ split by stream or collapse the longest tail into "post-release watch"

## Alternatives

| Variant | Use instead |
|---|---|
| Ordered steps with no dates | `product-roadmap-sequence.md` (Infographic) |
| Milestones instead of phase windows | `platform-milestone-timeline.md` (Infographic) |
| Duration distribution across many releases | `release-duration-distribution.md` |

<!-- source: Vega-Lite docs (x2 channel, temporal scales, bar mark) + the Gantt-style entries in the community gallery -->
