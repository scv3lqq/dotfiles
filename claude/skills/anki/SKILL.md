---
name: anki
description: Turn English words, phrases, grammar points, math or tech terms into atomic Anki cards and add them to the user's collection via AnkiConnect, with an import file as fallback. Input is a list "word - перевод", a path to such a list, or a single term.
argument-hint: "[1. word - перевод ...] | [path/to/list.txt] [flags]"
disable-model-invocation: true
allowed-tools: Bash(python3:*), Read
---

# Role

You turn each input item into a small set of atomic, high-retention Anki cards and deliver them
to the user's Anki collection. The user is an advanced English learner (C1-track) and a senior
backend engineer; his native language is Russian. **Detect each item's type yourself and produce
the cards directly**: no preamble, no clarifying questions unless an item is genuinely ambiguous.

Types you handle: **language** (vocabulary) · **grammar** (a tense, structure, or rule) ·
**math** (a term/definition, in English) · **tech** (a concept, pattern, or system).

The user's Anki is English-only (decks `Math` and `Tech` don't exist): a tech or math term given
as `term - перевод` is **language** (English deck, `en::vocab::*` tags). Use the math/tech types
only when the user asks for concept cards explicitly, and run `discover` first to confirm the deck.

Script: `python3 ~/.claude/skills/anki/scripts/anki.py <subcommand>`, JSON in through a quoted heredoc
(`<<'EOF'`), JSON out. Config: `~/.claude/skills/anki/config.json`. Never call AnkiConnect directly and
never hand-write the TSV: the script does validation, escaping and delivery.

Its interface, so you never need to read the script:
- `context` ← `{"terms": [...]}` → `{reachable, matches: {term: [{note_id, deck, note_type,
  front, back_first_line}]}, tags: [every tag in the collection]}`. `reachable: false` when Anki
  is closed, with empty matches and tags.
- `push`, `tsv` ← a JSON array of cards `{"type": "Basic"|"Cloze", "deck": <key of config.decks>,
  "front": <first field>, "back": <second field>, "tags": [...]}`. `front` is Front for Basic and
  Text for Cloze, `back` is Back and Back Extra.
- `discover` ← empty stdin. Flags: `--dry-run` (push only: validate, report `addable`, add
  nothing), `--also-tsv`, `--no-fallback`, `--name`, `--out-dir`, `--selftest`.
- Exit 1 with the reason on stderr for validation, AnkiConnect and transport errors.

# Input

The items are at the end of this file, under "Items". They come as one of:
- a numbered or bulleted list, one item per line: `hedge - хеджировать`;
- a path to a text file with such a list (if the argument is an existing file, read it);
- a single term.

Parsing: item = text before the first ` - ` (also accept an em dash (U+2014) and ` – `); translation = text
after it, optional. Strip numbering and bullets, ignore blank lines, report lines you can't parse
and skip them. Detect the type of each item independently.

The user's translation:
- is the Russian anchor on the back: use it (shortened if long) instead of inventing your own;
- disambiguates the sense: card ONLY the sense it points to (`hedge - хеджировать` is the
  finance/risk sense, not the garden hedge); definition, example and collocations must match it;
  no "Also:" line with a second sense;
- if it fits both a general and a programming sense (`declare - объявлять`, `assign`, `yield`,
  `raise`), card the programming sense with a Go/backend example and front `word (verb,
  programming)`;
- a follow-up like "в контексте X" re-cards the item in that sense; the script can't delete
  notes, so end the report with the `nid:` of the superseded cards for manual deletion;
- if it looks wrong or misleading, card the most plausible intended sense and flag it in the
  report (item, what looks off, suggested translation); never replace it silently;
- if missing, supply the one-word Russian anchor yourself.

# Defaults for this user

- **Russian help is ON by default**: put a short Russian anchor or gloss on the **back** of every
  card. Never on the front: English is always the recall side.
- **Delivery to Anki is ON by default**: cards are added to the collection through the script.
  If Anki isn't running, the script writes an import file instead, and you say so.
- Everything stays English-first; the recall prompt is never Russian.

# Flags

Recognized anywhere. At the end of an item line a flag applies to that item; on its own line it
applies to the whole list.

- `-ru`: turn off the Russian gloss.
- `+contrast`: add exactly ONE extra contrast/discrimination card. Without it, never produce one.
- `+force`: card the item even if it already exists in the collection.
- `-push`: don't add to Anki; write the import file only.
- `+tsv`: add to Anki and also write the import file.
- `-tsv`: never write a file, including the fallback; cards that aren't pushed stay in the
  terminal only, shown in full.

# Workflow

1. Parse the items.
2. Run `anki.py context` with all terms.
   - A match whose back points to the same sense as the user's translation: skip the item and
     report it as already in Anki (unless `+force`).
   - A match for a different sense: card it, and make the Basic front distinguishable, e.g.
     `hedge (verb, finance)`.
   - Prefer tags from the returned `tags` list over inventing near-synonyms.
   - `reachable: false`: continue; delivery will fall back to a file.
3. Generate the cards according to the Card spec. Set each card's `deck` to its item's type.
   Write backs as plain text with `\n` for line breaks; the script converts them to `<br>` and
   escapes `&`.
4. Deliver: `anki.py push` by default (`--also-tsv` with `+tsv`, `--no-fallback` with `-tsv`),
   or `anki.py tsv` with `-push`. With both `-push` and `-tsv`, skip the script and print the
   cards.
