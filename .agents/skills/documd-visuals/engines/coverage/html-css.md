# html-css coverage ledger

> Generated from `catalog/scenarios.json` plus the curated unit table for this engine.
> Runtime: the document renderer plus the page-skeleton and connector patterns in the engine reference. Last generated: 2026-09-22.

**Units** record what this engine does with each unit of its official documentation — kept, or
excluded with the reason. **Examples by goal** is collected from the catalog, so every link below is
resolvable from this file.

## Rules (5 original → all kept)

| Rule | Disposition | Where it is enforced |
|---|---|---|
| Embed HTML directly, never in a ` ```html ` fence | kept | `SKILL.md` iron rule 4 · validator (` ```html ` in examples fails) |
| No blank line inside an HTML block | kept | validator warns per file; `engines/html-css.md` explains the CommonMark termination |
| Analyse content before choosing a layout (density → structure → mood) | kept | `engines/html-css.md` |
| Choice of column count (one / two / three) | kept | [Page skeletons](../html-css.md) — the geometry table |
| Layer semantics, consistent colour, grid discipline | kept | [Page skeletons](../html-css.md) — the rules under the table |

Added from implementation archaeology: class-name prefixes (`card-*`) because `<style scoped>` does
nothing, a `max-width` on the card root, and inline images as data URLs.

## Inventory (90 files → 90 kept, reorganised)

| Group | Count | Disposition |
|---|---|---|
| the engine reference | 13 | **triaged** — see below |
| the engine reference | 12 | **triaged** — see below |
| the engine reference | 36 | **triaged** — see below |
| the engine reference | 29 | **triaged** — see below |

### Design-library triage (2026-09-22)

The inherited library (49 layouts + 41 styles, 604 KB) was audited against the catalog: each entry's
“best for” was matched to the 30 goal domains. Almost all of it was **form, not intent** — the same reader
need already served by an example, with different geometry or palette. Per the taxonomy rule that scenarios
are defined by reader and use (not by template), the library is not shipped:

| Outcome | Count | Detail |
|---|---|---|
| Promoted to a scenario | 1 | `quote-card` → [`internal-documents/key-quote-card.md`](../../examples/internal-documents/key-quote-card.md) — citing a statement had no scenario before |
| Folded into this engine reference | 2 | `connectors` and `layer-layouts` are technique, not content → their content became the *Page skeletons* and *Connectors* sections of [`../html-css.md`](../html-css.md) |
| Deleted | 87 | Content prototypes already carded (board memo, policy memo, incident review, compliance audit, risk register, sales/partner brief, customer story, research abstract, news bulletin, org update, education module, metric board, roadmap board), page geometry (columns, sidebar variants, bento, hub-spoke, banner, nested containers, split panel, hero), and all 41 tone styles — a tone is a delivery attribute, not a scenario |

Recoverable from git history if ever needed: `git show HEAD:infocard/layouts/<name>.md`,
`git show HEAD:architecture/styles/<name>.md`.

## Two jobs, one tool

| Job | Where the examples live |
|---|---|
| Content artefact — one page that settles one question | [internal-documents](../../goals/internal-documents.md), [customer-and-partner-comms](../../goals/customer-and-partner-comms.md), [catalogues-and-inventories](../../goals/catalogues-and-inventories.md), [incident-review-card](../../examples/incident-management/incident-review-card.md) |
| System architecture — the whole system on one page | [system-architecture](../../goals/system-architecture.md) — seven shapes: `layered-with-wings` (the default), `layer-stack`, `operations-overview`, `nested-zones`, `pipeline-stages`, `request-paths`, `service-catalog` |

## Export boundary (verified)

| Item | Fact | Consequence |
|---|---|---|
| HTML export | a card is rasterised — the exported file contains one `<img>` + a data URL, class names and text are gone | never keep the only copy of a fact inside a card |
| DOCX export | same rasterisation via the HTML plugin | card text is not selectable or searchable |
| `grid` / `flex` / `border-radius` / `gradient` / `box-shadow` | no DOCX semantics | these survive as a screenshot, not as reflowable content |
| `<style scoped>` | dead attribute, and the pipeline has no scoping step | prefix every class |
| Fonts | follow the document theme | do not hard-code `font-family` |
| Images | local or data URLs only | remote images are unreliable offline |

