---
name: feature
description: Plan, delegate, implement and independently validate a non-trivial coding change on a scoped branch. Use for the feature workflow or when project instructions require it.
---

# Feature workflow for Codex

Read the [canonical workflow](../../../claude/skills/feature/SKILL.md), resolving
this skill's symlink first. It owns the plan sections, task contracts, gates,
review formats and bounded fix loop. Apply the Codex overrides below throughout;
applicable project instructions take precedence over either file.

## Runtime overrides

- The task is the user's current request and any supplied focus, not the literal
  `$ARGUMENTS` placeholder. Use `$feature` or an explicit request to invoke it.
- Read project `AGENTS.md`; resolve instruction-file aliases and edit the
  canonical target. Explicitly read applicable `.claude/rules` after inspecting
  their `paths`. Neither reads nor spawns imply Claude rule auto-injection.
  Include relevant rule constraints in agent briefs when not otherwise loaded.
- Use native roles `implementer`, `plan-reviewer`, `acceptance-validator` and
  `skill-dry-run`. For research use available `explorer` or `default` agents.
  The custom role TOML files own approved model and reasoning settings. When the
  current runtime cannot select a configured role, read its TOML and pass the full
  `developer_instructions`, approved model and effort to an available agent;
  disclose that fallback.
  Ignore every canonical Claude model/effort dispatch or tier-switch directive,
  including failure retries and repeated-finding escalation. Never pass
  `sonnet`, `opus` or `claude-*` as Codex model names.
- Use available Codex tools: native spawn for Agent, send-message for a running
  agent, follow-up/resume for an idle agent. Read/Grep/Glob and Bash map to focused
  file/shell tools; Edit/Write map to file edits. Track tasks with the runtime's
  supported mechanism; absent TodoWrite is not a blocker.
- Verify paths and tools before dispatch. Give every worker exclusive file
  ownership and state that others share the checkout. Bound reports to verdict,
  changed files, command evidence and unresolved issues rather than raw logs.
- Limit each parallel wave to currently available child slots, not the canonical
  limit of twelve. Shared files and dependencies remain sequential. Do not
  duplicate a full/heavy test run while any agent is running it.
- Do not end the user turn just because agents were dispatched. Continue useful
  independent work, receive results through the runtime's agent tools, and stay
  active through review, fixes, validation and the authorized completion steps.
  Do not busy-poll or create fallback scheduled wakeups.
- After an agent failure inspect scoped changes before retrying. Resume the same
  agent when possible; redistribute only unfinished work when runtime guidance
  permits. Report unavailable models or persistent capacity errors. Do not invent
  model aliases or bypass approval, sandbox, rate or memory limits.

## Shared resources and boundaries

- The canonical `plan_edits.py` remains beside the canonical skill. Resolve it
  from that source directory when the documented `~/.claude/skills/feature/`
  installation is unavailable. Keep outer backtick fences longer than any run
  in the old or new text, and retain the exact old/new prose-edit checks.
- Claude's vault skills index and `skill-note-sync` prerequisite do not apply
  to Codex adapters. Do not edit an unrelated vault to read, install or edit a
  Codex skill. If a hook blocks a read, report the named blocker and continue
  independent authorized work; use the normal access flow without bypassing it.
- Read-only reviewer roles are behavioral restrictions; all child agents inherit
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
  Project-specific merge/push authorization overrides canonical branch defaults;
  do not infer authorization to send messages, publish data or weaken permissions.
