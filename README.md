# dotfiles

Personal macOS development environment: Ghostty · Neovim · AeroSpace · Zsh · Starship · tmux · Karabiner.

## Requirements

**macOS apps** (install manually):

| App | Purpose |
|---|---|
| [Ghostty](https://ghostty.org) | Terminal |
| [AeroSpace](https://github.com/nikitabobko/AeroSpace) | Window manager |
| [Karabiner-Elements](https://karabiner-elements.pqrs.org) | Keyboard remapping |
| [Vivaldi](https://vivaldi.com) | Browser |
| [Obsidian](https://obsidian.md) | Notes |
| [Telegram](https://telegram.org) | Messenger |
| [Spotify](https://spotify.com) | Music |

**CLI tools** (via Homebrew):

```sh
brew install neovim starship tmux fzf lazydocker
brew install font-jetbrains-mono-nerd-font
```

## Setup

```sh
git clone https://github.com/scv3lqq/dotfiles.git ~/dotfiles
cd ~/dotfiles && ./install.sh
```

> Requires Xcode Command Line Tools: `xcode-select --install`

## Updating

```sh
cd ~/dotfiles && git pull
```

Symlinks point directly into the repo — changes are active immediately.

---

## AeroSpace keybindings

| Key | Action |
|---|---|
| `Alt + h/j/k/l` | Focus window |
| `Alt + Shift + h/j/k/l` | Move window |
| `Alt + 1-9` | Switch workspace |
| `Alt + Shift + 1-9` | Move window to workspace |
| `Alt + Tab` | Previous workspace |
| `Alt + Shift + Tab` | Move workspace to next monitor |
| `Alt + /` | Toggle tiles layout |
| `Alt + ,` | Toggle accordion layout |
| `Alt + Enter` | Open Ghostty |
| `Alt + b` | Open Vivaldi |
| `Alt + z` | Open Obsidian |
| `Alt + Shift + ;` | Service mode |

Auto workspace assignment: Ghostty → `t`, Vivaldi → `w`, Spotify → `s`, Telegram → `m`, Obsidian → `o`, Chrome → `g`.

## Aliases

| Alias | |
|---|---|
| `n` | nvim |
| `nf` | nvim via fzf |
| `gst` | git status |
| `gcof` | checkout branch via fzf |
| `lzd` | lazydocker |
| `fkill` | kill process via fzf |
