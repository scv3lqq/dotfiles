# dotfiles

macOS development environment + Linux server configs: Neovim · tmux · Zsh · Starship.

## Setup

### macOS

> Requires Xcode Command Line Tools: `xcode-select --install`

```sh
git clone https://github.com/scv3lqq/dotfiles.git ~/dotfiles
cd ~/dotfiles && ./install.sh
```

`install.sh` installs Homebrew, all CLI tools, and macOS apps automatically.

### Linux server

```sh
git clone https://github.com/scv3lqq/dotfiles.git ~/dotfiles
cd ~/dotfiles && ./install.sh
```

`install.sh` detects Linux and installs only server-relevant tools (neovim, tmux, starship, zsh, stow) via apt/dnf. macOS-only configs (Ghostty, AeroSpace, Karabiner) are skipped.

**After install:**

1. Reconnect to the server so zsh becomes the default shell
2. Install tmux plugins — open tmux, then press `Ctrl+a` then `Shift+i`
3. Install nvim plugins — run `nvim`, lazy.nvim will install everything automatically

## Requirements

### macOS apps (install manually)

| App | Purpose |
|---|---|
| [Ghostty](https://ghostty.org) | Terminal |
| [AeroSpace](https://github.com/nikitabobko/AeroSpace) | Window manager |
| [Karabiner-Elements](https://karabiner-elements.pqrs.org) | Keyboard remapping |
| [Vivaldi](https://vivaldi.com) | Browser |
| [Obsidian](https://obsidian.md) | Notes |
| [Telegram](https://telegram.org) | Messenger |
| [Spotify](https://spotify.com) | Music |

### macOS CLI tools (via Homebrew, handled by install.sh)

```sh
brew install neovim starship tmux fzf fd bat eza lazygit lazydocker \
  zsh-fast-syntax-highlighting zsh-autosuggestions zsh-completions
brew install --cask font-jetbrains-mono-nerd-font
```

### Linux server (handled by install.sh)

```sh
# apt-based (Ubuntu/Debian)
sudo apt-get install -y stow zsh tmux curl git

# Neovim (latest)
curl -LO https://github.com/neovim/neovim/releases/latest/download/nvim-linux-x86_64.tar.gz
sudo tar -C /usr/local -xzf nvim-linux-x86_64.tar.gz --strip-components=1

# Starship
curl -sS https://starship.rs/install.sh | sh
```

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
| `gp` | git push |
| `gcof` | checkout branch via fzf |
| `lzd` | lazydocker |
| `fkill` | kill process via fzf |
