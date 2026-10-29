# Word Cloud — Topic Landscape (Vega)

**Best for**: visually emphasizing a small controlled vocabulary where prominence matters more than exact numeric comparison
**Avoid when**: the reader needs precise ranking, detailed axes, or many close-value terms
**Answers**: which topics dominate the discussion, and which terms are secondary but still present

```vega
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "width": 480,
  "height": 280,
  "padding": 8,
  "title": {"text": "Topic Landscape", "subtitle": "Terms extracted from platform review notes", "anchor": "start", "color": "#1f2937", "subtitleColor": "#2b66c4"},
  "data": [
    {
      "name": "table",
      "values": [
        {"word": "Reliability", "count": 86},
        {"word": "Identity", "count": 68},
        {"word": "Automation", "count": 74},
        {"word": "Latency", "count": 57},
        {"word": "Security", "count": 64},
        {"word": "Queue", "count": 49},
        {"word": "Observability", "count": 53},
        {"word": "Policy", "count": 42}
      ],
      "transform": [
        {"type": "wordcloud", "size": [480, 280], "text": {"field": "word"}, "fontSize": {"field": "count"}, "fontSizeRange": [16, 54], "padding": 2}
      ]
    }
  ],
  "scales": [
    {"name": "color", "type": "ordinal", "domain": {"data": "table", "field": "word"}, "range": ["#2b66c4", "#2f9e44", "#f3a33c", "#d1242f", "#7048e8", "#0f9b9b", "#c16f8a", "#7c5a3d"]}
  ],
  "marks": [
    {
      "type": "text",
      "from": {"data": "table"},
      "encode": {
        "enter": {
          "text": {"field": "word"},
          "x": {"field": "x"},
          "y": {"field": "y"},
          "angle": {"field": "angle"},
          "fontSize": {"field": "fontSize"},
          "fill": {"scale": "color", "field": "word"},
          "align": {"value": "center"}
        }
      }
    }
  ]
}


```

## Data Shape

One row per term with a numeric weight. The Vega `wordcloud` transform computes the placement and font size.

## Key Options

| Option | Effect |
|---|---|
| Vega `wordcloud` transform | Generates the placement, rotation, and font-size layout |
| `fontSizeRange` | Keeps large terms prominent without completely dwarfing the rest |
| Ordinal color scale | Adds variety while preserving a controlled palette |
| Direct text mark | Draws the positioned words computed by the transform |

## Pitfalls

- ❌ Using a word cloud for exact ranking → ✅ it is a prominence view, not a precise comparison chart
- ❌ Too many near-equal terms → ✅ the result becomes decorative rather than informative
- ❌ Expecting every term to fit without tuning → ✅ word clouds require a controlled vocabulary and bounded size range

## Alternatives

| Variant | Use instead |
|---|---|
| Exact topic ranking | A sorted bar chart |
| Relationship map between concepts | `service-dependency-network.md` |
| Qualitative executive summary | `executive-brief-summary.md` |

<!-- source: Vega docs (wordcloud transform) + repo vega examples reference word cloud pattern -->