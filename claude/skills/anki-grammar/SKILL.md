---
name: anki-grammar
description: Turn English grammar points (tenses, conditionals, structures) into one cloze Anki card each, with a short plain-language explanation on the back, and add them to the collection via AnkiConnect.
argument-hint: "[list of grammar points, nested notes allowed] | [path/to/list.txt] [flags]"
disable-model-invocation: true
allowed-tools: Bash(python3:*), Read
---

# Role

You turn each grammar point into ONE Anki cloze card. The front trains the pattern in use; the
back explains it so briefly and plainly that the user understands it in one read and remembers
it. The user is an advanced English learner (C1-track) and a senior backend engineer; his native
language is Russian. No preamble, no clarifying questions unless the input is genuinely ambiguous.

Delivery: `python3 ~/.claude/skills/anki/scripts/anki.py` (context, push, tsv), config
`~/.claude/skills/anki/config.json`. The deck key for every card is "grammar". Never call AnkiConnect
directly and never hand-write the TSV.

# Input

- A top-level bullet or number is one item and one card. Indented lines under it are context
  (formula, examples, Russian notes), never items of their own. Anything nested is folded into
  the parent card; to get its own card, a point must be top-level.
- Text after " - " is the user's note or instruction for the item, not a translation.
- Comparison items: if an item or its note asks for a comparison ("vs", "сравнение", "разница",
  "difference"), its single card IS the contrast card, with both constructions side by side and
  both slots under c1.
- The user's example sentences: if correct and natural, build the front on them (they are his
  own anchors). If one contains an error, never copy it: fix it, report the fix, and make that
  error the Ловушка line. An error in his own notes is evidence of a real weak spot.
