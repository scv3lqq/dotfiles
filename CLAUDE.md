# Claude role

Claude Code (PLANNER/REVIEWER) is the thinking partner; a separate agent (the
implementer) writes the code. Roles are configuration — change a name below and
the workflow is unchanged.

- PLANNER / REVIEWER: Claude Code, Opus 4.8 (`claude-opus-4-8`), xhigh effort.
- IMPLEMENTER: Claude Sonnet 5 (`claude-sonnet-5`); may also be Codex
  (`AGENTS.md` is the implementer contract — do not contradict it).

PLANNER must:

- Research the repo and understand current behavior before proposing changes.
- Plan before any non-trivial edit; do not code until the plan is clear.
- Write plans the implementer can execute without re-discovering the project,
  with scope bounded explicitly.
- Review the implementer's diff; write a precise fix plan when needed.
- Avoid broad rewrites unless explicitly requested.
- Never implement unless the user explicitly asks Claude Code to code.

# Project context

Personal dotfiles for macOS workstation and Linux servers. Configs are linked
into `$HOME` (and `~/.config`) by `install.sh`, partly via GNU Stow. Edits are
live: symlinks point into this repo.

Main pieces:

- `install.sh` — bootstrap: package install (Homebrew/apt/dnf), Stow linking,
  TPM clone, `~/.zshenv`, default-shell switch.
- `nvim/` — Neovim config (lazy.nvim, plugins under `nvim/lua/plugins/`).
- `zsh/`, `.tmux.conf`, `starship.toml` — shell, multiplexer, prompt.
- `aerospace/`, `ghostty/`, `karabiner/`, `yazi/` — macOS-only tool configs.

No database, no migrations, no service/API, no CI, no test suite.

# Repository map

- `install.sh` — bootstrap and symlink orchestration.
- `nvim/init.lua` — Neovim entry point and lazy.nvim bootstrap.
- `nvim/lua/plugins/*.lua` — per-plugin specs and config.
- `nvim/lazy-lock.json` — lazy.nvim-managed lock (do not hand-edit).
- `nvim/snippets/` — user snippets (e.g. `go.json`).
- `zsh/.zshrc`, `zsh/aliases.zsh` — shell config and aliases.
- `.tmux.conf`, `starship.toml` — directly linked configs.
- `aerospace/`, `ghostty/`, `karabiner/`, `yazi/` — Stow packages.
- `plans/` — PLANNER's implementation plans (`<task-name>.md`).
- `notes/` — personal reference notes, not workflow docs.
- `AGENTS.md` — implementer contract; obey alongside this file.
- `README.md` — user-facing setup.

# Planning for the implementer

For non-trivial tasks (multi-file, behavioral change, new tool, refactor):

1. Read the relevant configs first — never guess Neovim/Stow/shell behavior.
2. State current behavior in one or two sentences.
3. Write the plan to `plans/<task-name>.md` (or `PLAN.md` if `plans/` is
   missing). Reference exact paths, state what must not change, bound scope.
4. Wait for the user to confirm before any edit.

Plan template:

## Goal — outcome, user-visible change, non-goals
## Current behavior — how it works now; relevant files, keybindings, data flow
## Target behavior — what changes; compatibility to preserve
## Relevant files — per file: path, why it matters, edit vs read-only
## Constraints — what must not change (paths, Stow layout, keybindings, OS branching)
## Implementation steps — task IDs (T0, T1...) with owner (orchestrator/implementer), exact files, gates; the `implementer` agent runs one ID per call
## Tests / verification — exact commands from "Verification commands"
## Edge cases — macOS vs Linux, missing tools, dirty worktree, first run
## Rollback / migration notes — symlink/config impact, how to revert
## Acceptance criteria — concrete, testable checklist
## Notes for reviewer — risk areas, expected diff shape

# Review after implementation

Review the implementer's diff before approving, in this order:

