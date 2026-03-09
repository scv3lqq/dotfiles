#!/bin/zsh
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
  brew install stow neovim tmux starship fzf fd bat eza \
    zsh-fast-syntax-highlighting zsh-autosuggestions zsh-completions \
    lazygit lazydocker

  brew install --cask ghostty aerospace karabiner-elements \
    font-jetbrains-mono-nerd-font

elif [[ "$OS" == "Linux" ]]; then
  echo "Installing packages (Linux)..."
  if command -v apt-get &>/dev/null; then
    sudo apt-get update -q
    sudo apt-get install -y stow zsh curl git
  elif command -v dnf &>/dev/null; then
    sudo dnf install -y stow zsh curl git
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

if [[ "$OS" == "Darwin" ]]; then
  rm -rf ~/.config/karabiner
  stow --restow --target ~/.config ghostty aerospace karabiner
fi

stow --restow --target ~/.config/nvim nvim
stow --restow --target ~/.config/zsh zsh

ln -sf "$DOTFILES/starship.toml" ~/.config/starship.toml
ln -sf "$DOTFILES/.tmux.conf" ~/.tmux.conf

# =============================================================================
# Default shell
# =============================================================================
if [[ "$SHELL" != "$(command -v zsh)" ]]; then
  echo "Setting zsh as default shell..."
  chsh -s "$(command -v zsh)"
fi

echo "Done."
