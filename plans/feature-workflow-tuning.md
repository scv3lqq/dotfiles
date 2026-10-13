# Feature workflow tuning

## Goal

Apply the lessons of the first end-to-end `/feature` run (sandbox `~/dev/feature-sandbox`,
branch `feat/word-frequency-cli`, 2026-10-06):

- implementer moves from Claude Haiku 4.5 to Claude Sonnet 5.5 at `medium` effort;
- the acceptance validator stays fast (time budget, one batched evidence run);
- the parallel-wave mechanics that the orchestrator improvised in that run become written
  rules (shared-type T0 task, commit per wave, foreign gate failures, one-file red-gate fix).

Non-goals: no change to reviewer or validator models, concurrency cap (12), iteration
limit (5), report formats, or the sandbox repo.

## Current behavior

`/feature` (`~/.claude/commands/feature.md`) plans in the main session, dispatches one
`implementer` per single-file task (Haiku 4.5, `effort: high`, which Haiku ignores: it has
no effort parameter), reviews each task with `plan-reviewer` (Sonnet 5.5, medium) and
decides with one `acceptance-validator` (Opus 5.5, xhigh).

Observed in the run:

- Haiku drifted from the report format and needed 88 s / 32 tool calls for a 4-line fix.
- The validator took 6.2 min (longer than all 10 implementation tasks together) because it
  ran 200-iteration mutation loops for a MINOR finding. A budget paragraph was already
  added to `acceptance-validator.md` after the run; it is unverified.
- Parallel tasks in one Go package only compiled because shared types were split into a
  solo T0 task; a gate failing on a sibling's half-written file needed an ad-hoc plan rule
  (SD3); waves were committed one by one; a red lint gate was fixed through SendMessage,
  which `feature.md` only allows for PASS findings.

## Target behavior

Same workflow, with Sonnet 5.5 implementers and the rules above written down. No text
mentions Haiku as the implementer anywhere.

## Relevant files

| Path | Why | Action |
|---|---|---|
| `~/.claude/agents/implementer.md` | implementer model, effort, hard rules | edit |
| `~/.claude/commands/feature.md` | workflow phases | edit |
| `~/.claude/agents/acceptance-validator.md` | validator budget | edit (verify + 1 sentence) |
| `$HOME/dotfiles/CLAUDE.md` | role line names the implementer model | edit line 8 |
| `~/.claude/agents/plan-reviewer.md` | context only | read-only |
| `~/.claude/CLAUDE.md` | its line "effort does not exist on Haiku 4.5" stays true | do not touch |

`~/.claude/agents` and `~/.claude/commands` are not in git.

## Constraints

- Never write an em dash (U+2014) in new text; a hook rejects it. Existing lines that
  already contain one stay as they are unless a step replaces them.
- Edit with the Edit tool, one anchor per edit; do not rewrite whole files.
- Do not touch `nvim/lazy-lock.json`, Karabiner backups, or anything outside the four files.
- `dotfiles/CLAUDE.md` already has uncommitted changes: edit only line 8, do not commit.

## Implementation steps

### T0 (implementer): backups

```sh
ts=$(date +%Y%m%d-%H%M%S)
for f in ~/.claude/agents/implementer.md ~/.claude/agents/acceptance-validator.md ~/.claude/commands/feature.md; do
  cp "$f" ~/.claude/backups/"$(basename "$f")".$ts
done
cp $HOME/dotfiles/CLAUDE.md ~/.claude/backups/dotfiles-CLAUDE.md.$ts
```

### T1 (implementer): implementer to Sonnet 5.5 medium, all four files

1. `~/.claude/agents/implementer.md` frontmatter:
   - `model: claude-haiku-4-5-20251001` becomes `model: claude-sonnet-5-5`
   - `effort: high` becomes `effort: medium`
2. `~/.claude/commands/feature.md` line 56: replace the phrase
   `Implementers run on Haiku and read only` with `Implementers read only`. Keep the rest
   of the paragraph (the per-task spec list) unchanged: it still saves context.
3. `~/.claude/commands/feature.md` line 96: replace the substring
   `(haiku → sonnet, sonnet ⇄ opus)` with `(sonnet ⇄ opus)`.
4. `$HOME/dotfiles/CLAUDE.md` line 8: replace the substring
   ``Claude Haiku 4.5 (`claude-haiku-4-5-20251001`)`` with
   ``Claude Sonnet 5.5 (`claude-sonnet-5-5`), medium effort``.

### T2 (implementer): validator budget

In `~/.claude/agents/acceptance-validator.md`, confirm that this paragraph exists right
after check 4 ("Per-task findings"):

```text
Budget: you are the slowest step of the loop, so spend time only where it changes the
verdict. One run per criterion is evidence. Mutation tests, repeated runs and timing probes
only to rule on a CRITICAL/MAJOR finding or a criterion you cannot otherwise decide, and at
most 20 runs each; a MINOR finding is ruled by reading.
```

