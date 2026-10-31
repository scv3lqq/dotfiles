# Session Retro Feature Edits

Base: `c43d351`. Exact replacements for `codex/skills/feature/SKILL.md`.

**E1.** (lines 50-55)

```md E1-old
- The canonical `plan_edits.py` remains beside the canonical skill. Resolve it
  from that source directory when the documented `~/.claude/skills/feature/`
  installation is unavailable. Preserve its exact old/new prose-edit checks.
- Claude's vault skills index and `skill-note-sync` hook prerequisite do not
  apply to Codex adapters. Do not write to a vault to install or edit a Codex
  skill. Likewise, do not assume Claude hooks enforce tool restrictions.
```

```md E1-new
- The canonical `plan_edits.py` remains beside the canonical skill. Resolve it
  from that source directory when the documented `~/.claude/skills/feature/`
  installation is unavailable. Keep outer backtick fences longer than any run
  in the old or new text, and retain the exact old/new prose-edit checks.
- Claude's vault skills index and `skill-note-sync` prerequisite do not apply
  to Codex adapters. Do not edit an unrelated vault to read, install or edit a
  Codex skill. If a hook blocks a read, report the named blocker and continue
  independent authorized work; use the normal access flow without bypassing it.
```

**E2.** (lines 58-60)

```md E2-old
- Keep canonical baseline evidence, explicit pathspecs, red/green gates,
  independent reviewer verdicts and final acceptance validation. A gate that
  did not run or failed outside a worker's scope is not PASS.
```

```md E2-new
- Keep canonical baseline evidence, explicit pathspecs, red/green gates and
  independent review. Save required pre-commit gate commands, exit codes and
  output in private scratch; associate each log with the resulting commit and
  pass its path to the validator. A missing or failed check is not PASS.
  Reuse those logs for the same verified tree instead of canonical detached-worktree
  reruns solely to recreate archived evidence. Changed code or inputs require new
  gates; the validator still runs the final Gates.
  Check the full task diff against the plan's base, including committed changes,
  rather than relying on a working-tree-only diff check.
```
