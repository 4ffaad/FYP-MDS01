# Key Quote Card (HTML/CSS)

**Best for**: one statement that should land on its own — a principle, a mission line, a client's words
**Avoid when**: the message needs evidence, numbers or nuance around it (use a memo or brief card)
**Answers**: what the team stands for, or what someone said about it, in one breath

<div style="max-width: 820px; box-sizing: border-box; position: relative;">
  <style>
    .card-quote { position: relative; background: #eef2fb;  padding: 48px 44px 36px; border-left: 6px solid #1f2937; }
    .card-quote-kicker { margin: 0 0 22px; font-size: 11px; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase;  }
    .card-quote-mark { margin: 0; font-size: 84px; font-weight: 700; line-height: 0.6; color: rgba(0,0,0,0.10); }
    .card-quote-line { margin: 8px 0 0; font-size: 27px; line-height: 1.5;  max-width: 620px; }
    .card-quote-mark-inline { background: linear-gradient(to top, rgba(214,59,46,0.20) 42%, transparent 42%); padding: 0 2px; }
    .card-quote-attribution { display: flex; align-items: center; gap: 14px; margin-top: 30px; }
    .card-quote-rule { width: 44px; border-top: 3px solid #6d4f36; flex-shrink: 0; }
    .card-quote-name { margin: 0; font-size: 14px; font-weight: 700;  }
    .card-quote-role { margin: 2px 0 0; font-size: 12px;  }
    .card-quote-footer { margin-top: 34px; padding-top: 12px; border-top: 1px solid rgba(0,0,0,0.10); font-size: 11px;  }
  </style>
  <section class="card-quote">
    <p class="card-quote-kicker">Engineering Principles · Principle 3 of 9</p>
    <p class="card-quote-mark">"</p>
    <p class="card-quote-line">We ship every day, so a change that cannot be <span class="card-quote-mark-inline">reverted in five minutes</span> is not ready to ship.</p>
    <div class="card-quote-attribution">
      <div class="card-quote-rule"></div>
      <div>
        <p class="card-quote-name">Platform Engineering</p>
        <p class="card-quote-role">Operating principles · Reviewed quarterly</p>
      </div>
    </div>
    <div class="card-quote-footer">Handbook · Principles</div>
  </section>
</div>

## Data Shape

Three fields, in this order: a **kicker** (what kind of statement this is, and where it sits in a series), the
**quote** itself (one sentence, one emphasised phrase), and an **attribution** (a name plus the role or context
that makes it authoritative).

## Key Options

| Option | Effect |
|---|---|
| One emphasised phrase | The highlight carries the sentence; two highlights cancel each other out |
| Attribution block | Name + role/context; an unattributed quote reads as the author's own opinion |
| Kicker with a position ("Principle 3 of 9") | Turns a standalone quote into part of a series the reader can expect more of |
| `card-quote-*` class prefix | `<style scoped>` does nothing in browsers — the prefix is what keeps two cards in one document apart |
| Left rule (`border-left`) | A single vertical accent reads as "pull quote" without a box |
| No `font-family` | The card inherits the document's theme font; setting one here fights the reader's theme |

## Pitfalls

- ❌ A paragraph dressed as a quote → ✅ if it needs two sentences and a caveat, it is prose, not a pull quote
- ❌ Highlighting a whole line → ✅ emphasise 1–3 words; a fully highlighted sentence highlights nothing
- ❌ Inventing an attribution or paraphrasing someone loosely → ✅ quote exactly, with the role that gives it weight
- ❌ Using the card as the only place a decision lives → ✅ cards are rasterised on export; keep the binding text in prose too
- ❌ A blank line inside the HTML → ✅ a blank line ends the HTML block and splits the card

## Alternatives

| Variant | Use instead |
|---|---|
| A principle with its rationale | `culture-principles-checklist.md` (Infographic) |
| An internal decision or policy | `policy-memo-card.md` |
| A customer's words with outcome context | `customer-story-card.md` |

<!-- source: pull-quote convention (attribution + single emphasis) + the card rules in engines/html-css.md -->
