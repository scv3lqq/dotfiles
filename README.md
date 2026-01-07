# dotfiles

Personal macOS dotfiles managed with GNU Stow.

## Quick Start

```bash
# Clone and stow
git clone <repository-url> ~/.config
brew install stow
cd ~ && stow -d ~/.config -t ~ .

# Install essentials
brew install powerlevel10k zsh-autosuggestions eza bat fzf uv colima docker tmux
brew install --cask font-jetbrains-mono-nerd-font

# Setup tmux plugins
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
```

Then restart your terminal and configure Powerlevel10k with `p10k configure`.

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
- **Terminal**: Alacritty with Alabaster Dark theme
- **Terminal Multiplexer**: Tmux with vim-tmux-navigator and Gruvbox theme
- **Window Manager**: AeroSpace (i3-like tiling for macOS)
- **Editor**: Neovim with Lazy.nvim plugin manager
- **Python**: uv for package management and project scaffolding
- **Container**: Colima (Docker Desktop alternative)
- **Utility Scripts**: Python project scaffolding and package creation tools

## Key Features

- **Vim-style Navigation**: Consistent vim keybindings across tmux, Neovim, and AeroSpace
- **Modern CLI Tools**: eza (ls), bat (cat), fzf (fuzzy finder), z (smart cd)
- **Python Development**: Pre-configured uv workflows with FastAPI support
- **Smart Completions**: Context-aware FZF previews with file/directory awareness
- **Tiling Window Manager**: i3-like workspace management with multi-monitor support
- **Session Persistence**: Tmux sessions with automatic save/restore capability
- **Developer Aliases**: Shortcuts for common tasks (uv, docker, git, etc.)

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

1. Install Oh My Zsh if not already installed:
   ```bash
   sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
   ```

2. Install Powerlevel10k theme via Homebrew:
   ```bash
   brew install powerlevel10k
   ```

3. Install zsh plugins via Homebrew:
   ```bash
   brew install zsh-autosuggestions
   ```

4. Install required CLI tools:
   ```bash
   brew install eza bat fzf uv colima docker tmux
   ```

5. Install Tmux Plugin Manager (TPM):
   ```bash
   git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
   ```
   Then open tmux and press `Ctrl+a` + `I` to install plugins

6. Install JetBrainsMono Nerd Font:
   ```bash
   brew install --cask font-jetbrains-mono-nerd-font
   ```

7. Open Neovim to automatically install plugins via Lazy.nvim

8. Configure AeroSpace to start at login

9. (Optional) Run Powerlevel10k configuration wizard:
   ```bash
   p10k configure
   ```

## Documentation

See [CLAUDE.md](./CLAUDE.md) for detailed configuration architecture and guidance when working with these dotfiles.
