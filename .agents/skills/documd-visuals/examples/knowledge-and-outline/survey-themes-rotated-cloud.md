# Survey Themes Rotated Cloud — What Respondents Kept Saying (Infographic)

**Best for**: opening a research readout with the themes that dominated free-text answers
**Avoid when**: exact counts matter (use a ranked bar chart)
**Answers**: which themes appear most often in open-ended survey responses

```infographic
infographic chart-wordcloud-rotate
theme
  colorPrimary #2b66c4
  palette
    - #2b66c4
    - #2f9e44
    - #f3a33c
    - #d1242f
    - #7048e8
    - #0f9b9b
    - #c16f8a
    - #7c5a3d
data
  title Open Feedback Themes — NPS Follow-Up
  desc Size reflects mention frequency
  values
    - label onboarding
      value 92
    - label latency
      value 74
    - label pricing
      value 63
    - label search
      value 51
    - label exports
      value 33
    - label mobile
      value 28
    - label permissions
      value 21
    - label reporting
      value 17
```

## Data Shape

`values` where the number is the mention count. The rotated variant mixes angles, which reads as "raw
feedback" — helpful when the audience should not over-read precise ranks.

## Key Options

| Option | Effect |
|---|---|
| `infographic chart-wordcloud-rotate` | Mixed angles; energetic, less precise |
| `chart-wordcloud` | Horizontal words only — easier to read on mobile |
| `chart-bar-plain-text` | Use when the ranking must be exact |

## Pitfalls

- ❌ Weighting by sentiment → ✅ mention counts only; sentiment needs a different encoding
- ❌ Single words that mean nothing out of context → ✅ short phrases beat isolated nouns
- ❌ Thirty terms → ✅ eight to fifteen terms keep the cloud legible at 900×600

## Alternatives

| Variant | Use instead |
|---|---|
| Curated topic emphasis | `topic-emphasis-wordcloud.md` |
| Theme ranking with volumes | `team-throughput-bars.md` |
| Themes by customer segment | `segment-pattern-small-multiples.md` (vega-lite) |

<!-- source: AntV Infographic syntax docs + template list (`chart-wordcloud-rotate`) -->
