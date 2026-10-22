# Feature workflow: review and test ports

## Goal

Port into the four files that run `/feature` the review and test mechanisms it lacks,
taken from the official `pr-review-toolkit` and `code-review` plugins and from
`obra/superpowers`. No plugin or community skill set gets installed: the ideas are
ported, the agents and their formats stay ours.

## Current behavior

A test task runs after its source task, and nothing proves its tests would fail on a broken
implementation unless the reviewer happens to mutate a copy. `plan-reviewer` checks gates,
definition of done, correctness, integration and conventions; it has no explicit
error-path, test-gap or false-positive rules and no channel for claims it cannot verify.
A finding repeated twice stops the loop with no escalation attempt.

## Sources (read 2026-10-22)

- Local clone of `anthropics/claude-plugins-official` under
  `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/`:
  `pr-review-toolkit/agents/pr-test-analyzer.md` (behavioral gap rating 1-10),
  `pr-review-toolkit/agents/silent-failure-hunter.md` (swallowed errors, fallbacks that
  mask failures), `code-review` command (false positives: pre-existing issues, unchanged
  lines, intentional changes).
- `obra/superpowers` main: `skills/test-driven-development/writing-good-tests.md` ("Name
  the production change that would make this test fail", no expectation computed by the
  code under test), `skills/subagent-driven-development/task-reviewer-prompt.md`
  (rationales never lower severity, `plan-mandated`, "Cannot verify from diff"),
  `skills/subagent-driven-development/SKILL.md` (fresh implementer one tier up after
  repeated failures, no verdict hints in reviewer prompts, "Rulings I made" list).
- Not ported: red-first TDD ordering (superpowers `test-driven-development`, mattpocock
  `tdd`, wshobson `tdd-workflows`): it needs one agent for test and code, or a
  stub, test, source chain that serializes every wave; the named mutation below stands in
  for the red step. Two reviewers per task (mattpocock `code-review`): superpowers merged
  its pair back into one on 2026-06-10 for dispatch cost.

## Relevant files

`~/.claude/` is not in git: every diff is against the backup.

| Task | File (F) | Backup (B) |
|---|---|---|
| T1 | `~/.claude/agents/plan-reviewer.md` | `~/.claude/backups/plan-reviewer.md.20261022-review-ports` |
| T2 | `~/.claude/skills/feature/SKILL.md` | `~/.claude/backups/feature-SKILL.md.20261022-review-ports` |
| T3 | `~/.claude/agents/implementer.md` | `~/.claude/backups/implementer.md.20261022-review-ports` |
| T4 | `~/.claude/agents/acceptance-validator.md` | `~/.claude/backups/acceptance-validator.md.20261022-review-ports` |

The backups already exist (made by the orchestrator before the plan). Never overwrite them.

## Shared definitions

SD1. Editing rules:
- Edit with the Edit tool, one anchor per edit; never rewrite a whole file.
- Text inside a `text` fence below is copied verbatim (without the fence lines), keeping
  its line breaks, indentation and blank lines.
- Never add an em dash (U+2014) in new text. Existing lines that contain one stay
  untouched unless your task replaces them.
- Frontmatter (between the first two `---` lines) does not change.

SD2. Task gate for a file F with backup B (both commands exit 0):

```sh
diff "$B" "$F" | grep '^>' | python3 -c 'import sys; sys.exit(1 if chr(0x2014) in sys.stdin.read() else 0)'
diff <(sed -n '2,/^---$/p' "$B") <(sed -n '2,/^---$/p' "$F")
```

The first proves no added line carries an em dash, the second that frontmatter is unchanged.

## Gates

SD2 for all four F/B pairs of the table, plus `git -C ~/dotfiles status --short` printing
nothing (the plan is committed, nothing else in the repo changes).

## Acceptance criteria

Paths: `R=~/.claude/agents/plan-reviewer.md`, `S=~/.claude/skills/feature/SKILL.md`,
`I=~/.claude/agents/implementer.md`, `V=~/.claude/agents/acceptance-validator.md`.

