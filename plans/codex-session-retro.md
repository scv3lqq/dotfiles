# Session Workflow Retrospective

## Goal and evidence

Apply three improvements demonstrated by this session. Base `c43d351`, branch
`feat/codex-session-retro`. Existing untracked `.agents/` remains out of scope.
The visible avoidable work was concentrated in planning and repeated verification,
not implementation; precise timing was not recorded.

| Improvement | Evidence | Exact change and expected effect |
| --- | --- | --- |
| Robust prose edits | A nested code fence truncated a replacement; four stub EOF blank lines required a later commit | Adaptive fences and one final newline prevent both mechanical failures |
| Reusable gate evidence | Four archived gate runs repeated already successful pre-commit checks because logs were not retained | Save the existing runs and check the full task diff before acceptance |
| Keep blocked reads scoped | A skill-read denial led to an unrelated vault index edit despite the adapter boundary | Extend that boundary explicitly to reads and report the actual blocker |

Model mapping, complete plugin inventory and canonical instructions were already
fixed in the preceding work. Do not add new global rules for these settled items.

## Shared definitions

- Shared helper: `claude/skills/feature/plan_edits.py`; its public CLI and
  `expected(plan, path, base) -> tuple[str, int]` contract stay unchanged.
- Legacy triple-backtick E-blocks remain valid. The parser additionally accepts
  an opening run of at least three backticks and closes only on the exact same
  run, on its own line. Preserve body whitespace and old-text uniqueness checks.
- `stub` chooses one delimiter per range: length `max(4, longest backtick run in
  that range + 1)`. Use it for both old and new blocks. Join range sections with
  one blank line and terminate the complete output with exactly one newline.
  A later edit introducing a longer run must lengthen its surrounding fences.
- Native workflow edits are specified byte for byte in
  `plans/codex-session-retro-feature.md`, applied against base `c43d351`.
- Keep models, permissions, hooks, source skill behavior and public report
  contracts unchanged. This is a shared parser fix, not a client-specific fork.

## Acceptance and gates

1. Four focused unittest cases below pass, with nested-body tail text intact.
2. Existing E-block plans remain byte-equivalent through the new parser; the
   independent audit found 60 blocks in seven committed plans at base.
3. The native skill equals its exact prose specification, and an independent
   dry-run finds no workflow contradiction.
4. `just check` includes the helper tests and passes. Also run
   `uvx ruff check claude/skills/feature/plan_edits.py claude/skills/feature/test_plan_edits.py`
   and `uvx mypy --strict claude/skills/feature/plan_edits.py`.
5. Save required pre-commit gate logs privately, associate them with commits,
   and pass them to acceptance. `git diff --check c43d351` must pass before commit;
   final `git diff --check c43d351..HEAD` must pass before merge/push.

## T1: Repair and test the prose helper

Own `claude/skills/feature/plan_edits.py`, adjacent `test_plan_edits.py`, and
`justfile`. No dependencies. Write tests first and record RED before implementation.
Append the scoped unittest command below to the existing `just check` recipe.
Use only standard library unittest, temporary files and a mocked `at_base` returning
literal fixture text; no user configuration, network or Git commits in fixtures.
Four test cases (subtests allowed):

- Legacy multi-E replacement, with and without descriptive headings; nested
  tilde fences and blank lines retained. Literal source/result and count 2.
- Longer outer fences containing triple and quadruple inner fences in old/new;
  assert literal complete replacement including a tail after each inner fence.
- Adaptive stub round-trip for a source with a four-backtick run: expect literal
  five-backtick E headers and closers, unchanged source and count 1.
- Multiple stub ranges: expect both range labels, four E blocks, one separator
  blank line between sections, exactly one final newline and no EOF blank line.

Guard test: legacy replacement passes before and after. Named reviewer mutations:
restrict the parser to triple fences (nested-fence case fails); use a fixed
four-backtick stub delimiter (adaptive round-trip fails); append a second final
newline (multiple-range case fails). Run mutations only on isolated copies.
Task gates and mutation command:
`python3 -B -m unittest discover -s claude/skills/feature -p 'test_plan_edits.py'`;
the scoped Ruff and mypy commands above. No full suite in the worker/reviewer.
Done when all cases pass and existing bodies remain unchanged through parsing.

## T2: Apply the bounded workflow corrections

Own only `codex/skills/feature/SKILL.md`. No dependency on T1: both helper versions
accept this legacy prose plan. Apply/check the exact prose plan against `c43d351`.
Task gate: `python3 -B claude/skills/feature/plan_edits.py check
plans/codex-session-retro-feature.md codex/skills/feature/SKILL.md c43d351` (one command).
`python3 -B codex/check.py` is the second task gate. No full suite.
Done when exact equality and the existing skill asset check pass.

## Seams, edge cases and exclusions

T1 produces fence support; T2 explains delimiter preservation. Legacy plans must
continue to work during parallel edits. The new test recipe is portable Python,
not dependent on shell features or an installed client. Nonexistent/ambiguous old
text keeps the current failure behavior. No general Markdown parser rewrite.
No other sessions, private memories, vault edits, hooks, permissions, runtime
configurations, model changes, unrelated documentation or new always-loaded rules.
Review T1 independently with the named mutations; final acceptance runs full gates
after worker/reviewer runs finish. Then follow the repository fast-forward/push rule.

## Baseline

The audit reproduced truncation and the two-newline stub output. All 60 legacy
blocks matched the proposed delimiter prototype. Helper Ruff passed; helper strict
mypy baseline passed. The pre-plan `just check` passed 43 tests and its private log
is retained for acceptance. The four new tests do not exist at base. The exact
skill prose check failed as expected before T2; the task diff check passed.
