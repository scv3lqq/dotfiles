# Session retrospective: workflow efficiency

## Goal and evidence

Apply four small improvements from the tmux activity task in this session:
role availability was rejected for two configured roles; a repeated RED run
raced with source changes; acceptance reran tests already covered by its own
full Gates; the PTY smoke needed fixes for inherited file flags, terminal size
and clipped titles. Keep technical guidance in its existing scoped locations.
Base: `946be62`. Baseline `just check` passes; source prose is the base itself.

## Shared definitions and constraints

Preserve model choices, complete role contracts, report formats, independent
review, final full Gates, authorization and the canonical feature workflow.
The user authorized proceeding after the shared-checkout wait was reported.
Preserve all concurrent unrelated work. No product code, global/project
AGENTS.md or unrelated files change. The feature
adapter owns three workflow fixes; scoped tmux rules own the PTY lesson.
Use the existing plan_edits.py helper at its canonical source path. Existing
old blocks below were generated from git, not retyped. The tmux edits are in
`plans/session-retro-tmux-edits.md` because the helper applies one file per plan.

## T1: Apply exact prose changes

Ownership: `codex/skills/feature/SKILL.md` and `.claude/rules/tmux.md` only.
One task, no dependencies. The implementer applies this plan to the feature
adapter and the companion plan to tmux rules using plan_edits.py apply; no
manual prose rewriting. Others share checkout; preserve their changes.
Definition of done: both exact checks below pass. Scoped task gates:

```bash
python3 claude/skills/feature/plan_edits.py check plans/session-retro-efficiency.md codex/skills/feature/SKILL.md 946be62
python3 claude/skills/feature/plan_edits.py check plans/session-retro-tmux-edits.md .claude/rules/tmux.md 946be62
python3 -B codex/check.py
```

## Acceptance criteria and Gates

- Both source files equal base plus their generated old/new edits, byte for byte
  (the two exact checks above); no other source files change.
- `just check` passes before each commit; keep private command/exit/output evidence.
- `git diff --check 946be62` passes.
- Run the installed skill-creator quick_validate.py against the feature adapter
  with its PyYAML dependency in an isolated uv environment; no system install.
- Independent skill-dry-run verifies the plan before implementation and simulates
  the changed workflow afterwards: unavailable custom roles, RED still running,
  full Gates already covering an acceptance suite, and an isolated PTY fixture.
  Demonstrate how its decisions follow the text without changing permissions,
  skipping final Gates, or changing models/report contracts. For PTY use scratch
  and synthetic data only, no real desktop notifications or live tmux changes.
- Final acceptance-validator checks exact blocks, full Gates, source scope and
  dry-run evidence. Pure verbatim prose tasks need no separate code reviewer.

## Seams

| Producer | Consumer | Contract |
| --- | --- | --- |
| This plan and companion | T1 and validator | Exact helper checks, same base |
| Feature adapter | Configured runtime roles | Existing full contracts and model settings |
| Scoped tmux guidance | Scratch smoke experiments | Isolated server and PTY only |

## Edge cases

macOS copy flags require copyfile plus explicit chmod, not copy2 metadata.
Linux keeps existing portability; no new installed dependencies. Preserve the
pre-existing untracked .DS_Store. A first custom-role rejection triggers fallback;
new capability evidence permits another native attempt. Missing tools fail
honestly. RED source writers wait for evidence even in a shared checkout.

## Not doing

No new scripts, unit tests that match prose, model/default changes, role-contract
summaries, relaxed approval rules, broad instruction rewrites or task product edits.

## Exact feature adapter edits

**E1.** (lines 21-29)

````md E1-old
- Use native roles `implementer`, `plan-reviewer`, `acceptance-validator` and
  `skill-dry-run`. For research use available `explorer` or `default` agents.
  The custom role TOML files own approved model and reasoning settings. When the
  current runtime cannot select a configured role, read its TOML and pass the full
  `developer_instructions`, approved model and effort to an available agent;
  disclose that fallback.
  Ignore every canonical Claude model/effort dispatch or tier-switch directive,
  including failure retries and repeated-finding escalation. Never pass
  `sonnet`, `opus` or `claude-*` as Codex model names.
````

````md E1-new
- Use native roles `implementer`, `plan-reviewer`, `acceptance-validator` and
  `skill-dry-run`. For research use available `explorer` or `default` agents.
  The custom role TOML files own approved model and reasoning settings. When the
  current runtime cannot select a configured role, read its TOML and pass the full
  `developer_instructions`, approved model and effort to an available agent;
  disclose that fallback. After a custom-role availability rejection, use this
  fallback for the remaining configured roles in the session unless runtime
  capability evidence changes; do not repeat rejected capability probes.
  Ignore every canonical Claude model/effort dispatch or tier-switch directive,
  including failure retries and repeated-finding escalation. Never pass
  `sonnet`, `opus` or `claude-*` as Codex model names.
````

**E2.** (lines 34-39)

````md E2-old
- Verify paths and tools before dispatch. Give every worker exclusive file
  ownership and state that others share the checkout. Bound reports to verdict,
  changed files, command evidence and unresolved issues rather than raw logs.
- Limit each parallel wave to currently available child slots, not the canonical
  limit of twelve. Shared files and dependencies remain sequential. Do not
  duplicate a full/heavy test run while any agent is running it.
````

````md E2-new
- Verify paths and tools before dispatch. Give every worker exclusive file
  ownership and state that others share the checkout. Bound reports to verdict,
  changed files, command evidence and unresolved issues rather than raw logs.
- Limit each parallel wave to currently available child slots, not the canonical
  limit of twelve. Shared files and dependencies remain sequential. Do not
  duplicate a full/heavy test run while any agent is running it.
- For test-first tasks, wait for the RED command to exit and its log to be saved
  before dispatching source writers. Reuse that evidence; a baseline rerun in the
  shared checkout can race with implementation and invalidate the baseline.
````

**E3.** (lines 60-70)

````md E3-old
  the parent sandbox. Reviewers mutate only isolated scratch copies for probes.
- Keep canonical baseline evidence, explicit pathspecs, red/green gates and
  independent review. Save required pre-commit gate commands, exit codes and
  output in private scratch; associate each log with the resulting commit and
  pass its path to the validator. A missing or failed check is not PASS.
  Reuse those logs for the same verified tree instead of canonical detached-worktree
  reruns solely to recreate archived evidence. Changed code or inputs require new
  gates; the validator still runs the final Gates.
  Check the full task diff against the plan's base, including committed changes,
  rather than relying on a working-tree-only diff check.
- Preserve the canonical five-iteration and repeated-finding stop conditions.
````

````md E3-new
  the parent sandbox. Reviewers mutate only isolated scratch copies for probes.
- Keep canonical baseline evidence, explicit pathspecs, red/green gates and
  independent review. Save required pre-commit gate commands, exit codes and
  output in private scratch; associate each log with the resulting commit and
  pass its path to the validator. A missing or failed check is not PASS.
  Reuse those logs for the same verified tree instead of canonical detached-worktree
  reruns solely to recreate archived evidence. Changed code or inputs require new
  gates; the validator still runs the final Gates. Use that validator-owned run
  for acceptance criteria it already covers, rather than rerunning scoped suites
  solely to list passed tests. Changed inputs or unresolved results justify reruns.
  Check the full task diff against the plan's base, including committed changes,
  rather than relying on a working-tree-only diff check.
- Preserve the canonical five-iteration and repeated-finding stop conditions.
````

