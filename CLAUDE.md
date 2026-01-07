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

## Configuration Architecture

### Shell Configuration (.zshrc)

The ZSH configuration uses Oh My Zsh with a custom directory at `$HOME/.config/oh-my-zsh` (set via `ZSH_CUSTOM`). ZSH_THEME is set to empty string as Powerlevel10k is sourced from Homebrew instead.

**Critical plugins loaded**:
- git, poetry, poetry-env, z, fzf, eza, colored-man-pages, docker
- fast-syntax-highlighting, zsh-completions, golang, python, httpie, kubectl, aliases

**Additional ZSH enhancements** (loaded after Oh My Zsh):
- zsh-autosuggestions (Homebrew)

**Environment configuration**:
- `DOCKER_HOST=unix:///$HOME/.colima/docker.sock` - Colima socket instead of Docker Desktop
- `GPG_TTY=$(tty)` - Required for GPG signing
- PATH additions: `~/.local/bin` (pipx), `~/.cargo/bin` (Rust), `/usr/local/go/bin` (Go), `/opt/homebrew/opt/libpq/bin` (PostgreSQL)
- UV shell completions: `uv generate-shell-completion zsh` and `uvx --generate-shell-completion zsh`

**FZF integration**:
- Ctrl+T preview: Uses eza for directories, bat for files
- Alt+C preview: eza tree view
- Custom completion for cd, ssh, export/unset commands
- Requires bat and eza to be installed

**Additional environment**:
- `HOMEBREW_NO_ENV_HINTS=1` - Disables Homebrew environment hints

### Custom Shell Aliases (oh-my-zsh/aliases.zsh)

**Development shortcuts**:
- `n` → nvim
- `fdev` → uv run fastapi dev
- `ud` → uv add $1
- `ur` → uv run $1
- `ut` → uv tree

**Navigation and tools**:
- `ls` → eza with icons, git info, long format (no filesize, time, user, permissions)
- `pg` → pass generate -c (password manager with clipboard)
- Note: `z` plugin provides smart directory jumping without needing cd alias

**Docker**:
- `doc` → docker compose
- `dex` → docker exec
- `lzd` → lazydocker

### Neovim Configuration (nvim/)

**Module structure**:
- Entry point: `nvim/init.lua` loads two modules: `scv3lqq.core` and `scv3lqq.lazy`
- All configuration uses the `scv3lqq` namespace
- Plugins: `nvim/lua/scv3lqq/plugins/*.lua` (each plugin has its own file)
- LSP: `nvim/lua/scv3lqq/plugins/lsp/` subdirectory

**Key plugins** (nvim/lua/scv3lqq/plugins/):
- blink-cmp.lua - Completion engine
- conform-nvim.lua - Code formatting
- linting.lua - Linting
- telescope.lua - Fuzzy finder
- treesitter.lua - Syntax highlighting
- lazygit.lua - Git UI integration
- nvim-tree.lua - File explorer
- trouble.lua - Diagnostics viewer
- gitsigns.lua - Git change indicators
- vim-tmux-navigator.lua - Seamless tmux/vim navigation
- colorscheme.lua - Theme configuration
- lualine.lua - Status line
- bufferline.lua - Buffer/tab line

**LSP directory**: Contains mason.lua and lspconfig.lua for language server management.

### AeroSpace Window Manager (aerospace/aerospace.toml)

i3-like tiling window manager configuration for macOS.

**Layout settings**:
- Default layout: tiles
- Orientation: auto (horizontal for wide monitors, vertical for tall)
- Gaps: 5px inner, 0px outer
- Accordion padding: 10px
- Container normalization enabled

**Keybindings** (Alt as modifier):
- Navigation: h/j/k/l (vim-style)
- Move windows: Shift + h/j/k/l
- Layouts: `/` (tiles horizontal/vertical), `,` (accordion)
- Resize: Shift + `-` (shrink), Shift + `=` (grow)
- Workspaces: 1-9, w, t, s, m, o, g, p
- Move to workspace: Shift + [workspace key]
- Service mode: Shift + `;`

**App launchers**:
- Enter → Alacritty
- b → Vivaldi
- c → Spotify
- z → Obsidian

**Workspace auto-assignment** (aerospace/aerospace.toml:209-232):
- Alacritty → workspace t
- Vivaldi → workspace w (note: app-id has trailing quote bug at line 215)
- Spotify → workspace s
- Telegram → workspace m
- Obsidian → workspace o
- Chrome → workspace g