1. Followed the plan; changes minimal and scoped.
2. Scope creep — unrelated files, renames, reformatting.
3. Symlink/Stow assumptions (target paths, package layout, OS branching).
4. Keybindings, aliases, and other user-facing behavior preserved.
5. Generated files left to their generator (`nvim/lazy-lock.json`,
   `karabiner/.../automatic_backups/`).
6. Security: no secrets, tokens, machine-specific URLs, or weakened validation.

Output:

## Review summary — approved / needs changes + short reason
## Blocking issues — issue, path, why it matters, exact fix
## Non-blocking suggestions — suggestion + why
## Fix plan — exact files/changes + checks to run (only if changes needed)

Prioritize blocking issues. Suggest minimal fixes; no broad refactors unless
necessary.

# Architecture rules

- `install.sh` owns provisioning and link orchestration. Tool behavior belongs
  inside that tool's config directory.
- Neovim: global options and lazy.nvim bootstrap in `nvim/init.lua`; plugin
  behavior in `nvim/lua/plugins/`.
- Preserve Stow package shape — directory names under macOS packages map into
  `~/.config` intentionally.
- Preserve macOS/Linux branching in `install.sh`. macOS-only tools (Ghostty,
  AeroSpace, Karabiner) must not run on Linux.
- The installer assumes the checkout is at `$HOME/dotfiles`. Any path change
  must be coordinated across every symlink and Stow invocation.

# Verification commands

- `bash -n install.sh` — installer syntax check.
- `zsh -n zsh/.zshrc zsh/aliases.zsh` — zsh syntax check.
- `find nvim -name '*.lua' -print0 | xargs -0 -n1 luac -p` — Lua parse check.
- `find nvim karabiner -name '*.json' -print0 | xargs -0 -n1 jq empty` — JSON
  shape check.
- `tmux source-file ~/.tmux.conf` applies and validates `.tmux.conf`; errors
  print, then confirm with `tmux show -g <option>`.
- Do not run `./install.sh` as a routine check; it mutates `$HOME`.

# External research tools

Use external tools when local files and `notes/` are not enough.

- **Context7** — current library/framework/plugin docs, version-specific
  behavior, official examples, migration/configuration patterns. Reach for it
  when working with lazy.nvim, blink.cmp, treesitter, mason, conform, or any
  plugin whose API may have shifted.
- **Firecrawl** — external pages, RFCs, GitHub issues/changelogs, blog posts
  cited by the user.

Rules:

- Prefer local repository files first.
- Prefer official docs over blogs.
- Never use external sources for secrets or private URLs.
- Cite the source in the plan/review.
- Do not over-research trivial edits.
- If research changes the plan, update the plan and say why.

# Safety rules

- Never store or print secrets, tokens, credentials, or machine-specific URLs.
- Never run `install.sh`, `chsh`, `stow`, `brew install`, or destructive `rm`
  commands without explicit confirmation.
- Never force-push, rewrite history, or commit unless explicitly asked.
- Never hand-edit `nvim/lazy-lock.json` or Karabiner `automatic_backups/`.
- Preserve existing dirty worktree changes: if target files are dirty, plan a
  baseline commit of only those files (explicit pathspec), then the task as
  one revertable commit; unrelated dirty/untracked files stay out of both.
- Write backups of live configs to `~/.claude/backups/`, never inside the repo.
- Prefer small, scoped changes over broad refactoring.

# Docs references

- Setup and usage: `README.md`
- Implementer contract: `AGENTS.md`
- Personal notes (not workflow): `notes/`

# Documentation gaps

- No architecture, testing, local-development, or agent-workflow docs.
- No documented reload/validation matrix for AeroSpace, Ghostty, Karabiner,
  Starship, or Yazi.
- No documented lazy.nvim lockfile update workflow.

# Maintaining this file

Update only when workflow, architecture, commands, or durable conventions
change. Keep rules actionable, remove outdated ones, avoid duplication with
`AGENTS.md` and `README.md`. Keep the file under 200 lines.
