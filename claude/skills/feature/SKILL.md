---
description: Plan → dispatch → review loop on a fresh branch
argument-hint: [task description]
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, Agent, SendMessage, TodoWrite
disable-model-invocation: true
---

# Task
$ARGUMENTS

You are the orchestrator. You do not write production code yourself: implementation
goes through `implementer` subagents, code review goes through `plan-reviewer`, the final verdict through `acceptance-validator`.

## Phase 0 — branch
- `git status --porcelain --untracked-files=no`: if tracked files are dirty, stop and ask (untracked files outside the task scope are fine).
- No git remote operations (fetch/pull/push); branch off the local HEAD of the current branch.
- Create the branch the way the project `CLAUDE.md` prescribes: if it mandates worktrees, `git worktree add <its path> -b feat/<kebab-slug-from-task> <base>` and run everything (gates, commits, implementer/reviewer prompts) inside that worktree using its gate command form; otherwise `git switch -c feat/<kebab-slug-from-task>`. Everything after this happens there.

## Phase 1 — research
Before dispatching research: `grep -H -m1 '^paths:' .claude/rules/*.md` (never `cat`/`sed` rule
bodies just to list them — some rules are >10KB), then read only the rules whose `paths`
match the task scope AND whose matching files you will NOT Read directly — path-scoped
rules auto-inject when you Read a matching file, so pre-reading those is double-paid.
Exception: in bypass-permissions mode files are read via Bash (`cat`/`sed`), which never
triggers auto-inject — then `cat` every matching rule explicitly, once, before reading the file.
Rules may constrain the research itself (e.g. what must not be delegated). Files under ~300 lines that the plan will anchor to (exact lines,
constants): read them directly; delegate to Explore only what you will NOT read
yourself (test conventions, callers/importers, broad sweeps).

Delegate specific questions to the Explore agent, not "explore the repo":
where the affected logic lives, what the conventions are, how tests are structured,
who calls the code being changed, the exact build/test/lint commands.

Spikes: when the design hinges on how an external tool behaves (TUI keys, CLI flag
semantics, version gates), hand the experiment to a general-purpose agent working in the
scratchpad; it returns findings plus the working snippet as reply text, never its
transcript (the harness refuses report files such as FINDINGS.md from subagents). Keep
prototyping and test-harness output out of the orchestrator's context.
Format migrations (schema v1 -> v2, export/import): first find an old input whose converted
output already exists (git history vs a live export), have the spike agent make its converter
reproduce that output byte for byte, then freeze it (sha256) and make "fresh run + cmp" the
generating task's gate instead of hand-editing the target (2026-10-23: Grafana v2 port).
Porting logic from a sibling repo: list the inputs the source rule silently relies on (client
configs such as `auto.offset.reset`, commit presence, which consumers/callers exist) and grep the
target for each one that differs, before the plan (2026-10-23: a fetch watchdog ported from
a sibling service missed a consumer reading from `latest` and cost a fix iteration).

Unknown external-data semantics (what a source column/flag means, which rows or period
feed an aggregate/filter) are the user's call — never default them by analogy with nearby
code. Before the plan, ask ONE question about the meaning (plus ≤2 profiling queries if data
can settle it); phase 2's "no approval needed" does not cover guessing them.

## Phase 2 — plan
Fold the requirements of the rules from phase 1 into the plan — a rule only auto-loads
for whoever Reads/edits a matching file; tasks touching other files never see it.

Write the plan into the plan dir the project CLAUDE.md defines (e.g. `plans/<slug>.md`), else `.claude/plans/<slug>.md`; if the target dir is gitignored, pick a committable one:
- **Goal** and **acceptance criteria**: verifiable, not "works well"; each one a command
  whose observable result (stdout, exit code) the toolchain really exposes as written
  (e.g. `go run` turns every non-zero exit into 1: exit codes need a built binary); for
  prose, one `grep -F` phrase per check: a multi-pattern `grep -c` counts lines. A grep
  over code must not hit text the plan itself mandates (comments, docstrings): anchor it
  (`^\s*assert\b`) or use the AST. A "new tests fail before the change" criterion names
  the plan's guard tests (kept behavior, pass on both) as exempt
- **Gates** — the exact commands for this repo
- **Tasks T1..Tn**: scope, exclusive file list, dependencies, definition of done
- **Seams**: one row per pair of tasks that share a symbol, file, config key or output
  format: producer task · consumer task · the Shared definitions entry both follow. A row
  without an entry is a contract nobody wrote down: write it before phase 3.
- **Not doing** — an explicit list
Slice tasks so each one is self-contained: an agent sees only its prompt and this plan.
Slice for parallelism: ONE source file per task (a test file is its own task, depending on
the task whose file it tests). Give every task its own **task gates**: every full-Gates check
that can be scoped to its file or package (formatter, vet/type-check, the repo linter), plus
its package's tests, so a scoped gate never passes what the full Gates later reject. The full **Gates** run only in phase 4.

