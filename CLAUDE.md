# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a macOS dotfiles repository containing configuration files for a development environment. The main configuration is tracked in Git and located at `~/.config`.

## Key Technologies & Tools

- **Shell**: Zsh with Oh My Zsh framework (custom directory: `~/.config/oh-my-zsh`)
- **Terminal**: Alacritty (GPU-accelerated terminal emulator)
- **Window Manager**: AeroSpace (i3-like tiling window manager for macOS)
- **Editor**: Neovim (Lua-based configuration using Lazy.nvim plugin manager)
- **Python**: uv (Python package manager and environment tool)
- **Container**: Docker via Colima (Docker Desktop alternative)

## Configuration Structure

### Shell Configuration (.zshrc)
Located at `.zshrc` in this directory. Key aspects:
- Uses Powerlevel10k theme
- Oh My Zsh custom directory: `$HOME/.config/oh-my-zsh`
- Active plugins: git, poetry, poetry-env, z, fzf, eza, colored-man-pages, gitignore, git-prompt, history, docker
- Custom aliases defined in `oh-my-zsh/aliases.zsh`
- Docker host: `unix:///$HOME/.colima/docker.sock`
- FZF integration with eza and bat for file previews

### Custom Shell Aliases (oh-my-zsh/aliases.zsh)
- `n` → nvim
- `fdev` → uv run fastapi dev
- `ud` → uv add (add dependency)
- `ur` → uv run (run command)
- `ut` → uv tree (show dependency tree)
- `ls` → eza with icons and git info
- `cd` → z (smart directory jumper)
- `pg` → pass generate -c (password manager)
- `doc` → docker compose
- `dex` → docker exec
- `lzd` → lazydocker

### Neovim Configuration (nvim/)
Structure:
- Entry point: `nvim/init.lua` → loads `scv3lqq.core` and `scv3lqq.lazy`
- Plugin manager: Lazy.nvim
- Plugins directory: `nvim/lua/scv3lqq/plugins/`
- Core config: `nvim/lua/scv3lqq/core/` (keymaps, options)
- LSP config: `nvim/lua/scv3lqq/plugins/lsp/` (mason, lspconfig)
- Leader key: Space

Key plugins installed:
- blink-cmp (completion)
- conform-nvim (formatting)
- nvim-linting (linting)
- telescope (fuzzy finder)
- treesitter (syntax highlighting)
- lazygit (git integration)
- nvim-tree (file explorer)
- trouble (diagnostics)
- gitsigns (git signs)
- vim-tmux-navigator (tmux integration)

### AeroSpace (aerospace/aerospace.toml)
i3-like tiling window manager for macOS:
- Leader: Alt key
- Navigation: Alt + h/j/k/l (vim-style)
- Move windows: Alt + Shift + h/j/k/l
- Workspaces: 1-9 and named workspaces (w=web, t=terminal, s=spotify, m=messenger, o=obsidian, g=chrome)
- Service mode: Alt + Shift + ; (for layout management)
- App launcher shortcuts:
  - Alt + Enter → Alacritty
  - Alt + b → Vivaldi browser
  - Alt + c → Spotify
  - Alt + z → Obsidian
- Auto-assignment: Apps automatically move to designated workspaces on launch

### Alacritty (alacritty/alacritty.toml)
- Theme: Gruvbox Material Medium Dark
- Font: JetBrainsMono Nerd Font (size 10)
- Opacity: 0.5
- Option key as Alt on both sides

## Utility Scripts (bash_scripts/)

### ppkg
Creates an empty Python package with `__init__.py` in a new directory, then spawns a new shell in that directory.

### start_py
Scaffolds a complete Python project with:
- uv initialization (app mode)
- .gitignore from toptal.com/developers/gitignore
- pyrightconfig.json with recommended type checking
- Removes default main.py

Usage: Run `start_py`, then enter project name when prompted.

## Workflow Notes

### Python Development
- Primary tool: `uv` for dependency management and running commands
- FastAPI development: Use `fdev` alias (uv run fastapi dev)
- Type checking: Pyright is configured via pyrightconfig.json
- Docker runs via Colima (not Docker Desktop)

### Git Workflow
- Currently on `main` branch
- Recent commits show focus on Docker aliases and aerospace configuration
- Has uncommitted changes to `aerospace/aerospace.toml`

### Navigation
- Use `z` for smart directory jumping (aliased to `cd`)
- FZF is configured with bat/eza previews for files and directories
- Nvim and tmux are integrated with vim-tmux-navigator

## File Locations Reference

- Zsh config: `.zshrc`
- Zsh aliases: `oh-my-zsh/aliases.zsh`
- Neovim config: `nvim/init.lua`
- Alacritty config: `alacritty/alacritty.toml`
- AeroSpace config: `aerospace/aerospace.toml`
- Utility scripts: `bash_scripts/`
