---
description: "Session retro — evidence-based changes to CLAUDE.md, skills, agents, rules, applied immediately"
argument-hint: "[focus: claude-md | skills | agents | context]"
disable-model-invocation: true
---

Review this session and improve my Claude Code setup so similar tasks run faster, with fewer mistakes and less context.

Layout. Always loaded: `~/.claude/CLAUDE.md`, project `CLAUDE.md`, `.claude/rules/*.md` without `paths` — already in your context, do not re-read. On demand: skills (`~/.claude/skills`, `.claude/skills`), agents (`~/.claude/agents`, `.claude/agents`), path-scoped rules (`.claude/rules` with `paths`). Open a file only when a specific finding points at it.

## Evidence
Count only what actually happened in this session:
- wrong assumptions, rework, my corrections
- repeated exploration: files re-read, same search twice, conventions rediscovered
- questions to me that a doc or skill could have answered
- repeatable multi-step procedures done by hand → skill candidate
- missing knowledge → skill or path-scoped rule; CLAUDE.md only if needed in every session
- existing skill/agent that should have fired but didn't → fix its description
- subagents: wrong tools/model, missing context in the delegation prompt, output too long or too short for the parent, delegation not worth it (or skipped when it should have happened)
- permission prompts that interrupted routine steps → `allowed-tools` or settings allow rule
- CLAUDE.md lines that were noise for this task → flag as "unused here" (removal needs recurrence across retros)
- rough split of where turns/context went: exploration, rework, subagent output, docs

## Rules
- Context is a budget: every always-loaded line is paid on every session and by every custom subagent. An addition must have changed behavior here AND be likely to recur. Prefer delete > shorten > move to skill/rule > add.
- Placement: facts and "always do X" → CLAUDE.md; procedures → skill; file-type conventions → rule with `paths`; context-heavy or parallel work → agent; must-always-happen checks (lint, format, tests) → hook, not prose.
- Max 5 changes, ordered by impact/size. Each: evidence (one line) → change (file + exact diff or text) → expected effect. Terse.
- "Nothing worth changing" is a valid answer.
- Apply every change immediately — edit the files yourself, do not ask for confirmation. Report each change as applied (or why not).

Focus (optional): $ARGUMENTS
