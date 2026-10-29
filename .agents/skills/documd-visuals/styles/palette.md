# Palette contract

The rules every colour in this skill obeys. A **theme** assigns values to the tokens below; this
file defines what those tokens are, which uses they may have, and what has to hold for a use to be
allowed.

**documd-visuals does not follow the host document's theme.** A theme is chosen for the figure, and
the figure then looks the same wherever it is pasted — in the viewer, in an export, in a slide, on
paper. That is the point: a diagram is an artefact with its own design, not a chameleon.

Values are **literal** in every theme and every block. No alias or indirection layer, in any engine,
including CSS. Token *names* exist so we can talk about the roles; what ships is values.

## Themes

Pick the one that matches where the figure will be read. Nine exist, and they are deliberately
different — that is what makes the set useful.

**Every theme is designed for a light ground.** The set ships no dark page, by decision: a figure is
an artefact with its own background, and these are the backgrounds it can carry. A dark page is the
host document's business, not something a figure follows.

| theme | use it for | ground | file |
|---|---|---|---|
| **Default** | documents, reports, dashboards | `#ffffff` | [`themes/default.md`](themes/default.md) |
| **Editorial** | long-form reading, memos, policy on cream stock | `#fdfaf3` | [`themes/editorial.md`](themes/editorial.md) |
| **Slate** | technical documentation, dashboards, API and infra references | `#f4f4f4` | [`themes/slate.md`](themes/slate.md) |
| **Print** | black-and-white printing, photocopies, low-ink handouts | `#ffffff` | [`themes/print.md`](themes/print.md) |
| **Vivid** | presentations, slides, marketing, anything projected | `#ffffff` | [`themes/vivid.md`](themes/vivid.md) |
| **Accessible** | colour-critical figures, charts read by colour-blind readers | `#ffffff` | [`themes/accessible.md`](themes/accessible.md) |
| **Contrast** | large-print handouts, low vision, projection in a bright room | `#ffffff` | [`themes/contrast.md`](themes/contrast.md) |
| **Pastel** | onboarding, education, HR and internal comms | `#eff1f5` | [`themes/pastel.md`](themes/pastel.md) |
| **Nord** | cool technical decks, developer-facing docs, Nordic branding | `#eceff4` | [`themes/nord.md`](themes/nord.md) |

Each theme is grounded in a named system or a published methodology for its hues and its structure,
but the values are this package's own and every one of them is measured against the thresholds below:

| theme | grounding |
|---|---|
| Default | IBM Carbon's White theme, read as a figure palette |
| Editorial | warm-stock long-form reading; desaturated to mark rather than shout |
| Slate | IBM Carbon Gray 10 theme — grey-scale layering plus one action blue |
| Print | ColorBrewer's single-hue ladders: the ramp is a lightness ladder first |
| Vivid | high chroma for projection; four members are light enough to be fill-only |
| Accessible | **Okabe–Ito Colour Universal Design**, warm/cool alternating, with the darker blue and orange the CUD guidance prescribes for thin marks |
| Contrast | **APCA use-case ranges** (Lc 90 fluent text, 75 minimum, 60 content) rather than the WCAG floor |
| Pastel | **Catppuccin**'s light flavour (Latte) as a document palette |
| Nord | **Nord**'s bright-ambiance reading: Snow Storm, Frost, muted Aurora |

Across the set the ramp is held inside a narrow CIELAB lightness band — Solarized's rule — so no
category shouts louder than another. The cost is greyscale separation: two categories can sit close
in luminance, reported per theme as `ramp gap` by the contrast gate. A figure that has to survive a
photocopier should use **Print**, whose ramp is a lightness ladder first and a hue set second.

Each theme file carries its own token values, its derived tints and shades, a **complete rendered
figure** showing the theme in use, and a paste-ready block for every engine. Read one file, paste one
block.

Two things a theme cannot do, and one it must:

- **Cannot** widen a token's uses beyond the contract below — only narrow them.
- **Cannot** invent a token, or put a colour in a block that is not in its own table.
- **Must** declare, for every fill that may carry a label, the colour allowed to sit on it — and
  that declaration is measured, not trusted.

## Token contract

`may be used as` is the widest set of uses a theme may grant a token; a theme narrows it, never
widens. The cap is structural, not aesthetic: an amber light enough to be a pleasant band is too
light to be text or a line, on any ground. `sits on` is the fill a text token may be placed on.

