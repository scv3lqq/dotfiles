---
name: retro
description: Review the current Codex session and apply up to five evidence-based improvements to instructions, skills or native agents. Use for a session retrospective, optionally focused on guidance, skills, agents or context.
---

# Codex session retrospective

Review what actually happened in this session so similar tasks take fewer
corrections, repeated reads and unnecessary turns. Use the user's optional focus.
Do not mine unrelated conversations or private memory without a request.

## Evidence

Count demonstrated mistakes, rework, user corrections, duplicate exploration,
missing inputs, missed skill triggers, failed gates and avoidable questions.
For agents, examine file ownership, plan completeness, report size, tool/model
availability, fix follow-ups and whether delegation helped. Estimate where work
went: exploration, implementation, verification, rework and reporting.

Open a file only when a finding points to it. Global `~/.codex/AGENTS.md` and
applicable project `AGENTS.md` supply durable guidance. Personal/project skills
live in `~/.agents/skills` and `.agents/skills`; native agents are TOML under
`~/.codex/agents` or `.codex/agents`. Resolve symlinks before choosing a source
file. Shared Claude skills may still live in the dotfiles `claude/skills` tree;
prefer a Codex adapter for runtime differences instead of changing Claude behavior.

## Changes

- Propose and apply at most five demonstrated improvements, ordered by benefit
  relative to size. Each needs one line of evidence, an exact change and expected
  effect. "Nothing worth changing" is a valid result.
- Prefer delete, shorten or move before adding always-loaded instructions.
  One unused instruction is not evidence that it should be removed everywhere.
- Put durable conventions in `AGENTS.md`, procedures in skills, scoped behavior
  in native agents, and mechanical checks in the project's existing test/check
  mechanism. Codex does not automatically load Claude path rules or hooks.
- Preserve instruction precedence, unrelated edits, current model choices and
  report contracts. Do not add speculative rules or generalize one task's needs.
- A permission interruption is diagnostic evidence, not authorization to relax
  approvals, sandbox policy or tool permissions. Fix the workflow within current
  authorization; request any genuinely required access through its normal flow.
- Apply authorized local changes with the normal repository workflow, validate
  the changed behavior, and use an independent `skill-dry-run` when a substantial
  instruction workflow changes. Commit/push only as authorized by project rules.
- Report applied changes and verification concisely. Name any concrete blocker;
  never claim an unrun check passed.