If missing, insert it there verbatim. Then append one sentence to the end of that paragraph
(same paragraph, new line):

```text
Collect the acceptance evidence with one Bash script that runs every criterion and prints
command, exit code and output per criterion, instead of one call per criterion.
```

Do not change the model (`claude-opus-5-5`) or effort (`xhigh`).

### T3 (implementer): written rules for parallel waves

1. `~/.claude/agents/implementer.md`, section "Hard rules": insert a new bullet directly
   after the bullet that ends with ``use `git show <ref>:<path>`.``:

   ```text
   - Other agents may be editing sibling files of the same package while your gates run.
     A gate failure whose every error points at a file outside your scope is not yours:
     do not edit that file and do not retry in a loop; list it under **Out of scope** and
     count your gate as PASS. A failure in a file of your scope is always yours.
   ```

2. `~/.claude/commands/feature.md`, phase 2: insert a new paragraph directly after the
   line `names, config keys) live once in Shared definitions.`:

   ```text
   When parallel tasks share one compile unit (a Go package, a TS module), put the shared
   types, constants and errors in a T0 task that runs alone and is committed before the
   parallel wave, so every sibling file compiles against them while the others are written.
   ```

3. `~/.claude/commands/feature.md`, phase 3: insert a new paragraph directly after the
   line that ends with `misplaces context-free hunks; costs a reset + redo).`:

   ```text
   Parallel tasks run in waves of ready tasks. After each wave, run the full Gates and commit
   the wave's files by explicit pathspec before dispatching the next wave.
   ```

4. `~/.claude/commands/feature.md`, phase 4: insert a new paragraph directly after the
   line that ends with `full code review is phase 5.`:

   ```text
   Exception to "go straight to phase 6": a red gate whose cause is obvious and confined to
   one task's file goes to that still-alive implementer via SendMessage with the exact fix
   and its task gates; rerun the full Gates afterwards. It does not count as an iteration.
   ```

## Tests / verification

```sh
grep -n -E '^(model|effort):' ~/.claude/agents/implementer.md ~/.claude/agents/acceptance-validator.md
# expect: implementer claude-sonnet-5-5 / medium; validator claude-opus-5-5 / xhigh

grep -n -i haiku ~/.claude/agents/implementer.md ~/.claude/commands/feature.md $HOME/dotfiles/CLAUDE.md
# expect: no output

grep -c -E 'Collect the acceptance evidence|Budget: you are the slowest' ~/.claude/agents/acceptance-validator.md
# expect: 2

grep -c -E 'not yours:|one compile unit|waves of ready tasks|Exception to "go straight' \
  ~/.claude/agents/implementer.md ~/.claude/commands/feature.md
# expect: implementer.md:1, feature.md:3
```

No new em dash in added lines (compare with the T0 backups; replace `<ts>`):

```sh
for f in implementer.md acceptance-validator.md feature.md; do
  src=$( [ "$f" = feature.md ] && echo ~/.claude/commands/$f || echo ~/.claude/agents/$f )
  diff ~/.claude/backups/$f.<ts> "$src" | grep '^>' | python3 -c "import sys; print('$f', sum(l.count('—') for l in sys.stdin))"
done
# expect: 0 for each file
```

Smoke run (by the user, in a NEW Claude Code session, because agent definitions load at
session start): in `~/dev/feature-sandbox` on a fresh branch from `feat/word-frequency-cli`,
run `/feature add a -min flag to textstats that drops words seen fewer than N times`.
Expect: implementer reports start with `## T<n>`, the validator finishes in about 2 minutes
or less, `just check` is green.

## Edge cases

- A file differs from the line numbers above (edited in parallel): locate the anchor text,
  not the line number; if an anchor is missing, stop and report instead of guessing.
- Backups dir missing: `mkdir -p ~/.claude/backups` first.
- Running in the same session that loaded the old agents: edits are on disk but take
  effect only in a new session.

## Rollback

Copy the T0 backups back over the four files.

## Acceptance criteria

- [ ] implementer frontmatter is `claude-sonnet-5-5` / `medium`.
- [ ] No "haiku" left in `implementer.md`, `feature.md`, `dotfiles/CLAUDE.md`.
- [ ] Validator has the budget paragraph plus the one-script sentence; model and effort unchanged.
- [ ] The four rule texts of T3 are present at their anchors, verbatim.
- [ ] No em dash in any added line.
- [ ] Nothing else changed in the four files (check with `diff` against the backups).

## Notes for reviewer

- Expected diff: 2 frontmatter lines, 3 phrase replacements, 1 sentence, 4 inserted
  paragraphs/bullets. Anything larger is scope creep.
- Risk: the T3.4 exception loosens "red is a fact"; it is limited to one obvious one-file
  cause, and the full Gates still rerun.
