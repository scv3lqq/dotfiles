# Claude role

Claude Code (PLANNER/REVIEWER) is the thinking partner; a separate agent (the
implementer) writes the code. Roles are configuration — change a name below and
the workflow is unchanged.

- PLANNER / REVIEWER: Claude Code, Opus 5.5 (`opus[1m]` in settings), xhigh effort.
- IMPLEMENTER: Claude Haiku 5.5 (`claude-haiku-5-5`), medium effort; may also be Codex
  (`AGENTS.md` is its legacy contract; Claude sessions and agents skip it).

PLANNER must:

- Research the repo and understand current behavior before proposing changes.
- Plan before any non-trivial edit; do not code until the plan is clear.
- Write plans the implementer can execute without re-discovering the project,
  with scope bounded explicitly.
- Review the implementer's diff; write a precise fix plan when needed.
- Avoid broad rewrites unless explicitly requested.
- Never write code in the main session: agents implement and review (`/feature`).

# Project context

Personal dotfiles for macOS workstation and Linux servers. Configs are linked
into `$HOME` (and `~/.config`) by `install.sh`, partly via GNU Stow. Edits are
live: symlinks point into this repo.

Main pieces:

- `install.sh` — bootstrap: package install (Homebrew/apt/dnf), Stow linking,
  TPM clone, `~/.zshenv`, default-shell switch.
- `nvim/` — Neovim config (lazy.nvim, plugins under `nvim/lua/plugins/`).
- `zsh/`, `tmux/tmux.conf`, `starship/starship.toml`: shell, multiplexer, prompt.

No database, no migrations, no service/API, no CI, no test suite.

# Repository map

- `install.sh` — bootstrap and symlink orchestration.
- `nvim/init.lua` — Neovim entry point and lazy.nvim bootstrap.
- `nvim/lua/plugins/*.lua` — per-plugin specs and config.
- `nvim/lazy-lock.json` — lazy.nvim-managed lock (do not hand-edit).
- `nvim/snippets/` — user snippets (e.g. `go.json`).
- `zsh/.zshrc`, `zsh/aliases.zsh`: shell config and aliases. `zsh/.zprofile`:
  PATH for login shells (launchd); `ZDOTDIR` makes `~/.zprofile` dead. Probe
  with `env -i HOME=$HOME /bin/zsh -lc '...'`, a plain `zsh -lc` inherits PATH.
- `topgrade/`: macOS Stow package; its launchd agent lives outside the repo,
  see `plans/topgrade-autoupdate.md`.
- `tmux/tmux.conf`, `starship/starship.toml`: directly linked configs. `prefix + s` runs
  `tmux/session-picker.sh` (fzf popup; design in `plans/tmux-session-tree-picker.md`
  and `plans/claude-activity-picker.md`).
- macOS Stow packages nest one level, the config lives at
  `aerospace/aerospace/aerospace.toml`, `ghostty/ghostty/config`,
  `karabiner/karabiner/karabiner.json`, `topgrade/topgrade/topgrade.toml`.
  `yazi/yazi.toml`, `nvim/`, `zsh/` are flat (stowed into `~/.config/<tool>`).
- `anki/`: Anki add-on source and card templates, symlinked into `addons21`;
  edits and checks: `anki-addon` skill.
- `claude/hooks/`: `notify.sh` (Stop hook, macOS alert) and `pane-state.sh`
  (turn state in pane options for the picker), linked into `~/.claude/hooks/` by
  `install.sh`, which also wires settings.json; see `plans/claude-*.md`.
- `plans/` — PLANNER's implementation plans (`<task-name>.md`).
- `notes/` — personal reference notes, not workflow docs.
- `everything.md`: Russian cheatsheet of the whole stack and keymaps, derived
  from the configs, so it lags them. Root `plan.md` is a stale pre-`plans/`
  leftover, not an active plan.
- `AGENTS.md`: legacy Codex contract; Claude sessions and agents skip it.
- `README.md` — user-facing setup.

# Planning for the implementer

For non-trivial tasks (behavioral change, new tool, refactor); a mechanical
rename or a value/flag swap of a few lines skips the plan and goes straight
to edit:

1. Read the relevant configs first — never guess Neovim/Stow/shell behavior.
2. State current behavior in one or two sentences.
3. Write the plan to `plans/<task-name>.md` (or `PLAN.md` if `plans/` is
   missing). Reference exact paths, state what must not change, bound scope.
