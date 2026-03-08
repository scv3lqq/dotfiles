# dotfiles

Personal macOS development environment: Ghostty · Neovim · AeroSpace · Zsh · Starship · tmux · Karabiner.

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
| `ggg` | git pull |
| `gcof` | checkout branch via fzf |
| `lzd` | lazydocker |
| `fkill` | kill process via fzf |
