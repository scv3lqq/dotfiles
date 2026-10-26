---
name: obsidian-sr-flashcards
description: Write, review, fix and lint spaced-repetition flashcards for the Obsidian Spaced Repetition plugin (st3v3nmw) from technical books and notes, especially dense internals books such as Egor Rogov's "PostgreSQL 18 Internals" («PostgreSQL 18 изнутри»). Use this skill whenever the user asks to create, generate, add, improve, split, rewrite, review or check flashcards / cards / SRS prompts in an Obsidian vault, mentions spaced repetition, `#flashcards` decks, `::` or `?` card syntax, cloze deletions, or says things like «сделай карточки по главе», «карточки для интервального повторения», «улучши/проверь мои карточки», even if the plugin is not named.
---

# Flashcards for Obsidian Spaced Repetition, from technical books

Vault-specific overrides: read `~/.claude/private/obsidian-sr-flashcards.md` when it exists; it wins over the plugin workflow below.

Goal: turn what the user reads (e.g. a chapter of Rogov's *PostgreSQL 18 Internals*) into cards that
(1) the Obsidian SR plugin parses correctly, and (2) actually build durable, usable understanding:
the kind that helps when reading an `EXPLAIN` plan or debugging bloat, not just reciting sentences.

Supporting files (read when needed):
- `references/plugin-syntax.md`: exact card syntax, plugin settings file, scheduling comments, and
  **parser traps verified against the plugin source** (several of them silently delete cards).
  Read it before writing into a vault for the first time in a session.
- `references/pg-internals-examples.md`: worked before/after examples for PostgreSQL internals
  topics (MVCC, vacuum, WAL, locks, planner, indexes, PG 18 changes). Read it when writing cards
  for that book or any similar systems book.
- `scripts/lint_cards.py`: a port of the plugin's parser plus quality checks. Run it after every
  write.
- `references/interview-filter.md`: **which facts deserve a card at all** (interview test,
  P1/P2/P3, calibration examples, type mix, volume). Read it every time before writing cards: it
  overrides anything below that suggests carding parameters, identifiers or numbers.

---

## 1. Why cards fail: the four things to get right

A review only trains memory if you retrieve the *same specific thing* each time and can grade
yourself honestly. Most weak cards break one of these:

1. **Precise.** The question has one correct answer, so two graders would agree on pass/fail.
   "How does X help Y?" has dozens of acceptable answers, so you accept whatever you recalled
   and nothing specific gets trained.
2. **Atomic** (Wozniak's minimum-information principle). One retrieval per card. If the answer
   has three facts, recalling two feels like a pass and the third is never trained.
3. **Causal.** For a mechanism, the card should force you to produce the *reason*, not just the
   conclusion. Otherwise you memorise a sentence and it won't transfer to a real situation.
4. **Covering the useful side.** Happy-path facts are often the least useful. The negative case,
   the failure mode, who maintains the state, and how to observe it are where practical value is.

Andy Matuschak's summary of the same idea: prompts should be *focused, precise, consistent,
tractable, effortful*. Tractable means you can answer correctly ~90% of the time; if a card
keeps failing, it's usually too big or too vague, so split it or add a cue.

## 2. Worked example: the user's current card

Before (a typical weak card):

```
Как карта видимости помогает index-only scan?
?
Если страница all-visible, не нужно идти в таблицу проверять видимость строки
```

What's wrong: the stem «как помогает» is vague (not precise); the answer states a conclusion
without the cause (why would the table be needed at all?); it covers only the happy path; the
practical facts (what happens otherwise, who sets the bit, how you'd notice) are missing.

After: one concept, several angles, each card a single retrieval:

```
Почему при обычном индексном доступе PostgreSQL обращается к таблице, даже если все нужные столбцы есть в индексе?
?
В индексных записях нет информации о видимости (`xmin`/`xmax`): она хранится только в версиях строк в таблице.

Index-only scan: в каком случае для найденной индексной записи всё же читается табличная страница?
?
Если у этой страницы в карте видимости не установлен бит all-visible.

Какая строка `EXPLAIN (ANALYZE)` показывает, сколько раз index-only scan всё-таки сходил в таблицу?
?
`Heap Fetches: N`

Какой процесс обычно устанавливает бит all-visible в карте видимости?
?
Очистка: `VACUUM`, в том числе автоочистка.

Что происходит с битом all-visible, когда на странице меняется хотя бы одна строка?
?
Он сбрасывается; до следующей очистки видимость строк этой страницы снова проверяется по таблице.

Таблицу интенсивно обновляют, автоочистка отстаёт. Что происходит с index-only scan по ней?
?
Он вырождается в обычный индексный доступ: биты all-visible сброшены, растёт `Heap Fetches`.
↳ Лечение: очистка (настроить автоочистку или выполнить `VACUUM`).

Карта видимости хранит на каждую страницу таблицы ==два;;сколько?== бита: all-visible и all-frozen.
```

Notice: the old card's content survives (card 2), but now it is anchored by its cause (card 1),
its observable symptom (card 3), its maintenance (cards 4–5), and an applied scenario (card 6).

## 3. Workflow (Claude Code)

### Step 1: Discover the vault setup
- Find the vault root (the directory containing `.obsidian/`).
- Read `.obsidian/plugins/obsidian-spaced-repetition/data.json` if it exists. It overrides the
  defaults: separators, whether `==highlight==` / `**bold**` / `{{curly}}` are clozes, the
  multi-line end marker, deck tags, folder-as-deck mode, algorithm. Obey what you find.
- Find existing card files for this book (grep for the deck tag or the book title). Match their
  conventions (language, deck-tag path, file layout, heading style) unless those conventions
  are what the user asked you to fix.
- Card language: use the language of the user's existing cards (this user writes in Russian).
  Keep identifiers in English inside backticks: GUCs, functions, views, columns, plan nodes,
  `EXPLAIN` tokens. When the book's Russian term differs from the English docs term, it helps to
  give the English one once in parentheses: «бит полной видимости (all-visible)».

### Step 2: Get the source text
- Write cards from the actual text the user is studying, not from memory. If the book PDF is in
  the vault, extract the chapter: `pdftotext -layout -f <first> -l <last> book.pdf -`.
  (The Russian edition «PostgreSQL 18 изнутри» is free from postgrespro.ru.)
- Use the book's real chapter/section titles for headings. Never invent page numbers.
- If the source is missing, ask for it. If you must rely on general knowledge for a card, don't
  write it silently; list such cards in your report so the user can verify them.

### Step 3: Extract knowledge before writing cards
Read the section and list its knowledge units first (in your head or scratch notes, not in the
vault). Run each unit through `references/interview-filter.md`: drop everything that fails the
interview test or is P3, even when the book spends a page on it. For the surviving core
mechanisms, go through the lenses in §5. Prioritise:
- **High:** mechanisms that explain behaviour you'd see in production; failure modes and
  trade-offs; diagnosis (symptom → cause); defaults that change results; behaviour changes in
  the version the book covers.
- **Skip:** parameter, field, flag, view and function names; byte offsets, struct sizes, bit
  counts; directory layout; SQLSTATE codes; psql switches; exact output of the book's demo
  queries; historical trivia; anything one search away or obvious from another card.
- A dense 25–30 page chapter typically yields 10–25 good cards. Going past ~40 means trivia or
  enumerations sneaking in.

### Step 4: Write the cards (rules in §4–§6)

### Step 5: Lint and self-review
```bash
python3 <skill-dir>/scripts/lint_cards.py <card-file-or-dir> --vault <vault-root> --dump
```
Fix every ERROR (these are cards the plugin will lose or split wrongly). Review each WARN and
either fix it or consciously keep it. Read the `--dump` output: it is exactly what the plugin
will show on each side. Then run the checklist in §8.

### Step 6: Save and report
- One file per chapter, e.g. `PostgreSQL 18 Internals/Cards/<NN> <chapter title>.md` (number and
  title from the book's TOC), with the deck tag in frontmatter and one `##` heading per book section (the plugin shows
  `Note › Heading` as context on every card, so headings double as source references).
- Append new cards; never reorder or rewrite existing ones unless asked (see §7).
- Report briefly: number of cards added per section, anything you skipped and why, cards based on
  general knowledge rather than the source, and lint results.

## 4. Writing the card

### The question
- Ask for exactly one thing, phrased so the *shape* of the answer is obvious: a reason
  («почему»), a condition («в каком случае»), an actor («какой процесс»), a location («где
  увидеть»), a consequence («что произойдёт, если»), a value («значение по умолчанию»).
- Avoid vague stems: «как X помогает Y», «что можно сказать о», «расскажи про», "explain".
- Avoid yes/no questions: they're 50% guessable. Ask for the condition or reason instead.
- Don't leak the answer. If the question names the mechanism, it can't also ask for it.
- Give enough context to be unambiguous out of the flow of the book: say "index-only scan",
  "в PostgreSQL 18", "в B-дереве" when it matters. The heading context helps but don't depend on
  it for disambiguation.
- Keep it short: ideally one line.

### The answer
- **Line 1 is the gradable answer**: short (aim ≤ 15 words), concrete, checkable in seconds.
- **Optional line 2** starting with `↳`: the "because", an example, or the practical implication.
  This is for understanding during review; you don't grade yourself on it.
- No lists of 3+ items on the back. If the content is a list, see §6.
- Stamp version-specific facts: «с PG 18», «до PG 17 включительно», because the book is updated
  every release and your memory should age gracefully.

### Choosing the card type
- **Multi-line basic (`?`): the default.** Safe with code, allows the `↳` line, and immune to the
  `::` cast trap. Use it for almost everything.
- **Single-line (`::`)**: only for short plain-text facts with no code and no `::` anywhere
  in them (see traps below).
- **Cloze (`==…==`)**: for a key term, number or name inside a canonical sentence. One deletion
  per card is best, two at most; add a hint with `;;` when the blank is ambiguous:
  `==два;;сколько?==`. Don't cloze trivial words, and make sure the rest of the sentence doesn't
  give the answer away.
- **Bidirectional (`:::` / `??`)**: only when both directions are genuinely worth recalling:
  term ↔ short definition, GUC ↔ what it controls. Never for explanations (the reverse becomes an
  impossible question).

## 5. Lenses: covering a mechanism from several angles

For each important mechanism, consider these angles and write the ones the source supports and the
user would benefit from (typically 2–3 per core mechanism; secondary facts get none or one):

| Lens | Question pattern (RU) | Example target |
|---|---|---|
| Purpose / why | Зачем нужен X? Почему X, а не Y? | why an index can't judge visibility |
| Mechanism | Как именно X определяет/делает…? (one step) | how a snapshot decides visibility |
| Condition | В каком случае X происходит / не происходит? | when index-only scan reads the heap |
| Actor | Какой процесс/компонент делает X? | who sets / clears all-visible |
| Consequence | Что произойдёт, если…? | lagging autovacuum → heap fetches |
| Diagnose | Симптом в `EXPLAIN` / проде → какая причина? | `Heap Fetches` > 0 → VM не обновлена |
| Trade-off | Когда выбрать X вместо Y? Чем платим? | `fillfactor` < 100 ради HOT |
| Contrast | Чем X отличается от Y (по одному признаку)? | all-visible vs all-frozen |
| Scenario | Short situation → predict the behaviour | long transaction → bloat |
| Version delta | Что изменилось в PG 18? | skip scan, AIO `io_method` |

Scenario and consequence cards are the most valuable for applied understanding; include at least
one per core mechanism. Keep scenarios short enough to read in a few seconds.

## 6. Hard material: lists, sequences, numbers, look-alikes

- **Sets / enumerations** (e.g. "which lock modes conflict with ROW EXCLUSIVE"): don't put the
  whole set on one card. Options, best first: (a) one card per member with a distinguishing cue
  («Какой режим блокировки берёт `UPDATE` на таблицу?»); (b) a count card («Сколько режимов
  табличных блокировок?») plus per-item cards; (c) a cloze sentence per item.
- **Ordered processes** (vacuum phases, WAL recovery, query stages): one card per transition:
  «Что делает очистка сразу после сканирования таблицы?», plus one card for the overall purpose.
  Keep order the same across cards.
- **Numbers and defaults**: card one only if it drives decisions (8 KB page, ~2 KB TOAST
  threshold, default isolation level), and pair it with a "why this value / what happens if
  you change it" card; otherwise the number is noise, skip it.
- **Look-alikes cause interference** (`xmin`/`xmax`, all-visible/all-frozen, VM/FSM,
  index scan / index-only / bitmap scan, `vacuum_freeze_min_age`/`vacuum_freeze_table_age`):
  write an explicit contrast card, and word the individual cards with distinct cues so they don't
  blur together.

### Code and SQL in cards
- Identifiers in inline code: `pg_class.relallvisible`, `VACUUM`, `work_mem`.
- Multi-line SQL goes in a fenced block (at column 0, not inside a list) inside a `?` card. Fenced
  blocks are safe: the parser swallows them whole, including blank lines and `::`.
- Don't make the user memorise whole queries. Ask for the key function/view/column
  («Какой функцией `pageinspect` посмотреть заголовки версий строк?» →
  `heap_page_items(get_raw_page('t', 0))`) or for the observable result.

## 7. Improving existing cards

When the user asks to fix/improve cards:
1. Lint the file first (`--dump`) to see how the plugin currently parses it; some "cards" may not
   exist at all from the plugin's point of view.
2. Classify each card: keep, reword, split, merge, delete. Show the user a short before/after for a
   few representative cards before a bulk rewrite, unless they already asked for the bulk rewrite.
3. **Scheduling comments** (`<!--SR:!2026-10-02,4,270-->`, or the `> [!sr|card-metadata]` callout)
   hold review history. Treat them as opaque:
   - Reworded but same question intent → keep the comment directly after the card.
   - Split or meaning changed → drop it (the new cards start fresh) and say so in the report.
   - Never fabricate or edit the values.
4. Re-lint after editing.

## 8. Plugin-safe formatting: hard rules
(Details and evidence in `references/plugin-syntax.md`.)
- Exactly one blank line between cards; **no blank lines inside a card** (except inside fenced
  code blocks, or if the vault sets an end marker).
- The `?` / `??` separator must be alone on its line.
- **Never write a PostgreSQL cast `x::type` outside backticks**: `::` is the single-line
  separator. Inside a single-line card, even a backticked `::` before the real separator makes the
  plugin silently drop the card. Code → use a `?` card.
- **No HTML comments** (`<!-- … -->`) in card files other than the plugin's own `<!--SR:` lines:
  the parser also skips the line after a comment, and an unclosed comment line swallows the rest
  of the file.
- No `==highlights==` except intended clozes (on by default). Check settings for `**bold**` and
  `{{curly}}` clozes before using bold for emphasis.
- No cards inside bullet lists or indented blocks; fences must start at column 0.
- Blank line between a heading and the first card below it.
- Deck tag in frontmatter (`tags: [flashcards/pg18/indexes]`) or at the top of the file, before
  any card. Hierarchical decks mirror the book: e.g. `flashcards/pg18/mvcc`,
  `flashcards/pg18/wal`, `flashcards/pg18/locks`, `flashcards/pg18/execution`,
  `flashcards/pg18/indexes`.

## 9. Final checklist (per card)
- [ ] Passes the interview test; not P3 (`references/interview-filter.md`).
- [ ] One correct answer; two graders would agree.
- [ ] One retrieval; answerable in ~10 seconds if known.
- [ ] Not yes/no; question doesn't contain the answer.
- [ ] Mechanism cards ask for the cause, not only the conclusion.
- [ ] Line 1 of the answer is short; extras are on a `↳` line.
- [ ] No 3+ item lists on the back.
- [ ] Look-alike concepts have distinct cues or a contrast card.
- [ ] Version-specific facts are stamped.
- [ ] Grounded in the user's source (or flagged in the report).
- [ ] `lint_cards.py` shows 0 errors and the `--dump` sides look right.
