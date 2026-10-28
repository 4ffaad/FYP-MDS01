# Editable architecture diagrams

The report includes four detailed diagrams; the backend handover adds a
security-flow diagram. Each is editable in diagrams.net and has a stable-ID
JSON graph specification beside it. Static SVG/PNG previews are generated from
the same JSON; they are documentation previews, while the `.drawio` file is the
editable source.

| Diagram | Shows | Editable source | Preview |
|---|---|---|---|
| System architecture | Next.js, FastAPI services, owner authorization, database and encrypted file boundary | [Draw.io](system-architecture.drawio) · [JSON](system-architecture.json) | [SVG](system-architecture-preview.svg) · [PNG](system-architecture-preview.png) |
| EEG to H5 | Encrypted source intake, source waveform path, validated H5 input and timestamped output | [Draw.io](eeg-h5-processing.drawio) · [JSON](eeg-h5-processing.json) | [SVG](eeg-h5-processing.svg) · [PNG](eeg-h5-processing.png) |
| Combined VEEG review | Separate EEG and reference-video paths, clock mapping, owner-authorized popup and format preparation independent of VSViG | [Draw.io](veeg-review-flow.drawio) · [JSON](veeg-review-flow.json) | [SVG](veeg-review-flow.svg) · [PNG](veeg-review-flow.png) |
| Standalone VSViG | Pose validation, 15-joint patches, VSViG windows, score and Grad-CAM evidence | [Draw.io](vsvig-gradcam.drawio) · [JSON](vsvig-gradcam.json) | [SVG](vsvig-gradcam.svg) · [PNG](vsvig-gradcam.png) |
| Backend security flow | FastAPI request boundaries, EEG/H5, VEEG playback, standalone VSViG, encrypted files, selected database encryption, and runtime key custody | [Draw.io](backend-security-flow.drawio) · [JSON](backend-security-flow.json) | [SVG](backend-security-flow.svg) · [PNG](backend-security-flow.png) |

The [presentation architecture](presentation-architecture.drawio) is a separate
slide-oriented overview. It intentionally emphasizes the EEG/H5 and standalone
video/VSViG model paths.

## Rebuild and validate

From the repository root:

```sh
python3 .agents/skills/drawio-mxgraph/scripts/drawio_tool.py build --spec docs/diagrams/system-architecture.json --output docs/diagrams/system-architecture.drawio --offline
python3 .agents/skills/drawio-mxgraph/scripts/drawio_tool.py build --spec docs/diagrams/eeg-h5-processing.json --output docs/diagrams/eeg-h5-processing.drawio --offline
python3 .agents/skills/drawio-mxgraph/scripts/drawio_tool.py build --spec docs/diagrams/veeg-review-flow.json --output docs/diagrams/veeg-review-flow.drawio --offline
python3 .agents/skills/drawio-mxgraph/scripts/drawio_tool.py build --spec docs/diagrams/vsvig-gradcam.json --output docs/diagrams/vsvig-gradcam.drawio --offline
python3 .agents/skills/drawio-mxgraph/scripts/drawio_tool.py build --spec docs/diagrams/backend-security-flow.json --output docs/diagrams/backend-security-flow.drawio --offline
python3 .agents/skills/drawio-mxgraph/scripts/drawio_tool.py validate docs/diagrams/system-architecture.drawio
python3 .agents/skills/drawio-mxgraph/scripts/drawio_tool.py validate docs/diagrams/eeg-h5-processing.drawio
python3 .agents/skills/drawio-mxgraph/scripts/drawio_tool.py validate docs/diagrams/veeg-review-flow.drawio
python3 .agents/skills/drawio-mxgraph/scripts/drawio_tool.py validate docs/diagrams/vsvig-gradcam.drawio
python3 .agents/skills/drawio-mxgraph/scripts/drawio_tool.py validate docs/diagrams/backend-security-flow.drawio
python3 docs/diagrams/render_previews.py docs/diagrams/system-architecture.json docs/diagrams/eeg-h5-processing.json docs/diagrams/veeg-review-flow.json docs/diagrams/vsvig-gradcam.json docs/diagrams/backend-security-flow.json
```

Refresh the PNG previews from the SVGs with the repository's Playwright CLI,
using a viewport that fits each diagram. Inspect each preview after layout edits.
The static SVG renderer in `render_previews.py` is deliberately lightweight;
export from diagrams.net when its exact rendering is needed. Keep diagram labels
consistent with `docs/project-design.md` and never include patient identifiers,
local data paths, or secrets.
