#!/bin/zsh
set -e

DOTFILES="$HOME/dotfiles"

# Homebrew
if ! command -v brew &>/dev/null; then
  echo "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$(/opt/homebrew/bin/brew shellenv)"
fi

# Packages
echo "Installing packages..."
brew install stow neovim tmux starship fzf fd bat eza \
  zsh-fast-syntax-highlighting zsh-autosuggestions zsh-completions \
  lazygit lazydocker

brew install --cask ghostty aerospace karabiner-elements \
  font-jetbrains-mono-nerd-font

# Stow
echo "Symlinking configs..."
cd "$DOTFILES"

mkdir -p ~/.config/nvim
mkdir -p ~/.config/zsh

# Remove Karabiner-managed dir so stow can create a symlink
rm -rf ~/.config/karabiner

stow --restow --target ~/.config ghostty aerospace karabiner
stow --restow --target ~/.config/nvim nvim
stow --restow --target ~/.config/zsh zsh

ln -sf "$DOTFILES/starship.toml" ~/.config/starship.toml
ln -sf "$DOTFILES/.tmux.conf" ~/.tmux.conf

# Default shell
if [[ "$SHELL" != "/bin/zsh" ]]; then
  echo "Setting zsh as default shell..."
  chsh -s /bin/zsh
fi

echo "Done. Open Ghostty and run: nvim"