1. `grep -c -E '^(4\. Error paths|5\. Tests, only|6\. Integration|7\. Repository)' $R` → `4`
2. `grep -c -E '8-10 is MAJOR|labeled .plan-mandated.|^## Cannot verify$|git -C <repo> archive' $R` → `4`
3. `grep -c pytest $R` → `0`
4. `grep -c -E '^- \*\*Seams\*\*:|stands in for TDD.s red step|at most MINOR|haiku → sonnet → opus|named mutations\.$|made without the user' $S` → `6`
5. `grep -c 'the same finding twice in a row$' $S` → `0`
6. `grep -c -E 'never touches repo files|--exclude node_modules <repo>/ <dir>/' $I` → `2`
7. `grep -c -E 'Seams table|`Cannot verify` item|marked `plan correction`' $V` → `3`
8. SD2 exits 0 for all four pairs.
9. `diff -u B F` for each pair shows only the hunks its task specifies.
10. The `skill-dry-run` agent over the four files finds no CRITICAL or MAJOR
    contradiction between them (the orchestrator runs it in phase 5 and passes its
    findings to the validator).

## Tasks

T1 to T4 touch one file each, have no dependencies, and run in parallel. No task commits:
the files are outside git.

### T1: plan-reviewer.md

File: `~/.claude/agents/plan-reviewer.md`. Task gate: SD2 with its pair.
Definition of done: edits 1 to 4 applied, acceptance criteria 1 to 3 print the expected
counts, SD2 exits 0.

Edit 1. Replace this block (lines 17-23):

```text
2. Completeness: is the task's definition of done met? Point at where. Plan-wide
   acceptance criteria belong to the acceptance validator, not to you.
3. Correctness: edge cases, error handling, concurrency, resource cleanup. A claim
   about runtime behavior (cleanup, signals, exec, ordering) needs a command run that
   shows it; reasoning alone is not a finding, drop it.
4. Integration: grep for callers of the changed code and confirm nothing broke.
5. Repository conventions and CLAUDE.md.
```

with:

```text
2. Completeness: is the task's definition of done met? Point at where. Plan-wide
   acceptance criteria belong to the acceptance validator, not to you. The reverse
   counts too: behavior, flags, options or files the task did not ask for are MAJOR
   (tests the implementer lists under **Adapted** excepted).
3. Correctness: edge cases, error handling, concurrency, resource cleanup. A claim
   about runtime behavior (cleanup, signals, exec, ordering) needs a command run that
   shows it; reasoning alone is not a finding, drop it.
4. Error paths: every changed spot that catches, ignores or defaults an error: `_ = err`,
   an error checked but neither returned nor logged, a bare or broad `except`, `|| true`
   or `2>/dev/null` on a command whose failure matters, a fallback value or retry loop
   that gives up without a trace. A real failure swallowed with no log and no non-zero
   exit is MAJOR. A swallow the plan specifies with a reason (best effort, optional
   tool) is not a finding.
5. Tests, only when your tasks include a test file:
   - Run each mutation the plan names for the task on a mutation copy (below), one
     mutation per run, with the task's test command. A named mutation that no test
     fails on is MAJOR.
   - An expected value built by calling the code under test passes whatever that code
     does: MAJOR. Expected values are literals or come from an independent source.
   - Behavior the plan specifies for the source task that no test exercises: rate each
     gap 1-10 by the damage a regression would do (9-10 data loss, security, crash;
     7-8 wrong user-facing result; 5-6 confusing edge case; below 5 optional).
     8-10 is MAJOR, 5-7 MINOR, below 5 not reported.
6. Integration: grep for callers of the changed code and confirm nothing broke.
7. Repository conventions and CLAUDE.md.
```

Edit 2. Directly after the line
`Do not nitpick style, taste, or anything the plan explicitly listed as out of scope.`
insert a blank line and this paragraph:

```text
Rationales in the implementer's report or in code comments are claims, not evidence:
they never lower a finding's severity. A defect the plan itself mandates is still
reported, labeled `plan-mandated`: the plan does not grade its own work. Not findings:
pre-existing issues on lines the task did not change, and deliberate behavior changes
the plan asks for (a defect in them is `plan-mandated`, not dropped).
```

Edit 3. Replace this text (end of the "Git is read-only" paragraph, lines 30-32):

```text
To check that a test would catch a regression, mutate a
throwaway copy of the repo under the scratchpad directory and run pytest there; report
which tests failed under which mutation.
```

with:

```text
Mutation copy: extract the reviewed commit into a new
directory under the scratchpad (`git -C <repo> archive <commit> | tar -x -C <dir>`),
mutate and run the tests there; report which tests failed under which mutation.
```

Edit 4. Append to the end of the file (after the line `redo settled work.`) a blank line
and:

```text
## Cannot verify
Claims you could not settle with the code and a command (another task's file, a live
service, a GUI): one line each, for the acceptance validator; "none" if none.
```

