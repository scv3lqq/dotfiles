#!/usr/bin/env bash
set -e

DOTFILES="$HOME/dotfiles"

OS="$(uname -s)"

# =============================================================================
# Package installation
# =============================================================================
if [[ "$OS" == "Darwin" ]]; then
  if ! command -v brew &>/dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
  fi

  echo "Installing packages (macOS)..."
  brew install stow neovim tmux starship fzf fd bat eza yazi jq \
    zsh-fast-syntax-highlighting zsh-autosuggestions zsh-completions \
    lazygit lazydocker topgrade terminal-notifier

  brew install --cask ghostty karabiner-elements font-jetbrains-mono-nerd-font
  brew install --cask nikitabobko/tap/aerospace

elif [[ "$OS" == "Linux" ]]; then
  echo "Installing packages (Linux)..."
  if command -v apt-get &>/dev/null; then
    sudo apt-get update -q
    sudo apt-get install -y stow zsh curl git jq
  elif command -v dnf &>/dev/null; then
    sudo dnf install -y stow zsh curl git jq
  fi

  if ! command -v nvim &>/dev/null; then
    curl -LO https://github.com/neovim/neovim/releases/latest/download/nvim-linux-x86_64.tar.gz
    sudo tar -C /usr/local -xzf nvim-linux-x86_64.tar.gz --strip-components=1
    rm nvim-linux-x86_64.tar.gz
  fi

  if ! command -v starship &>/dev/null; then
    curl -sS https://starship.rs/install.sh | sh -s -- -y
  fi

  if ! command -v tmux &>/dev/null; then
    sudo apt-get install -y tmux 2>/dev/null || sudo dnf install -y tmux
  fi
fi

# =============================================================================
# Stow
# =============================================================================
echo "Symlinking configs..."
cd "$DOTFILES"

mkdir -p ~/.config/nvim
mkdir -p ~/.config/zsh
mkdir -p ~/.config/yazi

if [[ "$OS" == "Darwin" ]]; then
  rm -rf ~/.config/karabiner
  stow --restow --target ~/.config ghostty aerospace karabiner topgrade
fi

stow --restow --target ~/.config/nvim nvim
stow --restow --target ~/.config/zsh zsh
stow --restow --target ~/.config/yazi yazi

ln -sf "$DOTFILES/starship.toml" ~/.config/starship.toml
ln -sf "$DOTFILES/.tmux.conf" ~/.tmux.conf

# TPM (tmux plugin manager)
if [[ ! -d ~/.tmux/plugins/tpm ]]; then
  echo "Installing TPM..."
  git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
fi

# Tell zsh where to find its config
echo 'export ZDOTDIR="$HOME/.config/zsh"' > ~/.zshenv

# =============================================================================
# Claude Code notifications (macOS)
# =============================================================================
# The Stop hook is the only alert source: the built-in channel and gopass
# alerts are turned off, Ghostty drops terminal OSC notifications.
if [[ "$OS" == "Darwin" ]]; then
  echo "Setting up Claude Code notifications..."
  mkdir -p ~/.claude/hooks
  ln -sf "$DOTFILES/claude/hooks/notify.sh" ~/.claude/hooks/notify.sh

  settings="$HOME/.claude/settings.json"
  [[ -f "$settings" ]] || echo '{}' > "$settings"
  if ! jq -e '[.hooks.Stop[]?.hooks[]?.command] | any(test("notify\\.sh"))' "$settings" >/dev/null; then
    tmp="$(mktemp)"
    jq '.hooks.Stop += [{"hooks": [{"type": "command", "command": "~/.claude/hooks/notify.sh", "timeout": 10}]}]' \
      "$settings" > "$tmp" && mv "$tmp" "$settings"
  fi

  # A global config key: the same key in settings.json does not override it
  [[ -f ~/.claude.json ]] || echo '{}' > ~/.claude.json
  if ! jq -e '.preferredNotifChannel == "notifications_disabled"' ~/.claude.json >/dev/null; then
    tmp="$(mktemp)"
    jq '.preferredNotifChannel = "notifications_disabled"' ~/.claude.json > "$tmp" && mv "$tmp" ~/.claude.json
  fi

  # Without an existing config gopass would start its interactive setup
  if command -v gopass &>/dev/null && [[ -f ~/.config/gopass/config ]]; then
    gopass config core.notifications false >/dev/null
  fi
fi

# =============================================================================
# Default shell
# =============================================================================
if [[ "$SHELL" != "$(command -v zsh)" ]]; then
  echo "Setting zsh as default shell..."
  chsh -s "$(command -v zsh)"
fi

echo "Done."
