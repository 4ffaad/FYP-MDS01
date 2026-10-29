# Word Cloud — Topic Emphasis (Infographic)

**Best for**: a small thematic vocabulary where prominence and visual emphasis matter more than exact ranking
**Avoid when**: the audience needs precise numeric comparison or a very large, noisy vocabulary
**Answers**: which terms dominate attention, and which supporting terms still appear in the landscape

```infographic
infographic chart-wordcloud
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
  title Topic Emphasis
  desc The main themes appearing in recent platform review notes
  values
    - label Reliability
      value 86
    - label Automation
      value 72
    - label Security
      value 64
    - label Latency
      value 58
    - label Identity
      value 55
    - label Queue
      value 43
```

## Data Shape

Use `values` with one label and one weight per term. Keep the vocabulary deliberately small and curated.

## Key Options

| Option | Effect |
|---|---|
| `chart-wordcloud` | Converts weighted terms into a prominence view |
| `value` | Drives the relative emphasis or size of each term |
| Curated term list | Prevents the output from devolving into decorative clutter |

## Pitfalls

- ❌ Treating a word cloud as an exact ranking chart → ✅ it is about emphasis and landscape, not precise order
- ❌ Too many near-equal terms → ✅ the result becomes muddy and generic |
- ❌ Using raw noisy text without curation → ✅ control the vocabulary before the card is generated |

## Alternatives

| Variant | Use instead |
|---|---|
| Exact ranking of terms | A sorted Vega/Vega-Lite bar chart |
| Relationship between concepts | `capability-relationship-map.md` |
| Editorial narrative summary | `research-abstract-card.md` |

<!-- source: AntV Infographic template reference (`chart-wordcloud`) + syntax docs for values -->