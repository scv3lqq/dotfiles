# Agent role

- Codex implements requested changes, tests, refactors, and bug fixes.
- Follow the existing layout and style; keep diffs small and scoped.
- Follow an approved plan file when one is present.
- Stop and explain when a plan conflicts with the repository or is unsafe.
- Leave research, architecture exploration, and review to Claude Code unless
  implementation requires targeted external documentation.

# Repository map

- `install.sh`: macOS/Linux bootstrap, package installation, and symlink setup.
- `nvim/init.lua`: Neovim entry point and lazy.nvim bootstrap.
- `nvim/lua/plugins/`: Neovim plugin declarations and configuration.
- `nvim/lazy-lock.json`: lazy.nvim-managed dependency lock file.
- `zsh/`: Zsh startup configuration and aliases.
- `.tmux.conf` and `starship.toml`: directly linked user-level configs.
- `aerospace/`, `ghostty/`, `karabiner/`, `nvim/`, `yazi/`, and `zsh/`:
  GNU Stow packages with target-specific directory shapes.
- `notes/`: user reference notes, not project workflow documentation.

# Commands

- Full install/bootstrap: `./install.sh`. This installs system packages, rewrites
  symlinks and `~/.zshenv`, may replace `~/.config/karabiner`, and may change the
  login shell. Run only deliberately.
- Start the configured editor: `nvim`
- Check installer syntax: `bash -n install.sh`
- Check Zsh syntax: `zsh -n zsh/.zshrc zsh/aliases.zsh`
- Parse Neovim Lua: `find nvim -name '*.lua' -print0 | xargs -0 -n1 luac -p`
- Validate tracked JSON shapes:
  `find nvim karabiner -name '*.json' -print0 | xargs -0 -n1 jq empty`

# Needs verification

- Aggregate checks: no CI, test suite, Makefile, Taskfile, or Justfile exists;
  `just check` is not available in this repository.
- Linting and repository-wide formatting: no standalone command is documented.
- Neovim plugin lock regeneration: lazy.nvim owns `nvim/lazy-lock.json`, but no
  repeatable update command is documented.
- Runtime validation/reload commands for AeroSpace, Ghostty, Karabiner, tmux,
  Starship, and Yazi are not documented.

# Implementation rules

- Keep changes minimal and limited to the requested tool or workflow.
- Do not refactor, format, rename, or reorder unrelated files.
- Do not add dependencies unless necessary; explain the reason and impact.
- Follow each tool's existing error handling, logging, and configuration style.
- Preserve keybindings, aliases, paths, and other user-facing behavior unless
  the request explicitly changes them.
- Preserve public/config compatibility when practical. For intentional breaking
  changes, update relevant docs and describe migration impact.
- Treat edits as live: installation creates symlinks into this repository.
- Do not run `install.sh` as a routine validation command.

# Testing policy

- Run the smallest relevant syntax or parse check first after code/config edits.
- Run all applicable commands in `Commands` when shared installer or Neovim
  configuration behavior changes.
- Add focused regression coverage if an automated test harness is introduced.
- Manually inspect behavior-sensitive config changes when no validator exists.
- If a check cannot run, state why and give the exact command for the user.

# Architecture boundaries

- Keep provisioning and link orchestration in `install.sh`; keep tool behavior in
  that tool's config directory.
- Keep Neovim global options and lazy.nvim bootstrap in `nvim/init.lua`; keep
  plugin-specific behavior in `nvim/lua/plugins/`.
- Preserve the Stow layout and target assumptions in `install.sh`. The repeated
  directory names under macOS packages map into `~/.config` intentionally.
- Preserve macOS/Linux branching. Do not make macOS-only packages run on Linux.
- The installer assumes the checkout is at `$HOME/dotfiles`; coordinate any path
  change across every symlink and Stow invocation.

# External research tools

- Prefer local code, lock files, and established repository patterns first.
- Use Context7 when current or unfamiliar library/framework/API behavior,
  version details, or a documentation mismatch affects implementation.
- Use Firecrawl when a task references an external page, RFC, issue, changelog,
  or URL and local context is insufficient.
- Prefer official documentation and keep research narrowly task-focused.
- Summarize the source used and how it affected the implementation.

# Database and migrations

- This repository currently has no database or migrations.
- If migrations are introduced, do not edit ones already applied in production;
  create a new migration for schema changes.
- Document destructive changes and migration or rollback impact.
- Never drop columns, tables, or data without explicit confirmation.

# Generated files

- Do not manually edit generated or tool-managed files when a source exists.
- Change Neovim plugin specs first; let lazy.nvim update `nvim/lazy-lock.json`.
- Treat `karabiner/karabiner/automatic_backups/` as tool-produced snapshots.
- Run a verified generator when one becomes documented; otherwise report the gap.

# Security rules

- Never commit or log secrets, tokens, passwords, credentials, or personal data.
- Do not weaken authentication, authorization, validation, or TLS settings unless
  explicitly requested.
- Validate external input in scripts. Quote shell values and handle file paths,
  downloads, deserialization, and destructive commands carefully.
- Do not add private URLs or machine-specific credentials to tracked configs.

# Git rules

- Do not create commits or push unless explicitly requested.
- Never force push, rewrite history, or modify unrelated files.
- Do not change `.env`, secrets, credentials, or production configuration unless
  explicitly requested.
- Preserve existing user changes in a dirty worktree.
- When a commit is requested, use an imperative Conventional Commit subject no
  longer than 72 characters and include no agent attribution.

# Handoff summary

After implementation, always report:

1. What changed.
2. Files changed.
3. Tests and checks run.
4. Tests and checks not run, with reasons.
5. Risks or assumptions.
6. Suggested review focus.

# Docs references

- Setup and usage: [`README.md`](README.md)

# Documentation gaps

- There are no dedicated architecture, testing, local-development, or agent
  workflow documents.
- There is no documented validation matrix for the individual tool configs.

# Maintaining this file

- Update `AGENTS.md` only when workflows, architecture, commands, or durable
  conventions change.
- Keep rules actionable, remove outdated guidance, and avoid duplication.
- Do not add temporary TODOs, task notes, backlog items, implementation details,
  or content already maintained in `README.md` or another document.
- Keep this file under 200 lines.