**Monitor assignment**:
- Workspaces 1-5: main monitor only
- Workspaces 6-9, t, w, s, o, p: secondary monitor (fallback to main)

**Service mode bindings** (aerospace/aerospace.toml:195-207):
- Esc → reload config
- r → flatten workspace tree (reset layout)
- f → toggle floating/tiling
- Backspace → close all windows except current
- Shift + h/j/k/l → join window with direction

### Alacritty Terminal (alacritty/alacritty.toml)

- Theme: Alabaster Dark (imported from `~/.config/alacritty/themes/themes/`)
- Font: JetBrainsMono Nerd Font (normal, bold, italic), size 20
- Window: Buttonless decorations, 2px padding, maximized startup, full opacity
- Cursor: Block shape, non-blinking (in both normal and vi mode)
- Mouse: Hidden when typing
- Option key: Both left and right act as Alt
- Selection: Auto-copy to clipboard
- TERM: xterm-256color

### Tmux Configuration (.tmux.conf)

**Terminal settings**:
- TERM: tmux-256color with RGB support
- Prefix: Ctrl+a (with Ctrl+b unbound)

**Options**:
- Base index: 1 (windows and panes)
- Mouse support enabled
- Vi mode keybindings
- Auto-renumber windows
- Zero escape time
- 50k line history
- Focus events enabled

**Keybindings**:
- Prefix: Ctrl+a
- Split horizontal: `|` (maintains current path)
- Split vertical: `-` (maintains current path)
- Resize panes: h/j/k/l (with repeat)
- Maximize pane: m
- Clear screen: Ctrl+l (since Ctrl+l is used by vim-tmux-navigator)
- Reload config: r
- Vi copy mode: v (begin), y (copy)

**Plugins** (via TPM):
- vim-tmux-navigator - Seamless vim/tmux pane navigation
- tmux-resurrect - Save/restore sessions (captures pane contents)
- tmux-continuum - Automatic session saving (auto-restore disabled)
- tmux-sessionist - Session management utilities
- tmux-gruvbox - Gruvbox dark theme

## Utility Scripts (bash_scripts/)

### ppkg
Creates Python package structure:
```zsh
mkdir $1
cd $1
touch __init__.py
$SHELL  # spawns new shell in package directory
```

### start_py
Scaffolds Python project with uv:
1. Prompts for project name
2. Runs `uv init --app $NAME`
3. Removes default `main.py`
4. Downloads .gitignore from toptal.com/developers/gitignore
5. Creates pyrightconfig.json with:
   - venvPath: "."
   - venv: ".venv"
   - typeCheckingMode: "recommended"
   - Standard excludes: node_modules, .git, __pycache__, venv, dist, build
6. Spawns new shell in project directory

## Important Notes for Modifications

### When editing .zshrc:
- Custom directory is `$HOME/.config/oh-my-zsh`, not default `~/.oh-my-zsh`
- ZSH_THEME is empty; Powerlevel10k is sourced from Homebrew
- Syntax highlighting uses fast-syntax-highlighting plugin, not zsh-syntax-highlighting
- FZF previews depend on bat and eza being installed
- Autosuggestions loaded after Oh My Zsh to avoid conflicts

### When editing aerospace/aerospace.toml:
- Fix Vivaldi app-id at line 215 (has trailing quote: `com.vivaldi.Vivaldi"` should be `com.vivaldi.Vivaldi`)
- Workspace-to-monitor assignments affect multi-monitor setups
- Service mode must be exited to return to main mode

### When editing alacritty/alacritty.toml:
- Theme imports are relative to home directory
- Font size is 20 (larger for readability)
- Opacity is 1 (fully opaque) for better visibility
- Window starts maximized by default

### When editing .tmux.conf:
- Prefix is Ctrl+a (not default Ctrl+b)
- All comments are in English
- Split commands maintain current path with -c flag
- tmux-continuum auto-restore is disabled to prevent unwanted session restoration

### When editing Neovim configs:
- All modules must use `scv3lqq` namespace
- Plugin files in `nvim/lua/scv3lqq/plugins/` are auto-loaded by Lazy.nvim
- LSP configs are separate in `nvim/lua/scv3lqq/plugins/lsp/`