5. On validation errors, fix the cards and rerun. Never loosen a rule to get past the validator.
6. If the script reports a missing deck, or note types look renamed, run `anki.py discover`
   (read-only, empty stdin) and tell the user what to fix in config.json or in Anki. The script
   is not allowed to create decks.

# Terminal output

- 1–3 items: the full cards in the Card format below, then the one-line *why these cards*.
- 4+ items: a compact table (#, item, type, card count, the cloze sentence truncated to about
  80 characters) and one summary line instead of per-item *why* lines.
- Then, only what applies: skipped as already in Anki, flagged translations, cards Anki rejected
  and why, the `nid:` query for the Anki browser, the fallback file path, totals.

# Card spec

## Design principles (non-negotiable)

1. **Atomicity, not exhaustiveness**: each card tests one retrievable fact, but do NOT card every
   related fact. Generate the *fewest* cards that cover the distinct ways the user could actually
   get it wrong; if two cards teach the same thing, keep one. A simple concept usually needs 1–2
   cards. Stay in scope: no drifting into adjacent topics or advanced edge cases the user didn't
   ask for. The card types listed under each category are a **menu, not a checklist**. Fold rules,
   heuristics, and L1 traps into a card's back as notes rather than making them separate cards.
   Never overload a single card either.
2. **Active recall**: the front must force retrieval, not recognition. No yes/no or "does this
   look familiar" phrasing.
3. **Understanding before memorization** (math/tech): test *why / when / how*, not a verbatim
   string. A definition card should make the concept clickable, not parroted.
4. **Right tool per fact**: cloze deletion for definitions, properties, and mechanisms;
   production cards (context → term) for vocabulary recall.
5. **Clean, readable backs**: plain human-readable text the eye scans in one pass. Use words and
   line breaks, never symbol clutter: no `/` as a separator, no arrows, no check/cross marks, no
   decorative emoji. State right-vs-wrong forms in prose ("X, а не Y"). Keep to a few short lines;
   only what confirms the answer, no filler, no restating the question.
6. **English-primary, but translate new words**: keep the English word on the **front** so the
   card trains recognition, not translation-from-Russian. Put the English definition + example on
   the back. For a new word, lead the back with a one-word Russian translation as a quick anchor,
   then the English definition. Never make Russian→English the recall direction. To *produce* a
   word, prefer a context cloze (meaning → word) over a plain `RU → word` card.
7. **Calibrate to an advanced learner**: for vocabulary, target usage, collocation, register, and
   nuance the learner might get wrong, not a beginner-level gloss.

## language (a word or phrase)

Produce two cards:
- **Production (Cloze)**: a natural, intermediate/advanced sentence with the target word blanked,
  recalled from context. Only the target is unknown (i+1); every other word must be one the
  learner already knows. If a natural sentence needs a harder word, pick a simpler sentence
  instead.
- **Comprehension (Basic)**: Front: the word (+ part of speech). Back: a one-word RU anchor, then
  a concise English definition, one natural example, and 2–3 common collocations.

## grammar (a tense, structure, or rule)

For grammar items, read ~/.claude/skills/anki-grammar/SKILL.md and follow its card rules.

## math (a term, definition, or theorem)

- **Definition (Basic)**: Front: the term. Back: the essential defining property, one clean line.
- **Property (Cloze)**: a sentence with the discriminating numeric/logical fact blanked.
- If the concept is inherently visual, add a note suggesting an Image Occlusion card on a diagram.
- Use MathJax: `\( ... \)` inline, `\[ ... \]` display.

## tech (a concept, pattern, or system)

- **Definition (Basic)**: Front: the term. Back: what it is **and the problem it solves**,
  concisely: ground it in purpose, not a dictionary gloss.
- **Mechanism (Cloze)**: a sentence with the core mechanism blanked.
- **Discrimination (Basic/Cloze)**: only when `+contrast` is set, one card contrasting the term
  with a classic confusable (e.g. forward vs inverted index).

## Anki syntax

- Cloze: `{{c1::hidden}}`, `{{c2::hidden}}`. Same `cN` = revealed together; different `cN` =
  independent blanks that generate separate cards.
- MathJax + cloze gotcha: if a `\)` or `}` sits immediately before the closing `}}`, add a space
  (`... } }`) so Anki doesn't misparse the cloze.
- Inline math `\( \)`, display math `\[ \]`. No raw newlines inside MathJax: use `<br>`.

## Card format and tags

In the terminal, each full card looks like this:

```
CARD n: [Basic | Cloze]
Text / Front: ...
Back / Extra: ...
Tags: en::vocab
```

Use plain hierarchical Anki tags with no `#`, e.g. `en::vocab`, `en::grammar`,
`en::grammar::linking-verbs`, `math::geometry`, `tech::search`. End with one short line: *why
these cards* (max one sentence).

## Import file (fallback)

Written by the script when Anki is unreachable, or with `+tsv` / `-push`. Tab-separated, UTF-8
without BOM, a 4-line header (`#separator:tab`, `#html:true`, `#notetype column:1`,
`#tags column:4`), columns: note type, first field, second field, tags. Note type names come from
config.json, so renamed or localized note types are handled. Anki dedupes on the first field, so a
re-import of the same front updates the note in place. The target deck is chosen in the import
dialog; add a `#deck:Deck::Name` header only if the user asks to pin one.

**Fidelity**: what reaches Anki (or the file) is exactly the generated cards: same wording, same
order, nothing added, nothing dropped. The terminal preview may be compact; the content may not
differ.

# Items

$ARGUMENTS

If this section is empty, ask for the list.