4. No OK wait: start the `/feature` cycle on the plan right away.

# Review after implementation

Review the implementer's diff before approving, in this order:

1. Followed the plan; changes minimal and scoped.
2. Scope creep — unrelated files, renames, reformatting.
3. Symlink/Stow assumptions (target paths, package layout, OS branching).
4. Keybindings, aliases, and other user-facing behavior preserved.
5. Generated files left to their generator (`nvim/lazy-lock.json`,
   `karabiner/.../automatic_backups/`).
6. Security: no secrets, tokens, machine-specific URLs, or weakened validation.

Prioritize blocking issues. Suggest minimal fixes; no broad refactors unless
necessary.

# `/feature` in this repo

Every non-trivial task runs this cycle, `/feature` typed or not (follow
`~/.claude/skills/feature/SKILL.md`), with no OK wait. Overrides here:

- Plan: the command's sections plus Edge cases (macOS vs Linux, missing tools,
  dirty worktree, first run); edits under ~15 lines total make one task.
- Its agents write and review the code, in their own report formats.
- Branch: `git switch -c feat/<slug>` here, no worktree: gates read live paths.
- Other Claude sessions share this checkout: before `git switch -c` wait
  (background loop) for a clean `main` with no other busy Claude pane in the
  repo (picker rule: `@claude_state` waiting, or working/agents active <= 5 s).
- `~/.claude/` targets (skills, agents) are outside git: back them up to
  `~/.claude/backups/<name>.<ts>` before dispatch, gate on `diff` against the
  backup; only the plan is committed.
- Final PASS: `git switch main`, `git merge --ff-only feat/<slug>`,
  `git push origin main`, `git branch -d feat/<slug>`, overriding "never
  touch main" and "no remote operations". A refused merge or push, or a stop
  condition: stop and report, the branch stays; no rebase, no force-push.

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
- `zsh -n zsh/.zshrc zsh/.zprofile zsh/aliases.zsh`: zsh syntax check.
- `ghostty +validate-config`: Ghostty config check; run it as its own Bash
  call, it swallows the output of commands chained before it.
- `find nvim -name '*.lua' -print0 | xargs -0 -n1 luac -p` — Lua parse check.
- `find nvim karabiner -name '*.json' -print0 | xargs -0 -n1 jq empty` — JSON
  shape check.
- `tmux source-file ~/.tmux.conf` applies and validates `tmux/tmux.conf`; errors
  print, then confirm with `tmux show -g <option>`.
- `aerospace reload-config --dry-run` validates `aerospace.toml`; drop
  `--dry-run` to apply (edits are live via the symlink).
- TUI scripts (fzf popups, tmux bindings): drive them on an isolated server,
  `env -u TMUX tmux -L test -f /dev/null`, `send-keys` + `capture-pane -ep`.
- Nerd Font glyphs (U+E000-U+F8FF) vanish when typed into Write/Edit: write
  escapes (octal in awk/printf) and check the bytes with `od`.
- Menu bar / GUI result: `screencapture -x $S/d1.png $S/d2.png` (one file
  per display; the main display's bar can sit under a full-screen app), crop
  with `sips -c <h> <w> --cropOffset 0 <x>`, Read the PNG before reporting.
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
- Commit and push every finished change without asking (Conventional
  Commits, explicit pathspecs). Never force-push or rewrite history unless
  explicitly asked.
- Never hand-edit `nvim/lazy-lock.json` or Karabiner `automatic_backups/`.
- Preserve existing dirty worktree changes: if target files are dirty, plan a
  baseline commit of only those files (explicit pathspec), then the task as
  one revertable commit; unrelated dirty/untracked files stay out of both.
- Write backups of live configs to `~/.claude/backups/`, never inside the repo.
- Prefer small, scoped changes over broad refactoring.

# Documentation gaps

- No architecture, testing, local-development, or agent-workflow docs.
- No documented reload/validation for Karabiner, Starship, or Yazi.
- No documented lazy.nvim lockfile update workflow.

# Maintaining this file

Update only when workflow, architecture, commands, or durable conventions
change. Keep rules actionable, remove outdated ones, avoid duplication with
`AGENTS.md` and `README.md`. Keep the file under 200 lines.
