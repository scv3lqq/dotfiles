---
name: repo-knowledge-base
description: Explore a multi-repo workspace and write the agent-facing knowledge base for it: one CLAUDE.md per repo, a root CLAUDE.md, ARCHITECTURE.md, and path-scoped .claude/rules. Use when asked to "build a knowledge base", "document these repos", "create/improve CLAUDE.md files", "onboard me to this workspace", or to run /init across several repos. For a single repo with no siblings, the built-in init skill is enough.
argument-hint: [workspace dir]
---

# Multi-repo knowledge base

Goal: a future session picks up work in any repo here without re-exploring. Read-only exploration:
no installs, no migrations, no commits, no deploys.

## 1. Survey before delegating (cheap, do it yourself)

- List the dirs; per repo record file count and `git -C <d> rev-parse --abbrev-ref HEAD`.
- `find <repo>/.claude -type f` and note existing `CLAUDE.md` / `AGENTS.md` sizes. Never overwrite them
  blind: they carry decisions worth keeping.
- **Look for an already-generated architecture/lineage doc** (`docs/*.md`, a `_build/` generator, a
  drawing). If one exists, read it yourself and tell the subagents it exists so they don't rediscover it;
  reference it from `ARCHITECTURE.md` instead of duplicating it.
- Check whether `CLAUDE.md` / `.claude/` are gitignored per repo (`git check-ignore -v CLAUDE.md`).
  If they are, say so in the final summary: everything you write there is machine-local.

## 2. One subagent per repo, all in one message

`general-purpose`, `model: opus` (this work is judgment: spotting stale claims and fragile areas, not
grep). Give each the same shape, and include these constraints verbatim:

- Read-only. Never `cd`; absolute paths. Read files in chunks via `sed -n`, at most 150 lines per call.
- Name the sibling repos and say another agent covers each: report only the *references* found
  (topic names, table names, env vars, API paths).
- Ask for: purpose + who consumes it; stack and entry points with paths; commands taken **only** from
  justfile/Makefile/package scripts/pyproject/CI/README, quoted exactly, anything else marked
  `unverified`; conventions that differ from language defaults; **gotchas, where most of the effort
  goes**; hot spots from `git log --since=6.months --name-only --pretty=format: | sort | uniq -c | sort -rn`;
  cross-repo connections; existing `.claude/rules/*.md` paths + frontmatter + one-line topic.
- **Do not paste file contents verbatim.** For an existing `CLAUDE.md`/`AGENTS.md`, ask for the section
  list plus a numbered list of statements that are now wrong, with `file:line` evidence. A verbatim dump
  of two 150-line files costs the parent more than re-reading the one file it will actually edit.
- Cap it: "report compactly, no filler, under ~300 lines".

If paths change mid-run (workspace moved, repo renamed), `SendMessage` the new prefix to each running
agent instead of killing and relaunching: they keep their findings.

## 3. Write the files

Budgets, and they are hard: root `CLAUDE.md` under 60 lines, each repo `CLAUDE.md` under 100.
`ARCHITECTURE.md` has no limit but no filler either.

- Root `CLAUDE.md`: what the workspace is, one line per repo, cross-repo workflow and ordering rules,
  and a pointer to `ARCHITECTURE.md` as plain backticked text, never an `@import` (an import loads it
  into every session). Put the *shared* workflow here once so repo files don't repeat it.
- Repo `CLAUDE.md`: purpose in 1-2 sentences, commands that cannot be guessed, conventions that differ
  from defaults (pair every "don't" with the "do instead"), then gotchas for most of the file. Leave out
  directory trees, dependency lists and generic advice: that is readable from the code.
- Anything true of only part of a repo goes to `.claude/rules/<topic>.md` with `paths:` frontmatter.
  **Check an existing rules file in that repo first and match its frontmatter style** (for example
  inline `paths: ["src/x/*.py", "tests/test_x.py"]`, no `description:`). Writing block-list
  frontmatter and retrofitting it afterwards is pure rework.
- `ARCHITECTURE.md`: a Mermaid diagram of repos, datastores and external APIs with call directions;
  a section per repo (purpose, key modules with paths, main data flows); a "Where to change X" table
  mapping common tasks to files in order; a glossary of project terms; open questions. Mark inferred
  edges as unverified and say why.
- Root and repo files land in context together: they must not contradict or repeat each other.

## 4. Gates before reporting

- `wc -l` every file written, against the budgets above.
- Scan the new files for the em dash: `grep -rn "$(printf '\342\200\224')" <files>` (write the pattern
  with that escape so your own file stays ASCII and the style hook does not fire on it). Docs are
  English and the style rule forbids the em dash: use a colon, comma or parentheses. Writing long
  English prose is exactly where it slips in.
- Mermaid: quote every label, keep ids alphanumeric, and avoid parentheses in unquoted labels.
- Summary for the user: files created or changed, open questions, and what looked risky or inconsistent
  across repos. Flag stale absolute paths in `.claude/settings.local.json` if the workspace moved.