All design thinking happens here, in the orchestrator: implementers run on a small model
and only transcribe the spec. Every decision (algorithm, data shape, names, edge-case
handling, error text) is made in the plan; a section that leaves a choice open is not ready.
If a task's spec would amount to the whole file (over ~60 lines of non-obvious logic), do
not write the file into the plan: give behavior, decisions and the spike's snippets, and
dispatch that implementer with `model: sonnet`.
Implementers read only **Shared definitions** plus their own task section,
so each section is a complete spec, never "see T2" or "as discussed": the file and verified
anchor lines; every symbol to add or change with its exact signature; behavior including
edge cases and exact error/log text; imports; a snippet for any non-obvious logic; what in
the file must not change; task gates; definition of done. Cross-file contracts (signatures,
names, config keys) live once in Shared definitions.
Several edits to one file in one task: quote each edit's old text (an Edit `old_string`), line
numbers only as hints; an earlier insert shifts every later line (2026-10-24: dry-run caught
shifted anchors in one README/CLAUDE.md task).

When parallel tasks share one compile unit (a Go package, a TS module), put the shared
types, constants and errors in a T0 task that runs alone and is committed before the
parallel wave, so every sibling file compiles against them while the others are written.

A literal several tasks must reproduce identically (a list, regex, message format):
define it ONCE in the plan and make every task reference that definition — spelling it
per-task drifts, and parallel agents implement the drift faithfully.

A test task lists its cases, each with literal expected values written in the plan
(never "whatever the function returns") and the named mutation it must catch: the
smallest production change that breaks the case, still builds and changes behavior
(flip a comparison, drop a branch, return the zero value, skip a side effect), described
by function and change, since the source file does not exist yet. It also names one
mutation command, the build check plus the test run, relative to the repo root with no
repo path in it (`go vet ./internal/calc/ && go test ./internal/calc/`,
`uv run pytest tests/x.py`). The implementer writes the cases; the reviewer runs the
mutations on a copy of the commit. Tests land after their source task, so the mutation
stands in for TDD's red step. Its definition of done is the cases plus its task gates;
the mutations are not part of it.

If the task points at an EXISTING plan file (a reviewed design): commit it unchanged first,
then append one "Workflow sections" block (Gates, Shared definitions, Tasks, Seams, Not doing) in a
second commit — never rewrite or re-derive the design sections; where a task and the design
disagree, the design wins.
A design that already slices tasks (source and tests together, disjoint files) keeps its task IDs
and file sets: add per-task gates, closed decisions and named mutations, do not re-slice. The
committed plan file is one more line in the branch diff: if an acceptance criterion pins the exact
file set, say so in the Workflow block.

When tasks transcribe prose that agents will follow (skills, agent definitions, commands
they are told to run), send the plan to @skill-dry-run before phase 3 and fold its findings
in: found after implementation, each one costs a full iteration (2026-10-22: five
iterations on one mutation-check paragraph). A NEW skill also needs its line in the vault
skills index before an agent writes it: the `skill-note-sync` hook blocks the write otherwise.

Runnable blocks in the plan (a fixture suite) are fenced `bash`; steps that change live state
(settings writes, links, installs) are fenced `sh`, so an agent extracting "the bash block"
cannot run them (2026-10-26: an implementer extracted every `bash` block of a plan, live apply
included; only the suite's `exit` stopped it).
A task that pastes a verbatim plan block gets a gate that diffs the block (awk-extracted from the
plan) against the file range; a fixture that extracts a section by markers first checks that both
markers exist (2026-10-26: a splice dropped a block's last 5 lines, the end marker went missing,
and the fixture ran install.sh to EOF and still printed DONE).

Commit the plan, print a short summary (goal, tasks, gates), and proceed to phase 3
immediately — no approval needed.

## Phase 3 — dispatch
One @implementer per ready task. The prompt must be self-contained:
task ID · branch · path to the plan · scope · files · relevant paths from phase 1 ·
conventions · definition of done · the task's task gates (not the full Gates). (Prohibitions and the report
format live in the implementer agent definition — do not restate them. Same for
path-scoped rules covering the task's own files: they auto-load for the implementer —
cite the rule file, restate only what lives elsewhere. Project `CLAUDE.md` loads into every
subagent too — never restate its code style, gate rules or language conventions; a prompt
carries only task-specific anchors: verified line numbers, fixture/helper names, the plan's
§ references.)

Parallelize only tasks with non-overlapping files, at most 12 at a time.
Any dependency or shared file means strictly sequential — and then run the gates and COMMIT
the finished task before dispatching the next one that touches the same files. Never let two
tasks' hunks pile up in one working tree and split them afterwards (`git apply --unidiff-zero`
misplaces context-free hunks; costs a reset + redo).

