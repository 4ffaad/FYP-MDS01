# Editable architecture diagrams

Open the `.drawio` files in [diagrams.net](https://app.diagrams.net/) to edit
their nodes, labels, groups, and connectors. The adjacent JSON files are the
generator specifications used to create them. Keep cell IDs stable when
making incremental edits.

`system-architecture-preview.svg` is the 16:9 vector architecture view
embedded in the documentation; `system-architecture-preview.png` is a
1600 × 900 slide-ready image. After changing the architecture source, rebuild
and validate the `.drawio` file, then export an SVG at Page size from
diagrams.net and refresh the PNG from that SVG. Keep the presentation diagram
focused on the major components and workflows. The VEEG workflow source is kept
editable alongside its JSON specification.

From the repository root, validate and rebuild with:

```sh
python3 .agents/skills/drawio-mxgraph/scripts/drawio_tool.py validate docs/diagrams/system-architecture.drawio
python3 .agents/skills/drawio-mxgraph/scripts/drawio_tool.py validate docs/diagrams/veeg-review-flow.drawio
python3 .agents/skills/drawio-mxgraph/scripts/drawio_tool.py build --spec docs/diagrams/system-architecture.json --output docs/diagrams/system-architecture.drawio --offline
python3 .agents/skills/drawio-mxgraph/scripts/drawio_tool.py build --spec docs/diagrams/veeg-review-flow.json --output docs/diagrams/veeg-review-flow.drawio --offline
frontend/node_modules/.bin/playwright screenshot --browser chromium --viewport-size='1600,900' file://$(pwd)/docs/diagrams/system-architecture-preview.svg docs/diagrams/system-architecture-preview.png
```

The JSON specifications and editable Draw.io sources contain no patient data.
Review diagrams against `docs/project-design.md` after architecture changes.
