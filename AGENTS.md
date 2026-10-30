# Agent roles

The main agent plans and coordinates; scoped implementers write code and
independent reviewers check it. Roles are workflow responsibilities, independent
of a particular product or model. Runtime configuration owns model selection.

PLANNER must:

- Research the repo and understand current behavior before proposing changes.
- Plan before any non-trivial edit; do not code until the plan is clear.
- Write plans the implementer can execute without re-discovering the project,
  with scope bounded explicitly.
- Review the implementer's diff; write a precise fix plan when needed.
- Avoid broad rewrites unless explicitly requested.
- Delegate implementation and review beyond a micro task: at most two short
  calls on known targets or an edit of at most three already-decided lines.

# Project context

Personal dotfiles for macOS workstation and Linux servers. Configs are linked
into `$HOME` (and `~/.config`) by `install.sh`, partly via GNU Stow. Edits are
live: symlinks point into this repo.

Main pieces:

- `install.sh`: bootstrap with package install (Homebrew/apt/dnf), Stow linking,
  TPM clone, `~/.zshenv`, default-shell switch.
- `nvim/`: Neovim config (lazy.nvim, plugins under `nvim/lua/plugins/`).
- `zsh/`, `tmux/tmux.conf`, `starship/starship.toml`: shell, multiplexer, prompt.

No database, migrations, service/API or CI. `just check` validates shell and agent setup.

# Repository map

- `install.sh`: bootstrap and symlink orchestration.
- `nvim/init.lua`: Neovim entry point and lazy.nvim bootstrap.
- `nvim/lua/plugins/*.lua`: per-plugin specs and config.
- `nvim/lazy-lock.json`: lazy.nvim-managed lock (do not hand-edit).
- `nvim/snippets/`: user snippets (e.g. `go.json`).
- `zsh/.zshrc`, `zsh/aliases.zsh`: shell config and aliases. `zsh/.zprofile`:
  PATH for login shells (launchd); `ZDOTDIR` makes `~/.zprofile` dead. Probe
  with `env -i HOME=$HOME /bin/zsh -lc '...'`, a plain `zsh -lc` inherits PATH.
- `topgrade/`: macOS Stow package; its launchd agent lives outside the repo,
  see `plans/topgrade-autoupdate.md`.
- `tmux/tmux.conf`, `starship/starship.toml`: directly linked configs. `prefix + s` runs
  `tmux/session-picker.sh` (fzf popup; design in `plans/tmux-session-tree-picker.md`).
- macOS Stow packages nest one level, the config lives at
  `aerospace/aerospace/aerospace.toml`, `ghostty/ghostty/config`,
  `karabiner/karabiner/karabiner.json`, `topgrade/topgrade/topgrade.toml`.
  `yazi/yazi.toml`, `nvim/`, `zsh/` are flat (stowed into `~/.config/<tool>`).
- `anki/`: Anki add-on source and card templates, symlinked into `addons21`;
  edits and checks: `anki-addon` skill.
- `zen/`, `obsidian/`: macOS themes, checked by their `preview.py` + `check*`.
- Agent configuration directories hold global guidance, native roles, skills,
  themes and setup checks; concrete installation paths are documented in `README.md`.
  Private facts stay outside the repository; `.githooks/pre-commit` checks staged
  lines against the configured private denylist.
- `plans/`: implementation plans (`<task-name>.md`).
- `notes/`: personal reference notes, not workflow docs.
- `everything.md`: Russian stack/keymap cheatsheet, derived from configs and sometimes stale.
- `AGENTS.md`: the canonical regular instruction file; edit this file.
  Compatibility instruction filenames link to it.
- `README.md`: user-facing setup.
- `assets/screenshots/`: README shots of a made-up demo; retake: `readme-screenshots` skill.
- Project skills: `setup-dotfiles`, `docs-sync`, `readme-screenshots`.

# Planning for the implementer

For non-trivial tasks (behavioral change, new tool, refactor); a mechanical
rename or a value/flag swap of a few lines skips the plan and goes straight
to edit:

