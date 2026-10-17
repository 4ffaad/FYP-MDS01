# Icons and Draw.io libraries

## Selection order

1. Use a Draw.io native shape for process semantics: decision, database, document, queue, container, UML, BPMN, or ArchiMate.
2. Use `drawio_shape` for a native vendor stencil when its exact `mxgraph.*` name is known.
3. Use a bundled alias from `assets/icon-catalog.json` for common architecture concepts and product logos.
4. Use an exact Iconify ID such as `mdi:robot-outline` when an alias is unavailable.
5. Use a local SVG or bitmap path for company-owned or user-provided assets.

Do not use decorative icons when a standard notation communicates more precisely.

## Automatic selection

Automatic selection is enabled by default. Match node IDs, labels, and types against `auto_rules` in `assets/icon-catalog.json`, in listed order. More specific vendor and product rules must precede generic words.

Preserve explicit choices. Never override `style`, `drawio_shape`, or `icon`. Keep database, decision, document, and queue nodes in their standard notation unless explicitly decorated.

Disable automatic selection with either:

```json
{"auto_icons": false}
```

or:

```bash
python3 scripts/drawio_tool.py build --no-auto-icons --spec graph.json --output diagram.drawio
```

## Mainstream Draw.io libraries

The catalog records these commonly useful libraries:

- General and Flowchart
- UML / UML 2.5
- BPMN
- ArchiMate
- Entity Relation
- Network and Cisco
- Amazon Web Services
- Microsoft Azure
- Google Cloud Platform
- Kubernetes
- Draw.io extra icon sets at icons.diagrams.net

Run `python3 scripts/drawio_tool.py libraries` to show their names and activation paths. In diagrams.net, enable built-in libraries from **More Shapes**. Open downloaded custom `library.xml` files with **File > Open Library from > Device**.

Library activation affects the editor sidebar; it is not required to render icons already embedded in a generated `.drawio` file.

List bundled native stencil aliases:

```bash
python3 scripts/drawio_tool.py shapes
```

Use an alias or an exact stencil name:

```json
{"id": "run", "label": "Cloud Run", "drawio_shape": "gcp-cloud-run"}
{"id": "router", "label": "Router", "drawio_shape": "mxgraph.cisco19.router"}
```

## Iconify commands

Search:

```bash
python3 scripts/drawio_tool.py icons search "language model" --limit 20
python3 scripts/drawio_tool.py icons search kubernetes --prefix logos
```

Fetch and cache:

```bash
python3 scripts/drawio_tool.py icons fetch mdi:robot-outline
python3 scripts/drawio_tool.py icons fetch mdi:shield-check-outline --color "#2563eb"
```

Use in a graph spec:

```json
{"id": "planner", "label": "Agent Planner", "icon": "agent"}
{"id": "cluster", "label": "Kubernetes", "icon": "logos:kubernetes"}
{"id": "company", "label": "Company Service", "icon": "/absolute/path/company.svg"}
```

Build and edit fetch missing Iconify icons by default. Pass `--offline` to require cached or local icons.

## Adding aliases

Add a short semantic key to `assets/icon-catalog.json`:

```json
"feature-store": "mdi:database-cog-outline"
```

Keep alias keys lowercase and hyphenated. Map one concept to one stable Iconify ID. Do not silently replace an existing alias with a visually different icon.

## Portability and licensing

Embed fetched SVG and local images as Data URIs in mxGraph styles. This keeps the output independent of external URLs while preserving each icon as a movable, resizable Draw.io cell.

Icon sets have different licenses and trademark rules. Inspect the source collection's license before commercial distribution. Do not imply that a third-party product logo is owned or endorsed by the diagram author.
