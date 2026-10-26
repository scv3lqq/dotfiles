---
name: tech-note-review
description: Check, fix or extend a Russian technical study note (Obsidian Markdown) about DB/systems internals, e.g. PostgreSQL isolation levels, MVCC, locks, WAL from Rogov's «PostgreSQL 18 изнутри». Verifies facts, recomputes numbers in examples, fixes grammar and formatting, returns the corrected note ready to paste; `extend` also draws an Excalidraw diagram into Visuals/ and embeds it. Use for «правильная ли формулировка?», «проверь заметку», «исправь / допиши раздел», or a pasted note fragment with `######` headings and SQL examples.
argument-hint: "[check|fix|extend] <note text or path>"
---

# Tech note review

Input: a fragment of the user's own note (pasted or a file path). The note is a conspectus, so keep
the user's structure, headings and voice; correct and tighten, don't rewrite into a textbook.

## Mode

- `check`: list problems only.
- `fix` (default): list problems, then the corrected note.
- `extend`: `fix` plus missing material the section needs (mechanism, conditions, error text,
  a worked example, how to avoid or handle the anomaly), limited to the section's angle (see Scope)
  and written to the Density budget, plus one Excalidraw diagram of the section's mechanism
  (see Diagram).

## Density

The note is a conspectus for recall, not a retelling of the book. Target: the user's draft
grown by the essentials, roughly 10 to 25 lines for a section.

- One line per definition or rule; one sentence for the "why", one for its consequence.
- Drop trivia that does not change understanding (side parameters, historical asides,
  "also stored in WAL records").
- Each rule appears once: no prose rule followed by the same rule as a list.
- Worked example: only the command, its output and the final state that prove the rule. Explanations
  go into inline comments (`-- not visible: 809 in xip_list`), one per row; skip setup steps the
  prose already describes, cut output to the columns that matter.
- Before output, reread the note and cut every line whose loss would not hurt recall.

If the whole message is a pasted block and no mode is given, ask once with AskUserQuestion
(`fix` first). If the same session already set a mode for similar fragments, reuse it.

## Scope

A section title alone («TOAST», «Индексы», «Заморозка») is not the topic: the topic is that title
as seen from its chapter. The book returns to the same object several times, each time from a
different side. Example: 3.5 TOAST sits in «Глава 3. Страницы и версии строк», so it is only about
versioning of toast rows (own versions, rows only inserted and deleted, an `UPDATE` that does not
touch the long value reuses the old toast pointer). What TOAST is, strategies, the 2 KB threshold,
compression and `pg_toast` live in 1.1 and do not belong in a 3.5 note.

Before `extend` (and before flagging "missing" material in `check`/`fix`):

1. Pin the location: section number from the note heading, path or the user's words; chapter title.
   No number and the title is ambiguous: ask once.
2. Read the section in the source. Rogov's book: `<vault>/attachments/postgresql_internals-18.pdf`, where `<vault>` is the path in `~/.claude/private/vault` (no such file: ask the user for the PDF once).
   Find the page with `pdftotext -layout -f 5 -l 12 <pdf> -` (Содержание), then extract the section text
   with `pdftotext -f N -l M <pdf> - | sed -n '/^3.5. TOAST/,/^3.6. /p'`; PDF page ≈ book page + 1,
   verify by the running header. Other sources: same idea, locate the section and read it.
3. Extend only with material that serves the chapter's angle: mechanism, conditions, example and
   numbers of *this* section, plus details from the docs that answer the same question. A neighbouring
   section of the same chapter is off-angle too (4.3 «Из чего состоит снимок» lists the snapshot
   fields and which xids it sees; when a row version is visible belongs to 4.2).
4. General background covered elsewhere in the book (margin references like «с. 33» point to it):
   at most a few words inline where the section needs it, never a re-explanation. No cross-reference
   pointers (`см. 1.1`, `см. 4.4`) in the note.