Must not change: frontmatter, the intro, item 1, the Severity section, the `VERDICT` and
`## Findings` format lines.

### T2: feature/SKILL.md

File: `~/.claude/skills/feature/SKILL.md`. Task gate: SD2 with its pair.
Definition of done: edits 1 to 6 applied, acceptance criteria 4 and 5 print the expected
counts, SD2 exits 0.

Edit 1. Directly after the line
`- **Tasks T1..Tn**: scope, exclusive file list, dependencies, definition of done`
(phase 2 bullet list) insert, with no blank line before it:

```text
- **Seams**: one row per pair of tasks that share a symbol, file, config key or output
  format: producer task · consumer task · the Shared definitions entry both follow. A row
  without an entry is a contract nobody wrote down: write it before phase 3.
```

Edit 2. Directly after the line
`per-task drifts, and parallel agents implement the drift faithfully.`
insert a blank line and this paragraph (the existing blank line after it stays):

```text
A test task lists its cases, each with literal expected values written in the plan
(never "whatever the function returns") and the named mutation it must catch: the
smallest production change that breaks the case (flip a comparison, drop a branch,
return the zero value, skip a side effect). Its definition of done: each named mutation,
applied on a scratch copy, makes at least one test fail. Tests land after their source
task, so the mutation stands in for TDD's red step.
```

Edit 3. In phase 5, replace the line

```text
   gets one reviewer for both. It reviews only those tasks' code and runs only those gates.
```

with:

```text
   gets one reviewer for both. It reviews only those tasks' code and runs only those gates
   plus the test tasks' named mutations.
```

Edit 4. Directly after the line `   phase 6 acts on.` (end of phase 5) insert a blank line
and this paragraph (the existing blank line before `## Phase 6` stays):

```text
Reviewer and validator prompts carry facts only (paths, task IDs, files, gates, verdicts
verbatim), never a verdict hint such as "do not flag X", "at most MINOR" or "the plan
chose X on purpose": that pre-judges the review. Each reviewer's `Cannot verify` items
travel to the validator inside its verdict.
```

Edit 5. In the stop conditions, replace the line

```text
- the same finding twice in a row
```

with:

```text
- the same finding three times in a row. After the second, its fix goes to a fresh
  implementer one tier up (haiku → sonnet → opus, via `model`) whose prompt summarizes
  both failed attempts
```

Edit 6. Replace the line

```text
Final message: what shipped, what is left, the resulting diff --stat.
```

with:

```text
Final message: what shipped, what is left, the resulting diff --stat, and every call you
made without the user (a dropped finding, a deviation from the plan, an escalation) with
its reason.
```

Must not change: frontmatter, phases 0, 1, 3, 4, the Invariants section, and every line
not named above (including the existing em dashes in headings).

### T3: implementer.md

File: `~/.claude/agents/implementer.md`. Task gate: SD2 with its pair.
Definition of done: the edit applied, acceptance criterion 6 prints `2`, SD2 exits 0.

Edit 1. In "Hard rules", directly after the line
`  count your gate as PASS. A failure in a file of your scope is always yours.`
insert this bullet (no blank line before it):

```text
- A mutation check in your definition of done never touches repo files. Copy the
  working tree into a new directory under the scratchpad:
  `rsync -a --exclude .git --exclude .venv --exclude node_modules <repo>/ <dir>/`
  Apply one mutation there, run the test command there, note which test failed, and
  start each next mutation from a fresh copy. A named mutation that no test fails on
  means your tests are not done. List each mutation and its failing test under **Gates**.
```

Must not change: frontmatter, workflow steps, all other hard rules, the report format.

### T4: acceptance-validator.md

File: `~/.claude/agents/acceptance-validator.md`. Task gate: SD2 with its pair.
Definition of done: edits 1 and 2 applied, acceptance criterion 7 prints `3`, SD2 exits 0.

Edit 1. Replace the line

```text
   seams: shared names, call sites across task boundaries, config keys, imports.
```

with:

```text
   seams: shared names, call sites across task boundaries, config keys, imports; start
   from the plan's Seams table when it has one.
```

Edit 2. Replace the line

```text
   UPHELD or DROPPED with one line of reasoning.
```

with:

```text
   UPHELD or DROPPED with one line of reasoning. Settle each `Cannot verify` item with a
   command and rule it the same way. An UPHELD `plan-mandated` finding enters the Fix
   list marked `plan correction`: the fix changes the plan section first.
```

Must not change: frontmatter, checks 1 and 2, the Budget paragraph, the response format.

