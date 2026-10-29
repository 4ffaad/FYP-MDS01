# plantuml

> PlantUML-compatible diagrams. Authority for what this engine can do is the **implementation**, not the
> PlantUML marketing page: `@markdown-viewer/draw-uml` **1.5.2** → `@markdown-viewer/drawio2svg` 1.5.5.
> Every capability below comes from a 41-case fixture check that is replayed against the shipped bundle
> on each engine upgrade — the tables are measurements, not PlantUML documentation.

## Scope

| Area | Supported |
|---|---|
| UML | Class · Sequence · Activity (incl. lanes + legacy syntax) · State · Use case · Component · Deployment · Object/Map |
| Non-UML | ArchiMate · MindMap (`@startmindmap`) · Gantt · packetdiag (`@startpacketdiag`) · ER/IE (crow's foot) |
| Text | Creole rich text (bold/italic/lists/tables/emoji/HTML fragments) |
| Preprocessing | `!include` · `!define` · `!pragma` · `!theme` · `!function` |
| Icons | **`mxgraph.*` stencils — 9,514 icons across 60 families** (this engine's unique selling point) |
| Layout | `!pragma layout elk` (default) · `!pragma layout vizjs` (Graphviz behaviour) |
| Styling | Inline colour suffixes (`#fill`, `##stroke`, `#c;line:red;line.bold;text:blue`) |
| Containers | `cloud` · `node` · `rectangle` · `database` · `package` · `frame` (nestable) |
| Macros | C4 (`C4_*`) · AWS library (`awslib`) — legacy alternatives to stencils |

**Pipeline** (why this engine is the only icon-capable one):

```
PlantUML text ──draw-uml──► layout + icons ──drawio2svg──► SVG
```

That intermediate step is **not** a writing target — it is the pipeline, not a format to author in.

## Fit

- Choose PlantUML **whenever a brand/device icon is needed** — no other recommended engine has an icon library.
- Primary engine for process/BPMN, integration/EIP, software design, interfaces/sequence, cloud, network,
  security and enterprise architecture (ArchiMate).
- Also the engine for plain relationship graphs — dependency, causality, hierarchy, state machine: a
  `rectangle` per node and one arrow per relation, with the layout computed from the edges.

## Support levels (read this before writing)

Not every diagram type behaves the same. Three levels, verified from the parser and fixtures:

| Level | Meaning | Types |
|---|---|---|
| **L1 renders** | Produces a real diagram | all seven UML types above, ArchiMate, MindMap, Gantt, packetdiag, ER/IE, Creole, preprocessing |
| **L2 parses, does not draw** | ⚠️ **Silent failure** — no error, empty output | `@startwbs` · `@starttiming` (Timing) · `@startsalt` (Salt) |
| **L3 unsupported** | No parser rule | JSON · YAML · EBNF · Regex · nwdiag · SDL · Ditaa · Chronology · Math · Chart · Files tree |

⚠️ `@startwbs` is the dangerous one: it parses and exits 0, but the SVG comes out as an empty 342-byte file.
Use a mind map (`@startmindmap`) or a boxed rectangle tree instead, and say so instead of
"fixing" the WBS block.

### Single-line nesting blocks

`class User { +String name }` — the canonical PlantUML shorthand — **renders correctly** (`class`, `package`,
`node`, `cloud`, `frame`, `folder`, `rectangle`; verified against all eight containers). Prefer the multi-line
form anyway, because **official PlantUML rejects most of the one-line forms**: 1.2026.6 renders
`package P { rectangle R }` and `rectangle R { rectangle S }` but turns `class K { +int x }`,
`node N { … }`, `cloud C { … }` and `folder F { … }` into a syntax-error image. This engine is the
lenient superset; a diagram written here may not paste back into a stock PlantUML server.

```plantuml
class User {                     ' ✅ works here, and everywhere else
  +String name
}
```

## Styling

Every example starts from a theme's `plantuml` blocks — pick the theme in
[`../styles/palette.md`](../styles/palette.md), then copy from that theme file (the corpus uses
[`../styles/themes/default.md`](../styles/themes/default.md)): one block per diagram family, copied
verbatim, plus element suffixes where `skinparam` cannot reach. The tables below are the capability
survey behind those blocks.

The block is a **UML** block: `@startmindmap`, `@startgantt`, `@startpacketdiag` and `@startwbs`
ignore `skinparam` entirely (measured — byte-identical output with and without it), so those blocks
carry no styling rather than a block that does nothing.

Colour reaches the output through a small, verified subset of the PlantUML style syntax:

| Works | Notes |
|---|---|
| `skinparam <Type>BackgroundColor` / `BorderColor` / `FontColor` | 13 element types: Rectangle · Component · Class · Usecase · Database · Node · Actor · State · Note · Artifact · Cloud · Folder · Package |
| `skinparam Participant*` · `SequenceLifeLineBorderColor` · `Note*` | sequence participants, lifelines and notes |
| `skinparam ArrowColor` / `ArrowFontColor` / `DefaultFontColor` | edges and default text, including edge labels |
| Nested `skinparam X { … }` and `skinparam X<<tag>> { … }` | keeps a block short; key names are case-insensitive |
| Sequence aliases `sequenceArrowColor` · `skinparam sequence { ArrowColor }` · `{ LifeLineBorderColor }` · `SequenceParticipantBorderColor` | identical output to the generic keys |
| Element suffixes `#fill`, `##border`, `#fill##border`, `#line:x;back:y;text:z`, legacy `#c;line:x;line.bold;text:z` | per-element control; illegal colours are rejected instead of emitted |
| Custom type spot `class A <<(C,#CDE7FF)>>` | recolours the type badge of a single element; both engines support it |
| `skinparam stereotype<L>BackgroundColor` / `stereotype<L>BorderColor` (L = the badge letter: `A` abstract · `C` class · `E` enum · `I` interface) | recolours the type badge of every stereotyped element whose badge carries that letter — the letter must match the element type, so `stereotypeC*` does not touch an interface. `class A <<(C,#hex)>>` still overrides it per element; `stereotype<L>FontColor` has no effect (official ignores it too) |
| Activity steps `:step; <<#fill>>` (modern) and `#fill:step;` (legacy, superset) | the two ways to colour an activity step |
| `<style>` rules for `root`, `rectangle`, `classDiagram`, `activityDiagram`, `participant` | `root` covers the whole diagram; per-diagram selectors override skinparams |
| Colour aliases `!define BRAND cde7ff` + `#BRAND` | no `#` in the define value — `!define X #hex` expands to `##hex` and breaks. The theme blocks deliberately do not use aliases: they write values literally |
| `!theme plain` | swaps the default fill for white |
| Layout params `roundcorner` · `DefaultFontSize` · `nodesep` · `ArrowThickness` | theme-wide rounding, type scale, sibling spacing, edge width |

| Ignored — do not write them | |
|---|---|
| `Padding` | deliberately unimplemented (it only pads the canvas) |
| `shadowing` · `defaultFontName` · `handwritten` · `monochrome` · `linetype ortho` | no-ops |
| `!theme <anything but plain>` | ignored |
| `PackageFontColor` · `SequenceBoxBackgroundColor` · `ActivityStartColor` · `ClassHeader*` · `ClassAttributeFontColor` · `ClassArrowColor` · `skinparam backgroundColor` | no colouring from these keys |
| `Legend*` · `TitleFontColor` | legend and title cannot be coloured by skinparam at all |
| `<style> activity` / `<style> sequenceDiagram` | only the selectors listed as working above are honoured |

The engine reports every ignored or malformed directive through its diagnostics channel
(`UNSUPPORTED_SKINPARAM` · `UNKNOWN_SKINPARAM` · `INVALID_COLOR` · `EMPTY_DIAGRAM` · `UNPARSABLE_LINE` ·
`UNIMPLEMENTED_SHAPE` · `DEPRECATED_SYNTAX`). That channel is available to the JS API and the viewer; the
`documd` CLI does not print it, so a file that renders fine can still contain no-op style lines.

Unstyled diagram text is near-black (`rgb(24,24,24)`) on a light fill, and the renderer does no dark-mode
adjustment — so a diagram that must sit on an arbitrary page needs its own fills, not inherited defaults.

## Constraints

- Sequence diagrams always use a fixed grid layout — the `!pragma layout` setting does not apply.
- The correct default layout engine without a pragma has not been settled from the sources; write the pragma
  explicitly when the layout matters.
- Hyperlinks/tooltips and OpenIconic/Sprite icons have no fixture coverage — do not build examples on them;
  use `mxgraph.*` stencils for any icon need.
- Icon names must exist. An unknown `mxgraph.<family>.<icon>` renders a placeholder box. Validate against the
  stencil index in `plantuml-stencils/` before shipping a diagram.
- Prefer the fixture-proven syntaxes: `skinparam` · `hide` · `title` · `note` · `left to right` · `scale` ·
  `!include` · `autonumber` · `header` · `legend` · `footer` · `caption` · `together`.

## Anti-patterns

| ❌ Don't | ✅ Do |
|---|---|
| One-line nesting in a diagram that may be pasted into stock PlantUML | Open the brace on its own line — this engine accepts both, official PlantUML only the multi-line form |
| `@startwbs` for a work breakdown | `@startmindmap`, or a boxed rectangle tree — WBS renders empty |
| `@starttiming` / `@startsalt` | A `sequence` diagram for timing; HTML/CSS for wireframes/mockups |
| Free-hand hex colours on every element | `skinparam` once at the top, or stencil families that share a palette |
| A 60-stencil tour in one diagram | One icon family per diagram; the family *is* the visual language |
| Repeating the full diagram in each example | One diagram per example file; link instead |
| Relying on `@startuml` type inference | Write the explicit type keyword (`class`, `sequence`, `archimate`) |

## Icon families worth using (12 of 60)

`AWS4` · `Azure` · `GCP2` · `Kubernetes` · `Networks` · `Cisco` / `Cisco19` · `Cisco Safe` · `BPMN` · `EIP` ·
`Lean Mapping` · `Archimate` / `Archimate 3` · `Mockup` / `Webicons`.

Everything else is indexed in `plantuml-stencils/` — check there before inventing a family name.
`Basic` and `Flowchart` are the neutral fallbacks when no domain family fits.

## Sources

- Coverage ledger — every official diagram type and feature, kept or excluded with a reason:
  [`coverage/plantuml.md`](coverage/plantuml.md)
- Diagram index: <https://github.com/plantuml/plantuml> (README "Supported Diagram Types")
- draw-uml: <https://github.com/nicedoc/draw-uml#readme>
- Support-level evidence: `~/works/draw-uml-dev` — `docs/puml.peggy`, `fixtures/plantuml/**`,
  `fixtures/svg-generated/**`, `packages/draw-uml/src/parsers/**`
- Stencil index: [`plantuml-stencils/README.md`](plantuml-stencils/README.md) — one file per family, generated from the
  draw-uml runtime
