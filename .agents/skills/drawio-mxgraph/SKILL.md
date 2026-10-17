---
name: drawio-mxgraph
description: Create, validate, and incrementally edit editable Draw.io/diagrams.net architecture diagrams, process diagrams, flowcharts, and mxGraph XML (.drawio), with built-in Draw.io library guidance and portable embedded icons from Iconify or local SVG/image files. Use when Codex needs to convert a natural-language system or workflow description into Draw.io XML; choose or fetch architecture icons; add, remove, move, rename, connect, group, or ungroup nodes; change LR/RL/TB/BT layout direction; repair or validate mxGraph files; or prepare a diagram to open in diagrams.net.
---

# Draw.io mxGraph

Create editable diagrams as uncompressed mxGraph XML. Keep stable cell IDs across edits so future requests can modify the existing diagram instead of regenerating it.

## Workflow

1. Interpret the description as nodes, edges, groups, and layout direction.
2. Create a graph-spec JSON file following [references/graph-spec.md](references/graph-spec.md).
   Use `node.icon` for icon-based nodes and follow [references/icons.md](references/icons.md).
3. Run:

   ```bash
   python3 scripts/drawio_tool.py build --spec graph.json --output diagram.drawio
   ```

4. Validate every produced or edited diagram:

   ```bash
   python3 scripts/drawio_tool.py validate diagram.drawio
   ```

5. Open the `.drawio` file in diagrams.net, the Draw.io desktop app, VS Code with a Draw.io extension, or another mxGraph-compatible editor when available.

Choose concise stable IDs such as `api`, `orders-db`, and `edge-api-db`. Never derive IDs from coordinates. Preserve IDs when labels or positions change.

## Icons and shape libraries

Prefer icons for recognizable products, cloud services, actors, and infrastructure. Prefer ordinary Draw.io shapes for abstract process steps and containers.

Select icons automatically by default. Match the node ID, label, and type against the semantic rules in `assets/icon-catalog.json`. Preserve explicit `style`, `drawio_shape`, or `icon` values. Keep standard database, decision, document, and queue notation unless the user explicitly requests an icon. Use `auto_icons: false` in the graph spec or `--no-auto-icons` to disable automatic selection.

List bundled aliases and mainstream libraries:

```bash
python3 scripts/drawio_tool.py icons list
python3 scripts/drawio_tool.py libraries
python3 scripts/drawio_tool.py shapes
```

Search Iconify or fetch one icon:

```bash
python3 scripts/drawio_tool.py icons search "agent robot"
python3 scripts/drawio_tool.py icons fetch mdi:robot-outline
```

Set `node.drawio_shape` to a native Draw.io stencil alias or exact `mxgraph.*` name. Set `node.icon` to a bundled alias, an Iconify `prefix:name`, or a local SVG/PNG/JPEG/WebP/GIF path. During `build` and `edit`, fetch missing Iconify SVGs, cache them under `assets/icons/`, and embed them as Data URIs so the `.drawio` file remains portable. Use `--offline` to reject uncached icons instead.

For compact architecture cards, set top-level `icon_layout` to `tile` and
`icon_tile_size` to a square size such as `96`. Tile mode places the icon and
label inside a bordered square so connectors terminate at the card edge rather
than crossing external labels.

Read [references/icons.md](references/icons.md) before adding a library, selecting third-party icons, or changing aliases.

## Incremental edits

Prefer an operations JSON file over rebuilding the diagram. Translate the user's requested changes into operations documented in [references/graph-spec.md](references/graph-spec.md), then run:

```bash
python3 scripts/drawio_tool.py edit \
  --input diagram.drawio \
  --ops changes.json \
  --output diagram-updated.drawio
```

Supported operations include `add_node`, `update_node`, `remove_node`, `move_node`, `add_edge`, `remove_edge`, `group`, `ungroup`, and `set_layout`. `add_node` and `update_node` accept icons.

Apply only the requested changes. Preserve unaffected labels, styles, IDs, edge routing, and positions. Use `set_layout` only when the user asks to rearrange or change direction.

## Diagram conventions

- Use `rounded=1;whiteSpace=wrap;html=1;` for services and process steps.
- Use the cylinder style for databases.
- Use swimlane containers for groups or architectural zones.
- Label edges with protocols, events, or decisions only when useful.
- Give labeled edges an opaque label background and a subtle border so text
  remains distinct from connectors and grid lines.
- Use `edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;` for architecture edges.
- Default to `LR` for architecture and `TB` for business processes unless the description implies otherwise.
- Keep enough spacing for readable labels and future editing.
- Add explicit edge `points` for multi-branch flows, cross-group connections, feedback paths, or any connector that would otherwise cross a node.
- Prefer short local connectors and shared merge buses. Avoid edges that loop around the full diagram.
- Visually inspect complex outputs in diagrams.net before delivery; XML validation alone does not verify routing or icon rendering.

## Validation and safety

Always run `validate` after `build` or `edit`. Treat validation errors as blocking and fix them before delivery. Validation accepts standard uncompressed Draw.io XML and can inspect compressed diagram payloads, but incremental editing requires uncompressed XML.

Do not hand-edit XML when the bundled tool can express the requested change. If direct XML editing is necessary, preserve the required `mxfile > diagram > mxGraphModel > root` hierarchy, base cells `0` and `1`, unique IDs, valid parent/source/target references, and `mxGeometry` elements.

Use [assets/example-agent-architecture.drawio](assets/example-agent-architecture.drawio) and [assets/example-agent-architecture.json](assets/example-agent-architecture.json) as a smoke-test pair.