## Seams

| Producer | Consumer | Contract |
|---|---|---|
| T1 (`## Cannot verify`, `plan-mandated`) | T4 edit 2, T2 edit 4 | the exact strings `Cannot verify` and `plan-mandated` |
| T2 edit 2 (named mutation in the plan) | T1 item 5, T3 bullet | the phrase "named mutation" |
| T2 edit 1 (`**Seams**`) | T4 edit 1 | the plan section name "Seams" |

## Phase 5 for this plan

No commits exist for the four files, so instead of one `plan-reviewer` per commit: one
`plan-reviewer` for T1 to T4 (diffs against the backups) and one `skill-dry-run` over the
four files, in parallel; both verdicts go to the `acceptance-validator`.

## Edge cases

- Repos without tests, or plans without a test task: the new test rules apply only to test
  tasks, nothing changes for them (dotfiles plans included).
- Python repos: the `git archive` copy has no `.venv`; the test command (`uv run`) rebuilds
  it, slower but correct.
- Dirty worktree in a target repo: the implementer's `rsync` copy includes sibling agents'
  half-written files; the existing foreign-failure rule covers their errors.
- Linux: these files live only on the macOS workstation; `rsync` and `git archive` exist on
  both.
- A `/feature` run in another session reads these live files mid-edit: accepted, the edits
  take a minute.

## Not doing

- No plugin install: `pr-review-toolkit`, `code-review`, superpowers, mattpocock skills,
  wshobson `tdd-workflows`.
- No change to models, efforts, tools, colors or any frontmatter; concurrency cap (12) and
  iteration cap (5) stay.
- No red-first test ordering, no second reviewer per task.
- No change to `~/dotfiles/CLAUDE.md`, `go-code-reviewer`, `python-code-reviewer`,
  `skill-dry-run`, or the `skill-note-sync.sh` hook (its false positive on reads of the
  plugin marketplace cache is a separate follow-up).

## Iteration 1: fixes

Validator FAIL on criterion 10 (skill-dry-run). Upheld, `plan-mandated`: the mutation run
reuses the task gate, whose absolute repo paths test the repo instead of the copy (false
"caught" and "not caught"); a build or setup failure counts as a caught mutation. Upheld
MINOR: the reviewer has no stated way to apply a mutation (`sed -i` is hook-blocked, no
Edit tool), `tar -C` fails on a missing dir, phase 5 passes no commit SHA, the "Workflow
sections" list lacks Seams. Dropped: test-gap ownership, scope rule vs. copy.