| token | may be used as | sits on | role |
|---|---|---|---|
| `ink` | text | `surface-*`, `tint-*` | body text inside fills, headings, node labels |
| `ink-soft` | text | page | secondary body text on an unfilled background |
| `muted` | text | page | captions, axes tick labels, metadata — never inside a tinted fill |
| `line` | line | – | borders, edges, arrows, axes, rules |
| `line-strong` | line | – | emphasis border, connector on a tinted fill |
| `surface-0` | fill | – | quietest container fill |
| `surface-1` | fill | – | default shape / card fill |
| `surface-2` | fill | – | nested or selected container fill |
| `cat-1` … `cat-8` | text · line · fill | – | the categorical ramp, used **in order** |
| `positive` | text · line · fill | – | gains, passes, healthy state |
| `positive-ink` | text · line | page | positive text and deltas |
| `negative` | text · line · fill | – | failures, regressions |
| `negative-ink` | text · line | page | negative text and deltas |
| `warning` | text · line · fill | – | warning fill / band |
| `warning-ink` | text · line | page | warning text and threshold lines |
| `target` | line | – | dashed reference lines / goal markers |

The ramp is positional: a chart with four categories uses `cat-1` … `cat-4`, in order. Two themes
place different colours in those slots; nothing else about the diagram changes.

`positive` / `negative` are conveniences for the two semantic families — a theme may point them at
the category that already carries that meaning (`cat-2` and `cat-4` in most themes). `-ink` variants
exist because a mid-lightness family can be a fine fill and a poor text colour; instead of darkening
the family (which wrecks the fill), each semantic family gets one readable ink variant —
`positive-ink`, `negative-ink`, `warning-ink`. A status chip is the standard use: the family's tint
as the fill, its shade as the border, its `-ink` as the words.

## Derived colours

Two derivations cover everything else. Both are **computed by the theme generator**, never
hand-picked, and the table shipped in each theme file is generated from them:

| derived | formula | allowed use |
|---|---|---|
| `tint-<family>` | mix the theme's **ground** with the family at **18 %** | fill for that family; label text is `ink` |
| `shade-<family>` | darken the family 12 % (HSL lightness) | border of that family's own fill |

Three things about this are deliberate:

- The mix base is the **ground**, not a surface. Mixing into a tinted near-white drags every hue
  towards the same grey and the tints stop being tellable apart — measured: three families' tints
  became indistinguishable. Mixing into the ground also makes the formula work unchanged on a cream
  or a dark ground.
- A family gets a `shade` **only when the theme lets it be a line**. A family too light to be a line
  is too light to border its own fill; those take the neutral `line` border.
- `shade` flips direction with the theme's polarity. On a light ground the fill is light and the
  border must be darker; on a dark ground the fill is dark and the border must be lighter.

## Modes

| mode | where | colour budget |
|---|---|---|
| **chart** | `echarts` · `vega` / `vega-lite` · `chart-*` infographics | the category ramp, up to 8 colours, in order; semantic colours only for thresholds and deltas |
| **card** | `html-css` · `plantuml` · `list-*` / `sequence-*` infographics | one accent (`cat-1`) + neutrals (`ink` / `muted` / `surface-*`) + at most one semantic colour |

Charts pass the ramp to the engine (the top-level `color` array, `config.range.category`, the
infographic `theme.palette`, the ordinal scale's `range`) in token order — never a hand-written list.
Cards pick a single accent; a second categorical colour means the layout is really a chart.

## Contrast thresholds

WCAG 2.1 relative luminance. Measured **per theme**, against that theme's own ground and against
every fill a token may sit on:

| use | threshold | rationale |
|---|---|---|
| text | **≥ 4.5** | body copy, tick labels, deltas |
| line | **≥ 3.0** | borders, edges, axes — non-text UI |
| text on a fill | **≥ 4.5** | the declared `text on it`, against that fill |

A theme is not graded against the host document's background — that is what the contract's
"filled shapes carry their own background" rule is for. It is graded against its own ground, which is
the background it was designed to sit on.

## Rules for writers

- **Pick a theme first**, then take every colour from that theme's table. Never mix two themes.
- A raw hex that is not in the theme you chose is a bug — the usage gate fails on it.
- Never put `muted` inside a tinted fill (it only clears 4.5 on the theme's ground).
- Never use a `fill`-only token as text or as a line, and never a text token as a fill.
- Charts: list up to 8 categories, in ramp order. More categories → group the tail.
- Cards: one accent plus neutrals. Semantic colour earns its place only if the card is *about* that
  state.
- A figure that must survive both a light and a dark page should use a theme whose ground matches
  neither — the `Print` ladder reads on either. Otherwise pick the theme for where it will be read.

## Verification

Every claim above is machine-checked, per theme:

| gate | what it proves |
|---|---|
| `check-palette-contrast.mjs` | every declared use of every token holds against the theme's ground and its fills |
| `verify-blocks.mjs` | every block in every theme file renders, lands its declared values, and leaves no engine default |
| `check-palette-usage.mjs` | no example uses a colour outside the theme it is written in |
| `build-themes.mjs --check` | the shipped theme files equal the source tables — no hand drift |
| `validate-skills.mjs` | the palette and every theme stay reachable from `SKILL.md`, the goal docs and the engine references |

`node skills/scripts/check-all.mjs` runs all of them.
