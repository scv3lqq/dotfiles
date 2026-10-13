# dotfiles

macOS development environment + Linux server configs: Neovim · tmux · Zsh · Starship · Yazi.

## Setup

### macOS

> Requires Xcode Command Line Tools: `xcode-select --install`

```sh
git clone https://github.com/scv3lqq/dotfiles.git ~/dotfiles
cd ~/dotfiles && ./install.sh
```

`install.sh` installs Homebrew, all CLI tools, and the casks below (Ghostty,
Karabiner-Elements, AeroSpace, JetBrains Mono Nerd Font).

### Linux server

```sh
git clone https://github.com/scv3lqq/dotfiles.git ~/dotfiles
cd ~/dotfiles && ./install.sh
```

`install.sh` detects Linux and installs only server-relevant tools (neovim,
tmux, starship, zsh, stow, jq) via apt/dnf. macOS-only configs (Ghostty,
AeroSpace, Karabiner, topgrade) are skipped.

### After install (both platforms)

1. Open a new shell (or reconnect to the server) so zsh becomes the default shell
2. Install tmux plugins: open tmux, then press `Ctrl+a` then `Shift+i`
3. Install nvim plugins: run `nvim`, lazy.nvim installs everything automatically
4. Verified commits: `install.sh` signs commits in this repo with
   `~/.ssh/id_ed25519.pub`; to register it on GitHub run
   `gh auth refresh -h github.com -s admin:ssh_signing_key`, then `./install.sh` again
5. macOS: restart Claude Code (it may rewrite `~/.claude.json` from memory) and
   allow `terminal-notifier` in System Settings → Notifications on the first alert

The checkout must live at `$HOME/dotfiles`: every symlink and Stow call assumes it.

## What gets installed

### macOS apps (install manually)