Fix: every test task names a **mutation command** (build check plus test run, relative to
the repo root); the implementer and reviewer run it as `(cd <dir> && <mutation command>)`
inside a copy built from `git archive`; a mutation counts only when the copy builds and
the output names a failed test. The implementer copy switches from `rsync` (pulls wave
siblings' half-written files) to `git archive HEAD` plus its own scope files.

SD1 and SD2 apply unchanged; backups stay the originals (pre-plan), so SD2 diffs cover
both rounds. Tasks I1-T1, I1-T2, I1-T3 touch one file each and run in parallel.

### I1-T1: plan-reviewer.md

File: `~/.claude/agents/plan-reviewer.md`. Task gate: SD2 with its pair, plus criteria
2 (now `5`), 3, 11. Definition of done: both edits applied, those criteria pass.

Edit A. Replace:

```text
   - Run each mutation the plan names for the task on a mutation copy (below), one
     mutation per run, with the task's test command. A named mutation that no test
     fails on is MAJOR.
```

with:

```text
   - Run each mutation the plan names for the task on a mutation copy (below), one
     mutation per run, with the plan's mutation command. A valid named mutation that
     no test fails on is MAJOR. A named mutation that breaks the build is invalid:
     MAJOR, labeled `plan-mandated` (the plan picks a buildable one).
```

Edit B. Replace:

```text
Mutation copy: extract the reviewed commit into a new
directory under the scratchpad (`git -C <repo> archive <commit> | tar -x -C <dir>`),
mutate and run the tests there; report which tests failed under which mutation.
```

with:

```text
Mutation copy: extract the reviewed commit into a new
directory under the scratchpad
(`mkdir -p <dir> && git -C <repo> archive <commit> | tar -x -C <dir>`). Apply the
mutation with `python3 -c` (read_text, replace, write_text: `sed -i` is blocked and you
have no Edit tool), then run `(cd <dir> && <mutation command>)`, never with a repo path
and never through `<repo>/.venv`. A mutation is caught only when the copy builds and the
output names a failed test; a build or setup failure makes it invalid. Report which
tests failed under which mutation, one copy per mutation.
```

### I1-T2: feature/SKILL.md

File: `~/.claude/skills/feature/SKILL.md`. Task gate: SD2 with its pair, plus criteria 4,
5, 12. Definition of done: the three edits applied, those criteria pass.

Edit A. Replace the paragraph added by T2 edit 2:

```text
A test task lists its cases, each with literal expected values written in the plan
(never "whatever the function returns") and the named mutation it must catch: the
smallest production change that breaks the case (flip a comparison, drop a branch,
return the zero value, skip a side effect). Its definition of done: each named mutation,
applied on a scratch copy, makes at least one test fail. Tests land after their source
task, so the mutation stands in for TDD's red step.
```

with:

```text
A test task lists its cases, each with literal expected values written in the plan
(never "whatever the function returns") and the named mutation it must catch: the
smallest production change that breaks the case and still builds (flip a comparison,
drop a branch, return the zero value, skip a side effect). It also names one mutation
command, the build check plus the test run, relative to the repo root with no repo path
in it (`go vet ./internal/calc/ && go test ./internal/calc/`, `uv run pytest tests/x.py`).
Definition of done: each named mutation, applied on a scratch copy, builds and makes a
named test fail. The mutation stands in for TDD's red step: tests land after their
source task.
```

Edit B. In the line starting `then append one "Workflow sections" block`, replace the
substring `(Gates, Shared definitions, Tasks, Not doing)` with
`(Gates, Shared definitions, Tasks, Seams, Not doing)`.

Edit C. In phase 5, in the line starting `   waves), in parallel (same cap of 12), passing:`,
replace the substring `passing: path to the plan, the commit's task IDs,` with
`passing: path to the plan, the commit SHA, its task IDs,`.

### I1-T3: implementer.md

File: `~/.claude/agents/implementer.md`. Task gate: SD2 with its pair, plus criterion 13.
Definition of done: the edit applied, criterion 13 passes.

Edit A. Replace the whole bullet added by T3 (six lines, from
`- A mutation check in your definition of done never touches repo files. Copy the` to
`  means your tests are not done. List each mutation and its failing test under **Gates**.`)
with:

```text
- A mutation check in your definition of done never touches repo files. Build each copy
  from the last commit plus your own files, in a new directory under the scratchpad:
  `mkdir -p <dir> && git -C <repo> archive HEAD | tar -x -C <dir>`, then `cp` every file
  of your scope to its relative path under `<dir>`. Apply one mutation in the copy and run
  the plan's mutation command from it: `(cd <dir> && <mutation command>)`, never with a
  repo path and never through `<repo>/.venv`. A mutation is caught only when the copy
  builds and the output names a failed test; a build or setup failure makes it invalid:
  report it, do not count it. Use a fresh copy for each mutation. A valid named mutation
  that no test fails on means your tests are not done. Under **Gates**, list each
  mutation with its failing test, or "invalid: build fails".
```

### Iteration 1 acceptance criteria

Criterion 2 now expects `5` (a second `labeled `plan-mandated`` line). Criterion 6 is
replaced by 13. New:

11. `grep -c -E 'mkdir -p <dir> && git -C <repo> archive <commit>|`sed -i` is blocked|output names a failed test; a build' $R` → `3`
12. `grep -c -E 'breaks the case and still builds|relative to the repo root with no repo path|builds and makes a$|Tasks, Seams, Not doing|the commit SHA, its task IDs' $S` → `5`, and `grep -c 'makes at least one test fail' $S` → `0`
13. `grep -c -E 'never touches repo files|archive HEAD \| tar -x -C <dir>|output names a failed test|invalid: build fails' $I` → `4`, and `grep -c rsync $I` → `0`
14. Spike in a throwaway Go module under the scratchpad, with the documented forms only
    (`mkdir -p <dir> && git -C <repo> archive HEAD | tar -x -C <dir>`, mutation applied
    via `python3 -c`, then `(cd <dir> && go vet ./<pkg>/ && go test ./<pkg>/)`):
    a flip-a-comparison mutation prints a `--- FAIL: Test...` line; the clean copy prints
    `ok`; a mutation that leaves an unused import fails in `go vet` before any test runs
    (invalid, not caught).
15. A fresh `skill-dry-run` over the four files finds no CRITICAL or MAJOR issue
    (replaces criterion 10 for this iteration).
