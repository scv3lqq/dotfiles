# dotfiles

Personal macOS development environment managed with [GNU Stow](https://www.gnu.org/software/stow/).

## What's included

| Directory / File | Tool | Purpose |
|---|---|---|
| `zsh/` | Zsh | Shell config, aliases, plugins |
| `nvim/` | Neovim | Editor with Lazy.nvim |
| `ghostty/` | Ghostty | Terminal emulator |
| `aerospace/` | AeroSpace | Tiling window manager |
| `karabiner/` | Karabiner-Elements | Keyboard remapping |
| `starship.toml` | Starship | Shell prompt |
| `.tmux.conf` | tmux | Terminal multiplexer |

---

## Fresh macOS setup

### 1. Install Xcode Command Line Tools

```sh
xcode-select --install
```

### 2. Install Homebrew

```sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the post-install instructions to add Homebrew to your PATH.

### 3. Clone this repo

```sh
git clone https://github.com/<your-username>/dotfiles.git ~/dotfiles
```

### 4. Install packages

```sh
brew install stow neovim tmux starship fzf fd bat eza zsh-fast-syntax-highlighting zsh-autosuggestions zsh-completions lazygit lazydocker
```

```sh
brew install --cask ghostty aerospace karabiner-elements
```

Install a Nerd Font (Ghostty config uses JetBrainsMono Nerd Font):

```sh
brew install --cask font-jetbrains-mono-nerd-font
```

### 5. Symlink configs with Stow

Run from inside the `~/dotfiles` directory:

```sh
cd ~/dotfiles
```

Configs that live in `~/.config/`:

```sh
stow --target ~/.config nvim ghostty aerospace karabiner
```

Zsh config — `ZDOTDIR` is set to `~/.config/zsh`, so stow there:

```sh
mkdir -p ~/.config/zsh
stow --target ~/.config/zsh zsh
```

Starship and tmux:

```sh
ln -sf ~/dotfiles/starship.toml ~/.config/starship.toml
ln -sf ~/dotfiles/.tmux.conf ~/.tmux.conf
```

### 6. Set Zsh as default shell (if not already)

```sh
chsh -s /bin/zsh
```

### 7. Restart your terminal

Open Ghostty. Neovim plugins will auto-install via Lazy.nvim on first launch:

```sh
nvim
```

---

## AeroSpace keybindings (window manager)

| Key | Action |
|---|---|
| `Alt + h/j/k/l` | Focus window left/down/up/right |
| `Alt + Shift + h/j/k/l` | Move window |
| `Alt + 1-9` | Switch workspace |
| `Alt + Shift + 1-9` | Move window to workspace |
| `Alt + /` | Toggle tiles layout |
| `Alt + ,` | Toggle accordion layout |
| `Alt + Tab` | Switch to previous workspace |
| `Alt + Shift + Tab` | Move workspace to next monitor |
| `Alt + Enter` | Open Ghostty |
| `Alt + b` | Open Vivaldi |
| `Alt + z` | Open Obsidian |
| `Alt + Shift + ;` | Enter service mode |

Apps are auto-assigned to workspaces: Ghostty → `t`, Vivaldi → `w`, Spotify → `s`, Telegram → `m`, Obsidian → `o`, Chrome → `g`.

---

## Zsh aliases

| Alias | Command |
|---|---|
| `n` | `nvim` |
| `nf` | Open file in nvim via fzf |
| `lzd` | `lazydocker` |
| `gst` | `git status` |
| `gcof` | Checkout git branch via fzf |
| `fkill` | Kill process via fzf |
| `ll` | `ls -lah` |

---

## Updating configs

Symlinks point directly into the repo, so after `git pull` changes are active immediately — no re-stowing needed.

```sh
cd ~/dotfiles && git pull
```

If you add a **new file** to an existing package, re-run stow for that package:

```sh
stow --target ~/.config nvim   # or whichever package
```
