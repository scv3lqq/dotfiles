# dotfiles

Personal macOS dotfiles managed with GNU Stow.

## Installation

This repository uses [GNU Stow](https://www.gnu.org/software/stow/) to symlink configuration files to their proper locations.

```bash
# Clone the repository to ~/.config
git clone <repository-url> ~/.config

# Install stow if not already installed
brew install stow

# Navigate to the parent directory
cd ~

# Use stow to create symlinks
stow -d ~/.config -t ~ .
```

**Note**: Stow will create symlinks from `~/.config` to your home directory. Existing files may need to be backed up or removed before stowing.

## What's Included

- **Shell**: Zsh with Oh My Zsh and Powerlevel10k theme
- **Terminal**: Alacritty with Gruvbox Material theme
- **Window Manager**: AeroSpace (i3-like tiling for macOS)
- **Editor**: Neovim with Lazy.nvim plugin manager
- **Python**: uv for package management
- **Docker**: Colima setup (Docker Desktop alternative)
- **Utility Scripts**: Python project scaffolding tools

## Requirements

- macOS
- [Homebrew](https://brew.sh/)
- [Oh My Zsh](https://ohmyz.sh/)
- [Powerlevel10k](https://github.com/romkatv/powerlevel10k)
- [GNU Stow](https://www.gnu.org/software/stow/)
- JetBrainsMono Nerd Font

## Key Tools

- **Aerospace** https://github.com/nikitabobko/AeroSpace
- **Alacritty** https://alacritty.org/
- **Oh-my-zsh** https://ohmyz.sh/
- **Tmux** https://github.com/tmux/tmux
- **Neovim** https://neovim.io/
- **uv** https://github.com/astral-sh/uv

## Post-Installation

After stowing the dotfiles:

1. Install Oh My Zsh if not already installed
2. Install Powerlevel10k theme for Oh My Zsh
3. Install zsh plugins via Homebrew:
   ```bash
   brew install zsh-autosuggestions zsh-syntax-highlighting
   ```
4. Install required tools:
   ```bash
   brew install eza bat fzf uv colima docker
   ```
5. Open Neovim to automatically install plugins via Lazy.nvim
6. Configure AeroSpace to start at login

## Documentation

See [CLAUDE.md](./CLAUDE.md) for detailed configuration architecture and guidance when working with these dotfiles.