1. Read the relevant configs first: never guess Neovim/Stow/shell behavior.
2. State current behavior in one or two sentences.
3. Write the plan to `plans/<task-name>.md` (or `PLAN.md` if `plans/` is
   missing). Reference exact paths, state what must not change, bound scope.
4. No OK wait: start the `/feature` cycle on the plan right away.

# Review after implementation

Review the implementer's diff before approving, in this order:

1. Followed the plan; changes minimal and scoped.
2. Scope creep: unrelated files, renames, reformatting.
3. Symlink/Stow assumptions (target paths, package layout, OS branching).
4. Keybindings, aliases, and other user-facing behavior preserved.
5. Generated files left to their generator (`nvim/lazy-lock.json`,
   `karabiner/.../automatic_backups/`).
6. Security: no secrets, tokens, machine-specific URLs, or weakened validation.

Prioritize blocking issues. Suggest minimal fixes; no broad refactors unless
necessary.

# `/feature` in this repo

Every non-trivial task runs the installed `feature` workflow, explicitly invoked
or not, with no OK wait. Use its available runtime adapter. Overrides here:

- Plan: the skill's sections plus Edge cases (macOS vs Linux, missing tools,
  dirty worktree, first run); edits under ~15 lines total make one task.
- Its agents implement and independently review, using their report formats.
- Branch: `git switch -c feat/<slug>` here, no worktree: gates read live paths.
- Shared checkout: before `git switch -c` run `bin/wait-free-checkout.sh` in
  the background (exit 0: clean `main`, no other busy pane reported by the
  configured activity integration). A direct commit needs no open `feat/*`
  branch and is chained after a branch == `main` check.
- Third-party targets outside git: back them up to the existing private backup
  directory before dispatch and gate on `diff` against the backup.
  A lone tracked settings change from an interactive client is committed first
  with a scoped `chore` commit before task changes.
- Final PASS: `git fetch . feat/<slug>:main` (ff-only, moves no file under a
  busy pane), `git switch main`, `git push origin main`, `git branch -d
  feat/<slug>`, overriding "never touch main" and "no remote operations".
  Main moved, no shared file: rm untracked files equal to main's, `git rebase
  main`, Gates, retry. Else (or a stop): report, keep the branch, no force-push.

# Architecture rules

- `install.sh` owns provisioning and link orchestration. Tool behavior belongs
  inside that tool's config directory.
- Neovim: global options and lazy.nvim bootstrap in `nvim/init.lua`; plugin
  behavior in `nvim/lua/plugins/`.
- Preserve Stow package shape: directory names under macOS packages map into
  `~/.config` intentionally.
- Preserve macOS/Linux branching in `install.sh`. macOS-only tools (Ghostty,
  AeroSpace, Karabiner) must not run on Linux.
- The installer assumes the checkout is at `$HOME/dotfiles`. Any path change
  must be coordinated across every symlink and Stow invocation.

# Verification commands

- `bash -n install.sh`: installer syntax check.
- `zsh -n zsh/.zshrc zsh/.zprofile zsh/aliases.zsh`: zsh syntax check.
- `ghostty +validate-config` (own Bash call: it eats chained output);
  applying is the user's Cmd+Shift+, (osascript has no Accessibility).
- `find nvim -name '*.lua' -print0 | xargs -0 -n1 luac -p`: Lua parse check.
- `find nvim karabiner -name '*.json' -print0 | xargs -0 -n1 jq empty`: JSON
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

- **Context7**: current library/framework/plugin docs, version-specific
  behavior, official examples, migration/configuration patterns. Reach for it
  when working with lazy.nvim, blink.cmp, treesitter, mason, conform, or any
  plugin whose API may have shifted.
- **Firecrawl**: external pages, RFCs, GitHub issues/changelogs, blog posts
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
- Back up live configs outside the repo using their existing private backup convention.
- Prefer small, scoped changes over broad refactoring.

# Documentation gaps

- No architecture, testing, local-development, or agent-workflow docs.
- No documented reload/validation for Karabiner, Starship, Yazi, or lazy.nvim lock updates.

# Maintaining this file

Update only when workflow, architecture, commands or durable conventions change;
no duplication with `README.md`; keep the canonical `AGENTS.md` under 200 lines.
