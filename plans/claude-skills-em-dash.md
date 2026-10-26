# Remove em dashes from the moved Claude skills

## Goal

The skills moved into `claude/skills/` by `plans/claude-home-in-dotfiles.md`
still carry em dashes (U+2014) from before the style rule. Replace every one of
them in those files without changing meaning, behavior or line count.

## Current behavior

107 lines with an em dash in nine files (counts are lines, `grep -c`):

| File (under `claude/skills/`) | Lines |
| --- | --- |
| `anki/SKILL.md` | 29 |
| `anki/scripts/anki.py` | 1 |
| `anki-grammar/SKILL.md` | 5 |
| `refactor-proof/SKILL.md` | 3 |
| `retro/SKILL.md` | 3 |
| `obsidian-sr-flashcards/SKILL.md` | 33 |
| `obsidian-sr-flashcards/references/pg-internals-examples.md` | 22 |
| `obsidian-sr-flashcards/references/plugin-syntax.md` | 7 |
| `obsidian-sr-flashcards/scripts/lint_cards.py` | 4 |

In both scripts the dash sits only inside message strings, never in logic.

## Acceptance criteria

- AC1: `grep -r -c $'\xe2\x80\x94'` over the nine files prints `0` for each.
- AC2: for each file, `git diff --numstat main...HEAD -- <file>` shows added
  = deleted = its line count from the table (no line added, removed or reflowed).
- AC3: for each file, every deleted line held an em dash:
  `git diff -U0 main...HEAD -- <file> | grep '^-' | grep -v '^---' | grep -c -v $'\xe2\x80\x94'` prints `0`.
- AC4: `python3 ~/dotfiles/claude/skills/anki/scripts/anki.py --selftest` prints
  a line starting `SELFTEST OK` and exits 0.
- AC5: G-PY passes, and `lint_cards.py` on the G-LINT sample exits 0 with
  `0 error(s)`.
- AC6: the reviewer confirms every rewritten line keeps its meaning (SD-RULES).

## Gates

G-PY:

```bash
for f in ~/dotfiles/claude/skills/anki/scripts/anki.py ~/dotfiles/claude/skills/obsidian-sr-flashcards/scripts/lint_cards.py; do python3 -c 'import ast, sys; ast.parse(open(sys.argv[1]).read())' "$f" && echo "ok $f"; done
```

G-LINT:

```bash
T=$(mktemp -d); printf -- '---\ntags: flashcards\n---\n\nWhat does X do?\n?\nIt does Y.\n' > "$T/c.md"
python3 ~/dotfiles/claude/skills/obsidian-sr-flashcards/scripts/lint_cards.py "$T/c.md" | tail -1
```

Per-file task gate: AC1, AC2 and AC3 run against the working tree instead of
`main...HEAD`, before the commit:
`grep -c $'\xe2\x80\x94' <file>` prints `0`;
`git -C ~/dotfiles diff --numstat -- <file>` shows added = deleted = N;
`git -C ~/dotfiles diff -U0 -- <file> | grep '^-' | grep -v '^---' | grep -c -v $'\xe2\x80\x94'` prints `0`.

## Shared definitions

### SD-RULES (how to replace one em dash)

Pick the first that keeps the sentence natural; the line must read as if it
was written without a dash. Below, `<dash>` stands for the em dash character,
which this plan never types:

1. Label or heading before an explanation (`` `x` <dash> does y ``,
   `Part I <dash> Isolation`, `Worked examples <dash> PostgreSQL`): a colon,
   `` `x`: does y ``.
2. An explanation, result or consequence that follows a clause: a colon.
3. An aside inside a sentence (a pair of dashes): parentheses, or commas when
   the aside is short.
4. Two independent clauses: a semicolon, or a period and a capital letter when
   it stays on the same line.
5. Russian text: the same rules; a definition or copula `X <dash> это Y` /
   `X <dash> Y` becomes `X: Y` or `X это Y`. Keep the Russian wording otherwise, keep `«»`.
6. A dash that the text names as an accepted INPUT character (in
   `anki/SKILL.md` the line that starts `Parsing: item = text before the first`
   lists the separators the parser accepts): do not drop it and do not type it;
   name it in words: replace the backticked `` ` <dash> ` `` there with
   `an em dash (U+2014)`.
7. Code: only message strings carry a dash; use `: ` or `; ` so the message
   stays grammatical, and keep string concatenation and f-string fields intact.

Never: change an en dash (U+2013), a hyphen, `--` or anything without an em
dash; join, split or rewrap lines; touch a line without an em dash; type an em
dash anywhere (the PostToolUse hook rejects it; an Edit `old_string` that
contains one is fine).

## Tasks

Each task: Edit only the lines with an em dash in its files, run the per-file
task gate for each file, do not commit (the orchestrator commits by pathspec).
Implementers run with `model: sonnet` (every replacement is a judgment call).

- T1: `claude/skills/anki/SKILL.md` (29), `claude/skills/anki/scripts/anki.py`
  (1, line 234: the message continues the f-string above it, whose last string
  ends with a space, so the new string is `"(insert a space before the closing
  braces)"`; a leading colon would read `\\) : insert`). Extra gate: AC4.
- T2: `claude/skills/anki-grammar/SKILL.md` (5), `claude/skills/refactor-proof/SKILL.md`
  (3), `claude/skills/retro/SKILL.md` (3).
- T3: `claude/skills/obsidian-sr-flashcards/SKILL.md` (33). The YAML
  `description:` on line 3 has none; keep it untouched.
- T4: `claude/skills/obsidian-sr-flashcards/references/pg-internals-examples.md`
  (22), `claude/skills/obsidian-sr-flashcards/references/plugin-syntax.md` (7).
  Card examples keep their card syntax (`::`, `?`, `==cloze==`, `{{c1::...}}`)
  byte for byte around the replaced dash.
- T5: `claude/skills/obsidian-sr-flashcards/scripts/lint_cards.py` (4, lines
  316, 324, 327, 358: warning texts). Extra gates: G-PY, G-LINT.

Waves: T1..T5 in parallel (disjoint files). Commit subjects:
T1 `style(claude): drop em dashes from the anki skill`,
T2 `style(claude): drop em dashes from anki-grammar, refactor-proof, retro`,
T3 `style(claude): drop em dashes from the flashcards skill`,
T4 `style(claude): drop em dashes from the flashcards references`,
T5 `style(claude): drop em dashes from lint_cards messages`.

## Seams

None: no symbol, file or format is shared between tasks; SD-RULES is the one
shared definition.

## Not doing

- Em dashes outside the nine files (`claude/skills/feature/SKILL.md`,
  `claude/agents/*.md`, older docs).
- Any other wording, typo or formatting fix in the touched lines.
- The history rewrite that follows this plan (personal paths in old commits):
  it is a separate step done with the `git-history-rewrite` skill.
