# /feature agents on Sonnet 5.5 at max effort

## Goal

`/feature` runs `implementer`, `plan-reviewer`, and its phase 1 `Explore` and `general-purpose`
dispatches on `claude-sonnet-5-5` at effort `max`. The tier rules and the four prose contradictions
found in the skill stop contradicting the agents.

Current behavior: `implementer` is haiku/medium, `plan-reviewer` is sonnet/medium, built-ins inherit
the session. `SKILL.md` limits full Gates to phase 4 and to the orchestrator, while it also runs them
after each wave and has the validator run them. `SKILL.md` sends a plan to `skill-dry-run`, whose
input only knows finished changes. `CLAUDE.md` says `opus[1m]`, `settings.json` says `opus`.

Verified facts:
- `effort: max` is valid in frontmatter and supported on Sonnet 5.5; the Agent call `effort` overrides
  frontmatter (https://code.claude.com/docs/en/sub-agents.md, https://code.claude.com/docs/en/model-config.md).
- A built-in `Explore` dispatched with `model: sonnet`, `effort: max` ran on `claude-sonnet-5-5` with
  `"effort":"max"` in its transcript (this session, CLI 2.1.314).

## Acceptance criteria

The commands in Gates, run from the repo root, all print the expected result.

## Gates

Task gates, on the working tree:

```bash
python3 ~/.claude/skills/feature/plan_edits.py check plans/feature-agents-sonnet-max.md claude/skills/feature/SKILL.md 922354b
for f in claude/agents/implementer.md claude/agents/plan-reviewer.md; do
  sed -n '4,5p' "$f" | tr '\n' ' '; echo
done
grep -c haiku claude/skills/feature/SKILL.md claude/agents/implementer.md
grep -F 'IMPLEMENTER: Claude Sonnet 5.5 (`claude-sonnet-5-5`), max effort' CLAUDE.md
grep -F '(`opus` in settings)' CLAUDE.md
grep -F 'PLAN: the plan file' claude/agents/skill-dry-run.md
grep -F 'With PLAN:' claude/agents/skill-dry-run.md
```

Expected: `EDITS OK: 8 edits`; both agent lines read `model: claude-sonnet-5-5 effort: max`; both
haiku counts are 0; each of the four `grep -F` prints one line.

Full Gates add, after the commit:

```bash
git diff -U0 922354b HEAD | python3 -c 'import sys; print(sum(chr(0x2014) in l for l in sys.stdin if l.startswith("+") and not l.startswith("+++")))'
git diff --name-only 922354b HEAD
wc -l < CLAUDE.md
```

Expected: `0`; exactly `CLAUDE.md`, `claude/agents/implementer.md`, `claude/agents/plan-reviewer.md`,
`claude/agents/skill-dry-run.md`, `claude/skills/feature/SKILL.md`,
`plans/feature-agents-sonnet-max.md`; under 200.

Base result (`922354b`), task gates only: `FAIL: file differs from base + plan edits` (so all eight
old blocks match once); agent lines `model: claude-haiku-5-5 effort: medium` and
`model: claude-sonnet-5-5 effort: medium`; haiku counts 2 in `SKILL.md`, 1 in `implementer.md`; all
four `grep -F` find nothing.

## Shared definitions

None: one task.

## Tasks

### T1: apply the edits

Files: `claude/skills/feature/SKILL.md`, `claude/agents/implementer.md`,
`claude/agents/plan-reviewer.md`, `claude/agents/skill-dry-run.md`, `CLAUDE.md`.
Dependencies: none. Do not commit: the orchestrator commits.

1. `SKILL.md`, from the repo root, no hand edits:
   `python3 ~/.claude/skills/feature/plan_edits.py apply plans/feature-agents-sonnet-max.md claude/skills/feature/SKILL.md 922354b`
   It takes every E-block in this plan; the blocks below are only for `SKILL.md`.
2. The other four files, with Edit, exactly the Old/New pairs under "Other files".

Must not change: anything else in those files, including the em dashes already in `implementer.md`,
`plan-reviewer.md` and `SKILL.md`. Task gates: the first block in Gates.
Done: the task gates print their expected results.

### SKILL.md edits

**E1.** Phase 1, a new first sentence.

```md E1-old
Before dispatching research: `grep -H -m1 '^paths:' .claude/rules/*.md` (never `cat`/`sed` rule
```

```md E1-new
Every Explore and general-purpose dispatch in this phase passes `model: sonnet` and `effort: max`:
built-ins have no frontmatter of ours to carry them.

Before dispatching research: `grep -H -m1 '^paths:' .claude/rules/*.md` (never `cat`/`sed` rule
```

**E2.** Phase 2, who runs the full Gates and when.

```md E2-old
The full **Gates** run only in phase 4.
```

```md E2-new
Implementers never run the full **Gates**: the orchestrator runs them after each wave and in phase 4, the validator in phase 5.
```

**E3.** Phase 2, no small-model rationale.

```md E3-old
implementers run on a small model
and only transcribe the spec.
```

```md E3-new
implementers
only transcribe the spec.
```

**E4.** Phase 2, the implementer is already on sonnet.

```md E4-old
give behavior, decisions and the spike's snippets, and
dispatch that implementer with `model: sonnet`.
```

```md E4-new
give behavior, decisions and the spike's snippets.
```

**E5.** Phase 2, how the plan reaches the dry run.

```md E5-old
send the plan to @skill-dry-run before phase 3
```

```md E5-new
send the plan to @skill-dry-run (its PLAN input) before phase 3
```

**E6.** Phase 3, 529 fallback.

```md E6-old
another tier (haiku → sonnet, sonnet ⇄ opus)
```

```md E6-new
another tier (sonnet ⇄ opus)
```

**E7.** Phase 4, the validator also runs the full suite.

```md E7-old
The full test suite is the orchestrator's alone: one run at a time, never two in parallel;
every subagent prompt carries scoped gates plus "never the full suite".
```

```md E7-new
The full test suite runs one at a time, never two in parallel: the orchestrator runs it, and the
@acceptance-validator in phase 5 once no orchestrator run is active; every other subagent prompt
carries scoped gates plus "never the full suite".
```

**E8.** Phase 6, the tier above the implementer.

```md E8-old
implementer one tier up (haiku → sonnet → opus, via `model`)
```

```md E8-new
implementer on opus (via `model`)
```

### Other files

`claude/agents/implementer.md`

- Old: `model: claude-haiku-5-5` New: `model: claude-sonnet-5-5`
- Old: `effort: medium` New: `effort: max`

`claude/agents/plan-reviewer.md`

- Old: `effort: medium` New: `effort: max`

`CLAUDE.md`

- Old: `Opus 5.5 (`opus[1m]` in settings)` New: `Opus 5.5 (`opus` in settings)`
- Old: `IMPLEMENTER: Claude Haiku 5.5 (`claude-haiku-5-5`), medium effort` New: `IMPLEMENTER: Claude Sonnet 5.5 (`claude-sonnet-5-5`), max effort`

`claude/agents/skill-dry-run.md`

- Old: `skill, agent or helper script. Runs the scripts` New: `skill, agent or helper script, or of a plan to change one. Runs the scripts`
- Old: `You review a skill change another session just made.` New: `You review a skill change another session just made, or a plan for one.`
- Old: `- CHANGED: absolute paths of the changed files. DATA: files the skill reads.` New: `- CHANGED: absolute paths of the changed files, or PLAN: the plan file when nothing is implemented yet. DATA: files the skill reads.`
- Old: `1. Read every CHANGED file fully; DATA and CONSUMERS only where a check needs them (grep big files).` New: the same line, then a second line: `   With PLAN: read the plan and each file it edits, judge those files as the plan would leave them, run only what exists.`

## Seams

None: one task.

## Edge cases

- macOS vs Linux: agent files and skills link on both, `settings.json` is untouched.
- Missing tools: only `python3`, `git`, `grep`, `sed`.
- Dirty worktree: clean at base `922354b`; `plan_edits apply` rewrites `SKILL.md` from base.
- First run: the running session may hold the old agent definitions, so this cycle dispatches
  `implementer` with explicit `model: sonnet`, `effort: max`.

## Not doing

- `claude/settings.json`: `modelSettings` for Sonnet stays `medium`. It sets the session level, the
  docs imply frontmatter wins over it but do not say so; the cycle's reviewer transcript checks it.
- User-level `Explore.md` or `general-purpose.md` overrides: they would change every session, and the
  `general-purpose` override is undocumented.
- `acceptance-validator` and `skill-dry-run` models, the main session's model.
- `plans/` history, `claude/CLAUDE.md` (lists valid IDs only), `cc-settings` test instance on haiku.