5. Material that is correct but off-angle: don't add it; if it looks important, mention it in one
   line after the problem list as a candidate for another note.

## Diagram (`extend` only)

One diagram that makes the section's mechanism visible: a timeline of two transactions, page and
tuple layout, a snapshot against the xid axis, a state transition. It shows what the prose can't
show at a glance; a picture that only restates a list is skipped, say so in one line.

1. Draw it with skill `excalidraw-diagram` (render-view-fix loop in the scratchpad, mandatory).
   Labels in Russian like the note, identifiers and SQL as in the note; numbers match the worked
   example exactly (same xids, same values).
2. Save with its Obsidian target (`<vault>`: the path in `~/.claude/private/vault`): `to_obsidian.py <in.excalidraw>
   "<vault>/Visuals/<EN Name>.excalidraw.md" "<RU alias>"`. EN Name names the
   mechanism (`Snapshot xip_list Visibility`); if the file exists, pick another name, never overwrite.
3. Embed `![[<EN Name>.excalidraw]]` on its own line inside the corrected note, right after the
   paragraph or example it explains. The note goes into a daily note, the embed resolves vault-wide.
4. The fragment already embeds a hand drawing of the same thing: don't draw a duplicate, check the
   drawing's text against the note instead (`Visuals/` files keep labels under `## Text Elements`).

## What to check

1. **Facts.** Every claim against current PostgreSQL behavior (default: latest major, PG 18).
   Typical traps:
   - conditions of an error (same row vs different rows, when it fires: at statement, at COMMIT,
     after waiting for a lock, what happens if the other transaction rolls back);
   - exact error text and SQLSTATE (`40001` for serialization failures, retry the whole
     transaction);
   - scope of a guarantee: what the level prevents vs what still passes (write skew and read-only
     anomaly pass on Repeatable Read, only Serializable catches them);
   - Read Committed `UPDATE ... SET x = x - n` does not lose updates; lost update needs
     read-modify-write in the application;
   - option combinations that only work together (`DEFERRABLE` needs `SERIALIZABLE READ ONLY`).
   Unsure about a detail: check docs via context7 or the PostgreSQL docs, don't guess.
2. **Examples.** Recompute every number in comments (`-- 500`) by hand. Comments show the row value
   after the statement, not a total, unless labeled. The example must actually exercise the stated
   rule (a balance that is meant to go negative must go negative). Add missing `COMMIT` and the final
   state when the point of the example is "both commit, invariant broken" or "second one fails".
   Filter by the entity the rule is about (`WHERE client = 'Bob'`).
3. **Logic of the explanation.** The note must say *why* (dependency, snapshot, lock), not only
   *what*. Vague pronouns («он», «одна ещё не выполнилась») get replaced with the exact object.
4. **Russian.** Typos, missing commas (before «который», after introductory «Другими словами»,
   in «если ..., то ...»), extra words, calques («in Postgresql», «уровни изоляций»).
5. **Formatting.**
   - `PostgreSQL` spelling; English terms in bold on first use (**Repeatable Read**, **write skew**).
   - Code fences: `sql` (Prism has no `postgresql`), plain fence for table rows and error output.
   - SQL keywords upper case, identifiers lower case, consistent with the rest of the note.
   - Table rows get a header line (`id|client|amount`).
   - Keep the note's heading levels and list nesting (indented fences inside list items).
   - No em dash anywhere.

## Output

1. Short numbered list of problems: bold label + one or two sentences. Facts first, then examples,
   then language and formatting grouped into one item. In `extend`, list what was added in one
   item, not one item per addition, and name the diagram file there.
2. The corrected note in a single fenced block the user can copy as is. The note contains ``` fences,
   so wrap it in a four-backtick ````markdown fence. Never output the note as a `>` quote (the
   terminal renders it with a ▎ bar that gets copied).

No preamble, no summary after the block. Reply in Russian.
