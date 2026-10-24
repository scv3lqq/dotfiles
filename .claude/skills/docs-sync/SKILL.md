---
name: docs-sync
description: Check or refresh a doc in this repo against the live configs (README.md, everything.md, notes/). Use for "актуален ли README", "проверь everything.md", "обнови README после изменений", or before quoting package lists, keybindings or aliases from a doc. The docs lag the configs, so never trust them as a source.
---

# Doc vs config audit

Docs in this repo are written by hand and lag the configs. Verify every claim
against the file that owns it, then report mismatches before editing anything.

## Claim to source map

| Doc claim | Source of truth |
| --- | --- |
| Package lists, what is installed automatically | `install.sh`: `brew install` / `brew install --cask` lines, `apt-get` / `dnf` lines |
| "install manually" app list | anything NOT in the `--cask` lines of `install.sh` |
| What is linked where, link method | `install.sh` `stow --restow` and `ln -sf` lines |
| Aliases, shell functions | `zsh/aliases.zsh` plus the alias block and `function` defs in `zsh/.zshrc` |
| Prompt, PATH, login-shell behavior | `zsh/.zshrc`, `zsh/.zprofile`; `~/.zshenv` sets `ZDOTDIR`, so `~/.zshrc` and `~/.zprofile` are dead |
| tmux prefix, binds, plugin list | `tmux/tmux.conf` (`set -g prefix`, `bind`, `set -g @plugin`) |
| AeroSpace keys, workspace assignment | `aerospace/aerospace/aerospace.toml` (`alt-*` keys, `if.app-id`) |
| Neovim plugins | `nvim/lua/plugins/*.lua` |
| Auto-update behavior, schedule | `topgrade/topgrade/topgrade.toml` + `plans/topgrade-autoupdate.md` (launchd agent lives outside the repo) |
| Anki add-on | `anki/terminal_theme/`, symlinked into `addons21` by hand, not by `install.sh` |

Stow packages nest one level, so `aerospace/aerospace.toml` does not exist:
grep the nested path (`yazi/yazi.toml`, `nvim/`, `zsh/` are flat).

## Procedure

1. Read the doc fully (`wc -c` first, chunks of 150 lines).
2. Pull the facts, one Bash call per source:
   ```sh
   grep -nE 'brew install|apt-get|dnf|stow |ln -sf|chsh|TPM|zshenv' install.sh
   cat zsh/aliases.zsh; grep -nE '^alias|^function|^\s*function' zsh/.zshrc
   grep -nE 'set -g prefix|^bind|@plugin' tmux/tmux.conf
   grep -nE 'alt-|if.app-id' aerospace/aerospace/aerospace.toml
   ls nvim/lua/plugins
   ```
3. Classify each gap: **wrong** (doc contradicts the config), **stale**
   (feature exists, doc never mentions it), **curated** (deliberate subset,
   e.g. an alias table that skips rarely used aliases: leave it alone).
4. Report wrong first, then stale. Only edit after the user confirms scope.

## Known traps

- Ghostty, Karabiner, AeroSpace are installed by `install.sh` as casks, they
  are not manual installs.
- A "repo layout" section must say that `ZDOTDIR` kills `~/.zshrc`.
- `everything.md` is a Russian cheatsheet: keep it Russian, keep its grouping.
- Rewriting a doc with Write: strip the em dashes the old file carried.
