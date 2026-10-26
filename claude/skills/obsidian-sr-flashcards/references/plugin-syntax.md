# Obsidian Spaced Repetition plugin: syntax and parser traps

Plugin: `obsidian-spaced-repetition` by st3v3nmw (docs: stephenmwangi.com/obsidian-spaced-repetition).
Behaviour below was checked against `src/parser.ts` and `src/data/settings.ts` on the master
branch (plugin v1.15.x, clozecraft 0.4). `scripts/lint_cards.py` contains a line-by-line port of
that parser, so when in doubt, run it with `--dump`.

## Contents
1. Settings file
2. Card types
3. Clozes
4. Decks
5. Scheduling data
6. Parser traps (verified)
7. Recommended file template

---

## 1. Settings file

`<vault>/.obsidian/plugins/obsidian-spaced-repetition/data.json` → `settings` object.
Defaults (used when the file or a key is missing):

| Key | Default | Meaning |
|---|---|---|
| `flashcardTags` | `["#flashcards"]` | tags that mark decks; nested tags are subdecks |
| `convertFoldersToDecks` | `false` | folder path becomes deck path instead of tags |
| `singleLineCardSeparator` | `::` | |
| `singleLineReversedCardSeparator` | `:::` | |
| `multilineCardSeparator` | `?` | |
| `multilineReversedCardSeparator` | `??` | |
| `multilineCardEndMarker` | `""` | empty ⇒ a blank line ends a multi-line/cloze card |
| `convertHighlightsToClozes` | `true` | `==text==` is a cloze |
| `convertBoldTextToClozes` | `false` | `**text**` is a cloze |
| `convertCurlyBracketsToClozes` | `false` | `{{text}}` is a cloze |
| `clozePatterns` | `["==[123;;]answer[;;hint]=="]` | custom patterns override the three toggles |
| `cardCommentOnSameLine` | `false` | where scheduling comments go for single-line cards |
| `useCalloutsForSchedulingComments` | `false` | callout instead of HTML comment |
| `algorithm` | SM-2 variant (FSRS optional) | |

Always read the actual file; users change separators and cloze toggles.

## 2. Card types

Single-line basic: one line, `::` between sides:
```
Какая структура хранит свободное место на страницах таблицы?::Карта свободного пространства (FSM)
```

Single-line bidirectional: `:::`, creates two sibling cards (A→B and B→A):
```
`maintenance_work_mem`:::Память для служебных операций (VACUUM, CREATE INDEX)
```

Multi-line basic: `?` alone on a line; question above, answer below; a blank line ends it:
```
Почему очистка не может удалить версию строки, если в системе есть давняя активная транзакция?
?
Эта версия может быть видна снимку той транзакции: горизонт очистки не сдвигается.
↳ Отсюда раздувание таблиц при долгих транзакциях.
```

Multi-line bidirectional: `??` alone on a line; two sibling cards.

Fenced code inside a multi-line card is fine (fence must start at column 0):
````
Что вернёт второй запрос, если первый выполнен в другом сеансе без COMMIT?
```sql
-- сеанс 1
BEGIN; UPDATE t SET n = 2 WHERE id = 1;
-- сеанс 2
SELECT n FROM t WHERE id = 1;
```
?
Старое значение (1): незафиксированное изменение не видно чужим снимкам.
````

## 3. Clozes

Default delimiter `==…==`. Each deletion creates a sibling card that hides that deletion only.

- Simple: `==answer==`
- With hint (shown instead of `[...]`): `==answer;;hint==` → front shows `[hint]`
- Grouped (hidden together on one card): `==1;;answer==`, `==1;;other==`, `==2;;third==`
- Do **not** mix numbered and un-numbered deletions in one card (plugin can't mix cloze types).
- A cloze card ends at the next blank line; the whole paragraph is the card.

Examples:
```
Карта видимости хранит на каждую страницу таблицы ==два;;сколько?== бита: all-visible и all-frozen.

==1;;xmin== и ==1;;xmax== хранятся в заголовке версии строки, а ==2;;t_ctid== ссылается на следующую версию.
```
The second one produces 2 cards: one hides xmin+xmax, the other hides t_ctid.

## 4. Decks

- Tag in frontmatter applies to the whole file: `tags: [flashcards/pg18/mvcc]` (no `#` in YAML).
- An inline tag line (`#flashcards/pg18/mvcc`) applies to all cards after it until the next tag.
- A tag at the start of a card's first line applies to that card only.
- Multiple decks: several tags on the same line, space-separated.
- If `convertFoldersToDecks` is on, folders define decks and tags aren't needed.

## 5. Scheduling data

After the first review the plugin writes review state right after the card:
```
Question
?
Answer
<!--SR:!2026-10-02,4,270-->
```
(due date, interval in days, ease: SM-2; FSRS stores a different payload in the same place.)
With `useCalloutsForSchedulingComments` it writes a `> [!sr|card-metadata]` callout instead.
Treat both as opaque. Keep them attached (no blank line) to the card they belong to; delete them
only when the card's meaning changes; never invent them.

## 6. Parser traps (verified)

Each of these was reproduced by running the plugin's parser on test input.

| # | Input | What the plugin does | Fix |
|---|---|---|---|
| 1 | `What does SELECT '1'::int return?` then `?` / answer | Treats the cast `::` as a single-line separator: front `What does SELECT '1'`, back `int return?`; the real answer becomes orphan text | Put code in backticks inside a `?` card, or write `CAST('1' AS int)` |
| 2 | `` Result of `'1'::int`?::1 `` | Only the **first** `::` is checked; it's inside backticks, so the line is not a card at all. Card silently lost | Never have `::` in a single-line card other than the separator; use a `?` card |
| 3 | `<!-- source: ch.4 -->` followed directly by a card line | The comment line **and the next line** are skipped | No HTML comments in card files |
| 4 | Card, then `<!-- note -->` on the next line, then blank, then another card | The blank line that ended the first card is skipped; the first card is merged into the next and lost | Same |
| 5 | `<!--` on a line without `-->` (multi-line comment) | Everything to the **end of the file** is skipped | Same |
| 6 | Blank line inside an answer | Card ends at the blank line; the rest is orphan text | Keep answers contiguous, or configure `multilineCardEndMarker` (e.g. `+++`) and end every card with it |
| 7 | `==emphasis==` or (if enabled) `**bold**` in a normal card or prose | Paragraph becomes a cloze card | Don't use them for emphasis |
| 8 | Heading line directly above a card (no blank line) | Heading becomes part of the card's front | Blank line after headings |
| 9 | Code fence indented or inside a list item | Not recognised as code; `?`/`::` inside it are parsed as separators | Fences at column 0, no cards inside lists |
| 10 | Mixed `==1;;x==` and `==y==` in one paragraph | Invalid cloze typing | Number all deletions or none |

Safe:
- `::` inside inline code in a **multi-line** card: ignored by the separator check.
- `::`, `?`, blank lines inside a fenced code block: the whole block is consumed as text.
- A question line that simply ends with `?`: only a line that is exactly `?` is a separator.

## 7. Recommended file template

```markdown
---
tags: [flashcards/pg18/indexes]
book: "PostgreSQL 18 изнутри"
chapter: "<NN> <chapter title from TOC>"
---
# <NN> <chapter title>

## <section title from the book>

<card>

<card>

## <next section>

<card>
```
The plugin shows `Note title › Heading › Subheading` on each card, so section headings act as both
context and source reference. Be aware that a heading can give away an answer ("Карта
видимости" above «Какая структура хранит бит all-visible?»); phrase such questions differently or
accept the heading as a deliberate cue.
