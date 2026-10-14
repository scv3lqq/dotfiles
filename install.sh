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
    lazygit lazydocker topgrade terminal-notifier \
    ripgrep tree-sitter-cli go node yarn gh

  # A copy installed outside brew (DMG app, hand-installed font) makes brew
  # exit 1: keep it and go on
  for cask in ghostty karabiner-elements font-jetbrains-mono-nerd-font nikitabobko/tap/aerospace; do
    brew install --cask "$cask" || echo "Skipping $cask: brew could not install it (already installed by hand?)"
  done

elif [[ "$OS" == "Linux" ]]; then
  echo "Installing packages (Linux)..."
  case "$(uname -m)" in
    x86_64) nvim_arch=x86_64 ts_arch=x64 ;;
    aarch64 | arm64) nvim_arch=arm64 ts_arch=arm64 ;;
    *) echo "Unsupported architecture: $(uname -m)"; exit 1 ;;
  esac

  # Neovim, tree-sitter CLI (nvim-treesitter), make/gcc (plugin builds),
  # go/npm/unzip/python venv (Mason servers) must exist before the first
  # nvim start: lazy.nvim does not retry a failed build
  if command -v apt-get &>/dev/null; then
    sudo apt-get update -q
    sudo apt-get install -y stow zsh curl git jq tmux fzf ripgrep make gcc unzip \
      python3-venv nodejs npm golang-go zsh-autosuggestions
  elif command -v dnf &>/dev/null; then
    sudo dnf install -y stow zsh curl git jq tmux fzf ripgrep make gcc unzip \
      python3 nodejs npm golang zsh-autosuggestions
  else
    echo "No apt-get or dnf: install the packages listed in README.md by hand"
    exit 1
  fi

  # The config needs Neovim 0.11.3+; distro packages are older
  nvim_version="$(nvim --version 2>/dev/null | sed -n '1s/^NVIM v\([0-9.]*\).*/\1/p')"
  if [[ -z "$nvim_version" || "$(printf '%s\n' 0.11.3 "$nvim_version" | sort -V | head -1)" != 0.11.3 ]]; then
    # --no-same-owner: as root tar would keep the archive's uid on /usr/local/{bin,lib,share}
    curl -fsSL "https://github.com/neovim/neovim/releases/latest/download/nvim-linux-$nvim_arch.tar.gz" |
      sudo tar -C /usr/local -xz --strip-components=1 --no-same-owner
  fi

  # Checks the version output, not the exit code: a failed or interrupted
  # download leaves an empty file that bash runs as an empty script (exit 0)
  if ! tree-sitter --version 2>/dev/null | grep -q '^tree-sitter '; then
    curl -fsSL "https://github.com/tree-sitter/tree-sitter/releases/latest/download/tree-sitter-linux-$ts_arch.gz" |
      gunzip | sudo tee /usr/local/bin/tree-sitter >/dev/null
    sudo chmod 755 /usr/local/bin/tree-sitter
    if ! /usr/local/bin/tree-sitter --version 2>/dev/null | grep -q '^tree-sitter '; then
      sudo rm -f /usr/local/bin/tree-sitter
      echo "Skipping tree-sitter CLI: download failed or the prebuilt binary needs glibc 2.39+, Neovim gets no tree-sitter highlighting"
    fi
  fi

  if ! command -v starship &>/dev/null; then
    curl -sS https://starship.rs/install.sh | sh -s -- -y
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
  if ! jq -e '[.hooks.Stop[]?.hooks[]?.command // empty] | any(test("notify\\.sh"))' "$settings" >/dev/null; then
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
# Commit signing for this repo
# =============================================================================
# Repo-local only: the global ~/.gitconfig may carry another identity. The
# email comes from the last commit, so no address lives in the repo.
signing_key="$HOME/.ssh/id_ed25519.pub"
git_version="$(git --version | awk '{print $3}')"
IFS=. read -r git_major git_minor _ <<<"$git_version"
if [[ ! -f "$signing_key" ]]; then
  echo "Skipping commit signing: $signing_key not found"
elif (( git_major < 2 || (git_major == 2 && git_minor < 34) )); then
  echo "Skipping commit signing: git $git_version has no SSH signing (needs 2.34+)"
else
  echo "Setting up commit signing..."
  email="$(git -C "$DOTFILES" log -1 --format=%ae)"
  git -C "$DOTFILES" config user.email "$email"
  git -C "$DOTFILES" config gpg.format ssh
  git -C "$DOTFILES" config user.signingkey "$signing_key"
  git -C "$DOTFILES" config gpg.ssh.allowedSignersFile "$HOME/.ssh/allowed_signers"
  git -C "$DOTFILES" config commit.gpgsign true
  git -C "$DOTFILES" config tag.gpgsign true

  signer="$email $(cut -d' ' -f1,2 "$signing_key")"
  touch ~/.ssh/allowed_signers
  grep -qxF "$signer" ~/.ssh/allowed_signers || echo "$signer" >> ~/.ssh/allowed_signers

  # Listing signing keys needs the admin:ssh_signing_key scope
  if command -v gh &>/dev/null && signing_keys="$(gh api user/ssh_signing_keys --jq '.[].key' 2>/dev/null)"; then
    if ! grep -qF "$(cut -d' ' -f2 "$signing_key")" <<<"$signing_keys"; then
      gh ssh-key add "$signing_key" --type signing --title "$(hostname -s) signing" ||
        echo "Could not add the signing key to GitHub; commits will show Unverified"
    fi
  else
    echo "To get Verified commits on GitHub run: gh auth refresh -h github.com -s admin:ssh_signing_key, then ./install.sh again"
  fi
fi

# =============================================================================
# Default shell
# =============================================================================
if [[ "${SHELL##*/}" != zsh ]]; then
  echo "Setting zsh as default shell..."
  if [[ "$OS" == "Darwin" ]]; then
    chsh -s "$(command -v zsh)"
  else
    # chsh asks for a password cloud users do not have; on Fedora
    # `command -v zsh` is /usr/sbin/zsh, which /etc/shells does not list
    zsh_path="$(grep -m1 '/zsh$' /etc/shells || command -v zsh)"
    sudo usermod -s "$zsh_path" "$(id -un)"
  fi
fi

echo "Done."