## Examples by goal

24 examples across 9 goal domains.

### [system-architecture](../../goals/system-architecture.md)

| Scenario | Tier | Example |
|---|---|---|
| complex system blueprint | T1 | [complex-system-blueprint.md](../../examples/system-architecture/complex-system-blueprint.md) |
| layer stack | T1 | [layer-stack.md](../../examples/system-architecture/layer-stack.md) |
| layered with wings | T1 | [layered-with-wings.md](../../examples/system-architecture/layered-with-wings.md) |
| nested zones | T1 | [nested-zones.md](../../examples/system-architecture/nested-zones.md) |
| operations overview | T1 | [operations-overview.md](../../examples/system-architecture/operations-overview.md) |
| pipeline stages | T1 | [pipeline-stages.md](../../examples/system-architecture/pipeline-stages.md) |
| request paths | T1 | [request-paths.md](../../examples/system-architecture/request-paths.md) |
| service catalog | T1 | [service-catalog.md](../../examples/system-architecture/service-catalog.md) |

### [customer-and-partner-comms](../../goals/customer-and-partner-comms.md)

| Scenario | Tier | Example |
|---|---|---|
| customer story | T2 | [customer-story-card.md](../../examples/customer-and-partner-comms/customer-story-card.md) |
| education module | T2 | [education-module-card.md](../../examples/customer-and-partner-comms/education-module-card.md) |
| news bulletin | T2 | [news-bulletin-card.md](../../examples/customer-and-partner-comms/news-bulletin-card.md) |
| partner brief | T2 | [partner-brief-card.md](../../examples/customer-and-partner-comms/partner-brief-card.md) |
| sales brief | T2 | [sales-brief-card.md](../../examples/customer-and-partner-comms/sales-brief-card.md) |

### [internal-documents](../../goals/internal-documents.md)

| Scenario | Tier | Example |
|---|---|---|
| executive brief | T2 | [executive-brief-summary.md](../../examples/internal-documents/executive-brief-summary.md) |
| key quote | T2 | [key-quote-card.md](../../examples/internal-documents/key-quote-card.md) |
| policy memo | T2 | [policy-memo-card.md](../../examples/internal-documents/policy-memo-card.md) |
| research abstract | T2 | [research-abstract-card.md](../../examples/internal-documents/research-abstract-card.md) |

### [security-and-compliance](../../goals/security-and-compliance.md)

| Scenario | Tier | Example |
|---|---|---|
| compliance audit | T2 | [compliance-audit-card.md](../../examples/security-and-compliance/compliance-audit-card.md) |
| risk register | T2 | [risk-register-card.md](../../examples/security-and-compliance/risk-register-card.md) |

### [goal-and-status-reporting](../../goals/goal-and-status-reporting.md)

| Scenario | Tier | Example |
|---|---|---|
| metric board | T1 | [metric-snapshot-board.md](../../examples/goal-and-status-reporting/metric-snapshot-board.md) |

### [incident-management](../../goals/incident-management.md)

| Scenario | Tier | Example |
|---|---|---|
| incident review | T1 | [incident-review-card.md](../../examples/incident-management/incident-review-card.md) |

### [comparison-and-selection](../../goals/comparison-and-selection.md)

| Scenario | Tier | Example |
|---|---|---|
| decision record | T2 | [decision-comparison-card.md](../../examples/comparison-and-selection/decision-comparison-card.md) |

### [organization-and-roles](../../goals/organization-and-roles.md)

| Scenario | Tier | Example |
|---|---|---|
| org update | T2 | [org-update-card.md](../../examples/organization-and-roles/org-update-card.md) |

### [planning-and-roadmap](../../goals/planning-and-roadmap.md)

| Scenario | Tier | Example |
|---|---|---|
| roadmap board | T2 | [delivery-roadmap-board.md](../../examples/planning-and-roadmap/delivery-roadmap-board.md) |

## Counts

| | |
|---|---|
| Examples using this engine | 24 |
| Goal domains reached | 9 |
| Scenarios | 24 |
| T0 scenarios | 0 |

## Sources

- Engine reference: [`../html-css.md`](../html-css.md)
- Catalog: [`../../catalog/scenarios.md`](../../catalog/scenarios.md)