| App | Purpose |
|---|---|
| [Zen](https://zen-browser.app) | Browser |
| [Obsidian](https://obsidian.md) | Notes |
| [Telegram](https://telegram.org) | Messenger |
| [Spotify](https://spotify.com) | Music |

### macOS (via Homebrew, handled by install.sh)

```sh
brew install stow neovim tmux starship fzf fd bat eza yazi jq \
  zsh-fast-syntax-highlighting zsh-autosuggestions zsh-completions \
  lazygit lazydocker topgrade
brew install --cask ghostty karabiner-elements font-jetbrains-mono-nerd-font
brew install --cask nikitabobko/tap/aerospace
```

### Linux server (handled by install.sh)

```sh
# apt-based (Ubuntu/Debian); dnf is handled too
sudo apt-get install -y stow zsh curl git jq tmux

# Neovim (latest release tarball into /usr/local)
curl -LO https://github.com/neovim/neovim/releases/latest/download/nvim-linux-x86_64.tar.gz
sudo tar -C /usr/local -xzf nvim-linux-x86_64.tar.gz --strip-components=1

# Starship
curl -sS https://starship.rs/install.sh | sh
```

## Layout

| Path | Linked to | Notes |
|---|---|---|
| `nvim/` | `~/.config/nvim` | lazy.nvim, plugin specs in `nvim/lua/plugins/` |
| `zsh/` | `~/.config/zsh` | `install.sh` writes `ZDOTDIR` into `~/.zshenv`, so `~/.zshrc` and `~/.zprofile` are unused |
| `yazi/` | `~/.config/yazi` | file manager |
| `ghostty/`, `aerospace/`, `karabiner/`, `topgrade/` | `~/.config/*` | macOS only, via Stow |
| `starship.toml` | `~/.config/starship.toml` | prompt |
| `.tmux.conf` | `~/.tmux.conf` | TPM cloned into `~/.tmux/plugins/tpm` |
| `anki/terminal_theme/` | `Anki2/addons21/terminal_theme` | Anki add-on; symlinked by hand, not by `install.sh` (`anki/cards/` holds card templates) |
| `claude/hooks/notify.sh` | `~/.claude/hooks/notify.sh` | macOS only; Claude Code Stop hook, `install.sh` also wires it into `~/.claude/settings.json` |
| `notes/`, `plans/`, `everything.md` | | personal notes, implementation plans, Russian cheatsheet |

Symlinks point directly into the repo: edits are live.

## Updating

```sh
cd ~/dotfiles && git pull
```

On macOS `topgrade` upgrades brew/casks/rust/etc.; a launchd agent at
`~/Library/LaunchAgents/local.topgrade.plist` runs it daily at 22:00. The
agent lives outside the repo and has to be recreated by hand on a new machine,
see `plans/topgrade-autoupdate.md`. `system`, `vim`, `git_repos`, `containers`
and `colima` steps are disabled on purpose (`topgrade/topgrade/topgrade.toml`).

---

## tmux

Prefix is `Ctrl+a`.

| Key | Action |
|---|---|
| `prefix` + `c` | New window in the current path |
| `prefix` + <code>&#124;</code> / `-` | Split horizontally / vertically |
| `prefix` + `h/j/k/l` | Resize pane (repeatable) |
| `prefix` + `m` | Zoom pane |
| `prefix` + `s` | Session/window switcher popup (fzf, `Ctrl+d` kills a session) |
| `prefix` + `r` | Reload `~/.tmux.conf` |
| `Ctrl+h/j/k/l` | Move between nvim splits and tmux panes (vim-tmux-navigator) |

Plugins: tpm, vim-tmux-navigator, tmux-sessionist, tmux-dotbar, tmux-resurrect,
tmux-continuum, tmux-assistant-resurrect (restores AI assistant sessions).

## AeroSpace keybindings

| Key | Action |
|---|---|
| `Alt + h/j/k/l` | Focus window |
| `Alt + Shift + h/j/k/l` | Move window |
| `Alt + Shift + -` / `Alt + Shift + =` | Resize window ±50 |
| `Alt + 1-9` | Switch workspace |
| `Alt + w/t/s/m/o/g/p` | Switch to named workspace |
| `Alt + Shift + 1-9` | Move window to workspace |
| `Alt + Tab` | Previous workspace |
| `Alt + Shift + Tab` | Move workspace to next monitor |
| `Alt + /` | Toggle tiles layout |
| `Alt + ,` | Toggle accordion layout |
| `Alt + Enter` | Open Ghostty |
| `Alt + b` | Open Zen |
| `Alt + z` | Open Obsidian |
| `Alt + Shift + ;` | Service mode |

Auto workspace assignment: Ghostty → `t`, Zen → `w`, Spotify → `s`,
Telegram → `m`, Obsidian → `o`, Chrome → `g`.

## Shell

| Alias | |
|---|---|
| `n` / `nf` | nvim / nvim via fzf |
| `y` | yazi, cd's to the directory you exit in |
| `gst` / `gp` / `gpl` | git status / push / pull |
| `gl` | git log, graph + decorations |
| `gcof` | checkout branch via fzf |
| `lzd` | lazydocker |
| `md` | mkdir -p |
| `fkill` | kill process via fzf |
| `tmux-reload` | re-source `.zshrc` in every tmux pane |

`ll`, `la`, `..`, `...` and the fzf previews (`bat` for files, `eza --tree` for
directories) come from `zsh/.zshrc`.

## Verifying config changes

```sh
bash -n install.sh                                     # installer syntax
zsh -n zsh/.zshrc zsh/.zprofile zsh/aliases.zsh        # zsh syntax
ghostty +validate-config                               # Ghostty config
find nvim -name '*.lua' -print0 | xargs -0 -n1 luac -p # Lua parse
find nvim karabiner -name '*.json' -print0 | xargs -0 -n1 jq empty
tmux source-file ~/.tmux.conf                          # apply + validate tmux
```

`./install.sh` mutates `$HOME`, so it is not a check: run it only to provision.
