# topgrade daily auto-update (macOS)

Status: implemented 2026-09-21, topgrade 17.12.1. No real update run yet: the
first one is done by hand in a terminal (it also updates Claude Code).

## Goal

`topgrade` updates brew formulae/casks, TPM plugins, rustup, pipx, uv, npm
globals, gh extensions, VS Code extensions, Claude Code, Yazi packages.
launchd runs it daily at 22:00. Ghostty updates itself via its built-in updater.

Non-goals: macOS system updates (needs sudo), `greedy_cask`, Linux support.

## What was set up

- `topgrade/topgrade/topgrade.toml`: new Stow package, folded into
  `~/.config/topgrade` (second lookup path per topgrade README).
  `assume_yes`, `ask_retry = false`, `cleanup`, `notify_end = "on_failure"`,
  `[brew] autoremove`, post command `brew bundle dump --global --force`
  (writes `~/.Brewfile`). Option names verified against `config.example.toml`
  at tag v17.12.1.
- `zsh/.zprofile`: new, linked to `$ZDOTDIR/.zprofile` by the `zsh` package.
  `~/.zshenv` sets `ZDOTDIR=~/.config/zsh`, so `~/.zprofile` is never read and
  login shells (launchd) had no brew PATH at all. Holds guarded
  `brew shellenv`, `~/.local/bin`, `~/go/bin`, guarded Obsidian CLI path
  (moved from the dead `~/.zprofile`, which is left in place).
- `~/Library/LaunchAgents/local.topgrade.plist`: regular file, outside the
  repo (no launchd convention here). `/bin/zsh -lc topgrade`, 22:00 daily,
  stdout+stderr to `~/Library/Logs/topgrade.log`.
- `ghostty/ghostty/config`: `auto-update = download`,
  `auto-update-channel = stable`. The cask is `auto_updates`, so brew skips it
  without `--greedy`.
- `install.sh`: `topgrade` added to the macOS `brew install` list and to the
  macOS `stow --restow --target ~/.config` line.
- `brew pin mysql` (machine state, not in repo); `postgresql@17` untouched.
- Backups: `~/.claude/backups/{ghostty-config,install.sh,home-zprofile}.bak-2026-09-21`.

## Disabled steps

| Step | Why |
| --- | --- |
| `system` | macOS updates need sudo, handled by System Settings |
| `vim` | `Lazy sync` would rewrite `nvim/lazy-lock.json` daily and dirty the repo |
| `containers` | fails whenever Docker is not running: false failure notification |
| `colima` | `colima update` fails whenever the VM is not running |
| `git_repos` | would `git pull` `~/dotfiles`, whose worktree is live via symlinks |

## Steps that run (clean-env dry-run)

Brew (update, upgrade, cleanup, autoremove), Brew Cask (no greedy), tmux
plugins, rustup, pipx, VS Code extensions, npm global, gh extensions, Claude
Code + plugin marketplaces, uv, Yazi packages, then the Brewfile post command.
Skipped for missing prerequisites: cargo (`cargo-update`), App Store (`mas`),
poetry, gem, pip3.

tmux step (`src/steps/tmux.rs`, identical in v17.11.0 and v17.12.1):
`$TMUX_PLUGIN_MANAGER_PATH/tpm/bin/update_plugins` if the variable is set,
else `~/.config/tmux/plugins/tpm`, else `~/.tmux/plugins/tpm`. Both the
clean-env and the inside-tmux dry-run resolve to
`~/.tmux/plugins/tpm/bin/update_plugins all`.

## Operate

- Run now: `launchctl kickstart -k gui/$(id -u)/local.topgrade`
- Inspect: `launchctl print gui/$(id -u)/local.topgrade`
- Log: `~/Library/Logs/topgrade.log` (appended, never rotated)
- Disable: `launchctl bootout gui/$(id -u)/local.topgrade`
- Re-enable: `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.topgrade.plist`
- Preview as launchd sees it: `env -i HOME=$HOME /bin/zsh -lc 'topgrade --dry-run'`

## Edge cases

- Mac asleep at 22:00: launchd fires the missed job on wake; powered off: skipped.
- A cask that asks for a password fails unattended: `on_failure`
  notification, the rest of the run continues.
- The 22:00 run executes `claude update` even if a Claude Code session is open.
- Interactive login shells get `brew shellenv` twice (`.zprofile` + `.zshrc`):
  duplicate PATH entries only.
- New machine: `install.sh` links the config but does not create the launchd
  agent; recreate the plist by hand from the section above.

## Rollback

`launchctl bootout gui/$(id -u)/local.topgrade`, remove the plist,
`stow -d ~/dotfiles -D --target ~/.config topgrade`, remove `zsh/.zprofile`
and restow `zsh`, revert `ghostty/ghostty/config` and `install.sh`,
`brew unpin mysql`, `brew uninstall topgrade`.

## Manual TODO (user)

- [ ] First real run by hand in a terminal, outside a Claude Code session: `topgrade`
- [ ] System Settings → General → Software Update: enable automatic security updates
- [ ] Restart Ghostty to pick up the auto-update keys
- [ ] After brew upgrades tmux: restart the tmux server at a convenient time
- [ ] Notifications: allow Script Editor (osascript test) and topgrade in
      System Settings → Notifications if banners do not show