Parallel tasks run in waves of ready tasks. After each wave, run the full Gates and commit
the wave's files by explicit pathspec before dispatching the next wave.
Heavy gates (local JVM/Spark suites) share one machine: while a wave's implementers run theirs,
start no background full gate, and never rerun a baseline the prompt already states (2026-10-23:
a 12-min suite took 48 min next to three Spark implementers, one red run took 30 min).

After dispatching, end the turn and wait for completion notifications; never poll
or block on agent output (blocking duplicates their reports into context), and schedule no
fallback wakeups (ScheduleWakeup): they only add empty turns.

If an agent dies (API error / usage limit): inspect `git diff` first; re-dispatch only
the missing part and finish mechanical leftovers (format) yourself. A usage-limit death
(429): after the reset, resume the same agent via SendMessage (context intact; it restarts
a half-done step on a fresh copy) instead of a new dispatch. On `529 Overloaded`
re-dispatch at once with a `model` override to another tier (haiku → sonnet, sonnet ⇄ opus) — never
retry the same model blind; it cost two dead dispatches on 2026-09-03.

## Phase 4 — gates
Run build/test/lint yourself. Red is a fact — no reviewer needed, go straight to phase 6.
Verify with `--stat` + gates; read an implementer's diff only when a later task consumes
its API (check the signatures) or its report raises a doubt — full code review is phase 5.
The full test suite is the orchestrator's alone: one run at a time, never two in parallel;
every subagent prompt carries scoped gates plus "never the full suite". A run the harness
kills for memory pressure is restarted only on the user's word (2026-10-23).

Exception to "go straight to phase 6": a red gate whose cause is obvious and confined to
one task's file goes to that still-alive implementer via SendMessage with the exact fix
and its task gates; rerun the full Gates afterwards. It does not count as an iteration.

Gate commands handed to implementers are exactly the task's task gates from the plan: do not add checks the
repo gate lacks (e.g. `ruff format --check` on whole files), they only trigger agents to
prove drift in untouched hunks is pre-existing.

## Phase 5 — review
Two tiers:
1. Code review: one @plan-reviewer per commit as soon as it lands (do not wait for later
   waves), in parallel (same cap of 12), passing: path to the plan, the commit SHA, its task IDs,
   their file lists, their task gates. A test task committed together with its source task
   gets one reviewer for both. It reviews only those tasks' code and runs only those gates
   plus the test tasks' named mutations. Tasks that only copy verbatim plan text get no
   reviewer: the validator checks each fenced block against the file.
2. Validation: ONE @acceptance-validator after all per-task verdicts are in, passing: path
   to the plan, `git diff <base>...HEAD --stat`, task list, the per-task verdicts verbatim.
   If a criterion needs the full Gates on every commit, run them yourself in the background
   as commits land (detached worktrees, logs in the scratchpad) and pass the log paths: the
   validator reads them and reruns only the tip.
   It proves every acceptance criterion with command evidence, runs the full Gates, checks
   cross-task seams, and rules on each per-task finding. Its VERDICT is the only one
   phase 6 acts on.

Reviewer and validator prompts carry facts only (paths, task IDs, files, gates, verdicts
verbatim), never a verdict hint such as "do not flag X", "at most MINOR" or "the plan
chose X on purpose": that pre-judges the review. Each reviewer's `Cannot verify` items
travel to the validator inside its verdict.

## Phase 6 — loop
FAIL → append an "Iteration N: fixes" section to the plan (a delta; rewrite the whole
plan only if the problem is architectural), one fix task per item of the validator's
Fix list (items on the same files merge into one task) → back to phase 3.

A `plan correction` that changes only a named mutation (no code to change) skips phase 3:
rerun the test task's @plan-reviewer on its existing commit SHA with the corrected plan.

PASS with non-blocking findings: send the trivial ones to the still-alive implementer
via SendMessage (its context is intact — no re-dispatch, no new plan section); fold
the rest into the final report as documented follow-ups. Does not count as an iteration.

Stop conditions — honor them, no "just one more pass":
- 5 iterations spent
- the same finding three times in a row. After the second, its fix goes to a fresh
  implementer one tier up (haiku → sonnet → opus, via `model`) whose prompt summarizes
  both failed attempts
- a fix requires going outside the plan's boundaries
- a gate does not run

Final message: what shipped, what is left, the resulting diff --stat, and every call you
made without the user (a dropped finding, a deviation from the plan, an escalation) with
its reason.

## Invariants
- Never touch main. Commit after each green iteration with a meaningful message.
- No --no-verify, no skipped tests, no bending tests to match the code.
- Do not trust agent reports. Trust the gates.
- Write all artifacts in English. Talk to me in Russian.