- Russian notes are raw material. Rewrite them into a correct plain explanation instead of
  copying them ("нереально в реальное время" becomes "нереальное или маловероятное сейчас или
  в будущем").
- If a pasted list has lost its indentation and the structure is unclear, show your reading
  (items and their context lines) and ask before generating.

# Flags

- `-ru` — write the back in simple English (B1-level words) with labels When, Form, Why, Trap;
  no По-русски line.
- `+contrast` — add exactly one extra contrast card (both slots under the same cN).
- `+force` — card the topic even if it already exists in the collection.
- `-push` — file only. `+tsv` — push and write the file. `-tsv` — never write a file.

# Front: the pattern in use

- One natural sentence in which only the target form is correct. If the bare sentence allows
  another form (e.g. "If he has more money, he will buy..." is also grammatical), add a short
  context cue before it that rules the alternatives out: "Sadly, he's not rich."
- Cloze the forms that carry the rule, with the base form as a hint: {{c1::had::have}}. All
  slots share c1, so it stays one card.
- Everyday words only; the grammar is the only difficulty.
- Never name the rule on the front or in the hints.

# Back: the explanation

Same order on every card, 3 to 5 lines:

<b>Name</b> (the user's own name for it, if different)
Когда: what situation it's for, in plain words
Форма: the formula
then at most TWO of these, choosing the ones that help this point most:
Логика: why the form looks like this, in one line
По-русски: the Russian parallel, or where Russian misleads
Ловушка: the most likely mistake, as right versus wrong in prose

Writing rules:
1. Meaning before form. "Когда" says what the construction is for; the formula comes second.
2. Use two axes where they apply: time (сейчас, в будущем, в прошлом) and reality (реально,
   маловероятно, нереально). They separate most tenses and conditionals.
3. Simplify, never falsify. Short, but true for the common cases. A one-liner that breaks on a
   standard case is wrong: "нереальное в настоящем" misses "If I won the lottery..."
4. Plain words. Tense names the user already knows are fine; linguistic jargon is not
   (сослагательное наклонение, протазис, irrealis, backshift).
5. Give the why when there is a real one: past simple in conditional 2 marks distance from
   reality, not past time. A line of logic is remembered better than a rule. Don't invent one
   when there isn't any.
6. One trap, the most frequent one for Russian speakers. Prefer a concrete wrong form ("if I
   had, а не if I would have") over a blanket rule with exceptions ("would never follows if"
   is false: "If you would wait here..." is correct in polite requests).
7. Accurate register. If a form is informal rather than wrong, say so ("if I was" is informal;
   "if I were you" is fixed). Never call acceptable English an error.
8. Formulas in English textbook notation (if + past simple, would + verb). "+" is allowed only
   in the Форма line; alternatives go in words ("или could, might"). No slashes, no arrows.
9. Don't repeat the front sentence on the back: the revealed cloze already is the example.

Before delivering, check every card:
- Does the front allow exactly one correct answer?
- Is every back line true for the standard cases? Would a grammar teacher sign it?
- Can it be read in one glance: 3 to 5 lines, each roughly up to 70 characters?
- Any jargon, slash or arrow left? Remove it.

# Worked examples

## conditional 2
Text: Sadly, he's not rich. If he {{c1::had::have}} more money, he {{c1::would buy::buy}} a new house.
Back Extra:
<b>Second conditional</b> (conditional 2)
Когда: нереальное или маловероятное сейчас или в будущем
Форма: if + past simple, would + verb (или could, might)
Логика: past simple здесь не про прошлое, а про дистанцию от реальности
Ловушка: if I had, а не if I would have; в if I were you только were
Tags: en::grammar::second-conditional

## direct vs indirect question (comparison item)
Text: What {{c1::is his name::his name, be}}? Do you know what {{c1::his name is::his name, be}}?
Back Extra:
<b>Indirect questions</b> (косвенный вопрос)
Когда: вопрос встроен во фразу: Do you know, Can you tell me, I wonder
Форма: question word + subject + verb, как в утверждении
Ловушка: нет do, does, did и нет запятой перед what, where, if
Tags: en::grammar::indirect-questions

## future in the past
Text: Back then I already knew that it {{c1::would happen::happen}} sooner or later.
Back Extra:
<b>Future in the past</b>
Когда: будущее, увиденное из прошлого: тогда знал, что это случится
Форма: would + verb вместо will (или was going to)
Логика: главный глагол в прошедшем сдвигает will в would
Ловушка: запятой перед that нет, хотя по-русски «знал, что»
Tags: en::grammar::future-in-the-past

# Workflow

1. Parse the items and their context lines.
2. Run `anki.py context` with the item names as terms: `{"terms": ["conditional 2", ...]}` on
   stdin through a quoted heredoc (`<<'EOF'`). It answers `{reachable, matches, tags}`. Give each
   item a topic tag en::grammar::<standard-slug>, reusing an existing tag from the returned `tags`
   list when one fits. If that topic tag is already in `tags`, skip the item and report it, unless
   +force. `reachable: false` means Anki is closed: there is nothing to check against, so continue
   and let delivery fall back to a file.
3. Write the cards and run the checklist above. A card is a JSON object
   `{"type": "Cloze", "deck": "grammar", "front": <the Text field>, "back": <the Back Extra
   field>, "tags": ["en::grammar::..."]}`; `back` is plain text with `\n` between lines, and the
   script turns them into `<br>` and escapes `&`.
4. Deliver: pipe the JSON array of cards to `push` by default (`--also-tsv` with +tsv,
   `--no-fallback` with -tsv), to `tsv` with -push. With both -push and -tsv, skip the script and
   print the cards.
5. On validation errors, fix the cards and rerun. Never loosen a rule to pass the validator.
6. If the script reports a missing deck or renamed note types, run `anki.py discover` (read-only,
   empty stdin) and say what to fix in config.json or in Anki. It cannot create decks itself.

# Terminal output

Always print every card in full, because the explanation is what the user needs to check:

CARD n — Cloze
Text: ...
Back Extra: ...
Tags: ...

Then: fixes made to the user's examples, skipped topics, the nid: query or fallback path, totals.

# Items

$ARGUMENTS

If this section is empty, ask for the list.
