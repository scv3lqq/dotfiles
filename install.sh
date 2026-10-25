#!/usr/bin/env bash
set -e

DOTFILES="$HOME/dotfiles"

OS="$(uname -s)"

# README.md lists the same packages: change both together
brew_formulae=(
  stow neovim tmux starship fzf fd bat eza yazi jq
  zsh-fast-syntax-highlighting zsh-autosuggestions zsh-completions
  lazygit lazydocker topgrade terminal-notifier
  ripgrep tree-sitter-cli go node yarn gh
)
brew_casks=(ghostty karabiner-elements font-jetbrains-mono-nerd-font nikitabobko/tap/aerospace claudebar)
apt_packages=(
  stow zsh curl git jq tmux fzf ripgrep make gcc unzip
  python3-venv nodejs npm golang-go zsh-autosuggestions
)
dnf_packages=(
  stow zsh curl git jq tmux fzf ripgrep make gcc unzip
  python3 nodejs npm golang zsh-autosuggestions
)

# =============================================================================
# Helpers
# =============================================================================
usage() {
  cat <<'EOF'
Usage: install.sh [--update]

  (no flag)  install packages, link configs, set up the shell; safe to re-run
  --update   git pull --ff-only, then the same as above, plus upgrade the
             tools this repo installs and sync tmux and Neovim plugins
EOF
}

version_lt() {
  [[ "$1" != "$2" && "$(printf '%s\n' "$1" "$2" | sort -V | head -1)" == "$1" ]]
}

# The redirect of /releases/latest names the tag: no API token, no rate limit
latest_release() {
  local url
  url="$(curl -fsSLI --connect-timeout 10 --max-time 30 -o /dev/null -w '%{url_effective}' "https://github.com/$1/releases/latest" 2>/dev/null)" || return 0
  [[ "$url" == */tag/* ]] || return 0
  url="${url##*/tag/}"
  echo "${url#v}"
}

# Downloads and lists the archive before touching the install, so a failed or
# corrupt download leaves the old Neovim working. The old runtime goes before
# extracting: files a release dropped must not linger in the runtime path.
install_nvim() {
  local tarball
  tarball="$(mktemp)"
  curl -fsSL -o "$tarball" "https://github.com/neovim/neovim/releases/latest/download/nvim-linux-$1.tar.gz" || { rm -f "$tarball"; return 1; }
  tar -tzf "$tarball" >/dev/null || { rm -f "$tarball"; return 1; }
  if [[ -e /usr/local/bin/nvim ]]; then
    sudo rm -rf /usr/local/share/nvim/runtime /usr/local/lib/nvim
  fi
  # --no-same-owner: as root tar would keep the archive's uid on /usr/local/{bin,lib,share}
  sudo tar -C /usr/local -xzf "$tarball" --strip-components=1 --no-same-owner || { rm -f "$tarball"; return 1; }
  rm -f "$tarball"
}

# Checks the version output, not the exit code: a failed or interrupted
# download leaves an empty file that bash runs as an empty script (exit 0).
# The temporary name keeps a working binary in place when the new one fails.
install_tree_sitter() {
  local new=/usr/local/bin/tree-sitter.new
  curl -fsSL "https://github.com/tree-sitter/tree-sitter/releases/latest/download/tree-sitter-linux-$1.gz" |
    gunzip | sudo tee "$new" >/dev/null
  sudo chmod 755 "$new"
  if ! "$new" --version 2>/dev/null | grep -q '^tree-sitter '; then
    sudo rm -f "$new"
    return 1
  fi
  sudo mv -f "$new" /usr/local/bin/tree-sitter
}

# TPM asks a tmux server for its plugin path. With no server running it starts
# one from ~/.tmux.conf, which loads every plugin (tmux-continuum then
# restores the saved sessions); inside tmux it uses the live server. A private
# server without a config avoids both.
sync_tmux_plugins() {
  local dir rc=1
  dir="$(mktemp -d)"
  if tmux -S "$dir/tmux" -f /dev/null new-session -d &&
    tmux -S "$dir/tmux" set-environment -g TMUX_PLUGIN_MANAGER_PATH "$HOME/.tmux/plugins/"; then
    rc=0
    TMUX="$dir/tmux,0,0" ~/.tmux/plugins/tpm/bin/install_plugins || rc=1
    TMUX="$dir/tmux,0,0" ~/.tmux/plugins/tpm/bin/update_plugins all || rc=1
  fi
  tmux -S "$dir/tmux" kill-server 2>/dev/null
  rm -rf "$dir"
  return "$rc"
}

# lazy.nvim bootstraps itself from its stable branch, so the first start
# rewrites the "lazy.nvim" line of the lock. That line is reset; any other
# change is the user's and is kept. An external diff tool prints no +/- lines
# and would hide a user edit.
lock_has_user_changes() {
  git -C "$DOTFILES" diff --no-ext-diff --no-textconv --no-color -U0 -- nvim/lazy-lock.json |
    grep -E '^[-+]' | grep -Ev '^(---|\+\+\+) ' | grep -vq '"lazy.nvim":'
}

sync_nvim_plugins() {
  local lock=nvim/lazy-lock.json rc=0 lua

  if lock_has_user_changes; then
    echo "Skipping Neovim plugins: nvim/lazy-lock.json has local changes (commit or discard them, then re-run)"
    return 0
  fi

  echo "Restoring Neovim plugins to nvim/lazy-lock.json..."
  git -C "$DOTFILES" checkout -- "$lock"
  # Headless nvim ends its last message without a newline
  nvim --headless "+Lazy! restore" +qa || rc=1
  echo
  if ! git -C "$DOTFILES" diff --quiet -- "$lock"; then
    git -C "$DOTFILES" checkout -- "$lock"
    nvim --headless "+Lazy! restore" +qa || rc=1
    echo
  fi
  # A plugin the restore could not install drops out of the lock; a dirty lock
  # would block the next pull and the next sync
  if ! git -C "$DOTFILES" diff --quiet -- "$lock"; then
    echo "Warning: nvim/lazy-lock.json still differs from the repo after the restore, resetting it"
    git -C "$DOTFILES" checkout -- "$lock"
    rc=1
  fi

  # Headless nvim exits 0 after a Lua error, hence pcall and cquit. A parser
  # whose install was cut short (nvim quit while the config's async install
  # ran) has no revision file and makes update() fail: reinstall those first.
  lua="$(mktemp)"
  cat >"$lua" <<'EOF'
local ok, res = pcall(function()
  local ts, config = require("nvim-treesitter"), require("nvim-treesitter.config")
  local info_dir = config.get_install_dir("parser-info")
  local broken = vim.tbl_filter(function(lang)
    return not vim.uv.fs_stat(info_dir .. "/" .. lang .. ".revision")
  end, config.get_installed("parsers"))
  if #broken > 0 and not ts.install(broken, { force = true }):wait(1800000) then
    return false
  end
  return ts.update(nil, { summary = true }):wait(1800000)
end)
if not ok then
  io.stderr:write(tostring(res), "\n")
end
if not (ok and res) then
  vim.cmd("cquit 1")
end
EOF
  echo "Updating tree-sitter parsers..."
  nvim --headless -c "luafile $lua" +qa || rc=1
  echo

  cat >"$lua" <<'EOF'
local ok, err = pcall(function()
  local registry = require("mason-registry")
  registry.refresh()
  local outdated = {}
  for _, pkg in ipairs(registry.get_installed_packages()) do
    if pkg:get_installed_version() ~= pkg:get_latest_version() then
      outdated[#outdated + 1] = pkg.name
    end
  end
  if #outdated > 0 then
    vim.cmd("MasonInstall " .. table.concat(outdated, " "))
  end
end)
if not ok then
  io.stderr:write(tostring(err), "\n")
  vim.cmd("cquit 1")
end
EOF
  echo "Updating Mason packages..."
  nvim --headless -c MasonUpdate -c "luafile $lua" +qa || rc=1
  echo
  rm -f "$lua"
  return "$rc"
}

# =============================================================================
# Arguments
# =============================================================================
case "$#:${1-}" in
  0:) mode=install ;;
  1:--update) mode=update ;;
  1:-h | 1:--help)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

# git pull may rewrite this file while bash is still reading it: bash parses
# the whole if block before running it, so the exec comes from the old text
if [[ "$mode" == update && -z "${DOTFILES_PULLED-}" ]]; then
  old_head="$(git -C "$DOTFILES" rev-parse HEAD)"
  # The lazy.nvim line would block a pull that changes the lock
  lock_has_user_changes || git -C "$DOTFILES" checkout -- nvim/lazy-lock.json
  echo "Pulling $DOTFILES..."
  if ! git -C "$DOTFILES" pull --ff-only; then
    echo "git pull failed: fix it in $DOTFILES, then re-run install.sh --update"
    exit 1
  fi
  DOTFILES_PULLED="$old_head" exec bash "$DOTFILES/install.sh" --update
fi

# =============================================================================
# Package installation
# =============================================================================
if [[ "$OS" == "Darwin" ]]; then
  if ! command -v brew &>/dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
  fi

  cask_env=()
  if [[ "$mode" == update ]]; then
    echo "Updating Homebrew..."
    brew update || echo "Warning: brew update failed, upgrading from the current package index"
    # brew install upgrades a named cask even when it updates itself
    # (Ghostty): the brew outdated filter below decides instead. Formulae keep
    # the default, with it an outdated one prints an Error: line
    cask_env=(HOMEBREW_NO_INSTALL_UPGRADE=1)
  fi

  echo "Installing packages (macOS)..."
  brew install "${brew_formulae[@]}"

  # A copy installed outside brew (DMG app, hand-installed font) makes brew
  # exit 1: keep it and go on
  for cask in "${brew_casks[@]}"; do
    env "${cask_env[@]}" brew install --cask "$cask" || echo "Skipping $cask: brew could not install it (already installed by hand?)"
  done

  if [[ "$mode" == update ]]; then
    echo "Upgrading packages (macOS)..."
    brew upgrade "${brew_formulae[@]}" || echo "Warning: brew could not upgrade every formula, see the errors above"
    # A named cask is upgraded even when it updates itself (Ghostty); brew
    # outdated leaves those out, and casks installed by hand too
    outdated_casks="$(brew outdated --cask --quiet)" || outdated_casks=""
    for cask in "${brew_casks[@]}"; do
      if grep -qxF "${cask##*/}" <<<"$outdated_casks"; then
        brew upgrade --cask "$cask" || echo "Skipping $cask: brew could not upgrade it"
      fi
    done
  fi

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
    # On an installed package apt-get install takes the newest candidate, so
    # --update needs no extra apt command
    sudo apt-get install -y "${apt_packages[@]}"
  elif command -v dnf &>/dev/null; then
    sudo dnf install -y "${dnf_packages[@]}"
    if [[ "$mode" == update ]]; then
      sudo dnf upgrade -y "${dnf_packages[@]}"
    fi
  else
    echo "No apt-get or dnf: install the packages listed in README.md by hand"
    exit 1
  fi

  # The config needs Neovim 0.11.3+; distro packages are older
  nvim_version="$(nvim --version 2>/dev/null | sed -n '1s/^NVIM v\([0-9.]*\).*/\1/p')"
  if [[ -z "$nvim_version" ]] || version_lt "$nvim_version" 0.11.3; then
    install_nvim "$nvim_arch"
  # Upgrades only the copies install.sh put in /usr/local/bin. -ef, not ==:
  # Fedora links /usr/local/sbin to bin, and an sbin-first PATH finds them there
  elif [[ "$mode" == update && "$(command -v nvim)" -ef /usr/local/bin/nvim ]]; then
    nvim_latest="$(latest_release neovim/neovim)"
    if [[ -z "$nvim_latest" ]]; then
      echo "Could not check the latest Neovim release, keeping $nvim_version"
    elif version_lt "$nvim_version" "$nvim_latest"; then
      echo "Updating Neovim $nvim_version to $nvim_latest..."
      install_nvim "$nvim_arch" ||
        echo "Could not update Neovim: download or unpack failed, see the errors above"
    fi
  fi

  if ! tree-sitter --version 2>/dev/null | grep -q '^tree-sitter '; then
    # A broken binary left on PATH makes nvim-treesitter fail instead of skip
    install_tree_sitter "$ts_arch" || {
      sudo rm -f /usr/local/bin/tree-sitter
      echo "Skipping tree-sitter CLI: download failed or the prebuilt binary needs glibc 2.39+, Neovim gets no tree-sitter highlighting"
    }
  elif [[ "$mode" == update && "$(command -v tree-sitter)" -ef /usr/local/bin/tree-sitter ]]; then
    ts_version="$(tree-sitter --version | awk '{print $2}')"
    ts_latest="$(latest_release tree-sitter/tree-sitter)"
    if [[ -z "$ts_latest" ]]; then
      echo "Could not check the latest tree-sitter release, keeping $ts_version"
    elif version_lt "$ts_version" "$ts_latest"; then
      echo "Updating tree-sitter CLI $ts_version to $ts_latest..."
      install_tree_sitter "$ts_arch" ||
        echo "Could not update tree-sitter CLI: download failed or the new binary does not run, keeping $ts_version"
    fi
  fi

  if ! command -v starship &>/dev/null; then
    curl -sS https://starship.rs/install.sh | sh -s -- -y
  elif [[ "$mode" == update && "$(command -v starship)" -ef /usr/local/bin/starship ]]; then
    starship_version="$(starship --version | awk 'NR == 1 {print $2}')"
    starship_latest="$(latest_release starship/starship)"
    if [[ -z "$starship_latest" ]]; then
      echo "Could not check the latest Starship release, keeping $starship_version"
    elif version_lt "$starship_version" "$starship_latest"; then
      echo "Updating Starship $starship_version to $starship_latest..."
      # Piped, a failed download would hand sh an empty script, which exits 0
      starship_installer="$(mktemp)"
      if ! curl -fsSL -o "$starship_installer" https://starship.rs/install.sh || ! sh "$starship_installer" -y; then
        echo "Could not update Starship, keeping $starship_version"
      fi
      rm -f "$starship_installer"
    fi
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

ln -sf "$DOTFILES/starship/starship.toml" ~/.config/starship.toml
ln -sf "$DOTFILES/tmux/tmux.conf" ~/.tmux.conf

# TPM (tmux plugin manager)
if [[ ! -d ~/.tmux/plugins/tpm ]]; then
  echo "Installing TPM..."
  git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
fi

# Tell zsh where to find its config
echo 'export ZDOTDIR="$HOME/.config/zsh"' > ~/.zshenv

# =============================================================================
# Claude Code: the /feature skill and the agents it runs
# =============================================================================
# File links: ~/.claude/skills and ~/.claude/agents also hold skills and
# agents from outside this repo. A regular file in the way is replaced.
echo "Linking Claude Code skills and agents..."
mkdir -p ~/.claude/skills/feature ~/.claude/agents
ln -sf "$DOTFILES/claude/skills/feature/SKILL.md" ~/.claude/skills/feature/SKILL.md
ln -sf "$DOTFILES"/claude/agents/*.md ~/.claude/agents/

# =============================================================================
# Claude Code status line
# =============================================================================
echo "Linking Claude Code status line..."
ln -sf "$DOTFILES/claude/statusline.sh" ~/.claude/statusline.sh
settings="$HOME/.claude/settings.json"
[[ -f "$settings" ]] || echo '{}' > "$settings"
if ! jq -e '.statusLine.command == "~/.claude/statusline.sh"' "$settings" >/dev/null; then
  tmp="$(mktemp)"
  jq '.statusLine = {"type": "command", "command": "~/.claude/statusline.sh"}' \
    "$settings" > "$tmp" && mv "$tmp" "$settings"
fi

# =============================================================================
# Claude Code notifications (macOS)
# =============================================================================
# The Stop hook is the only alert source: the built-in channel and gopass
# alerts are turned off, Ghostty drops terminal OSC notifications.
if [[ "$OS" == "Darwin" ]]; then
  echo "Setting up Claude Code notifications..."
  mkdir -p ~/.claude/hooks
  ln -sf "$DOTFILES/claude/hooks/notify.sh" ~/.claude/hooks/notify.sh
  ln -sf "$DOTFILES/claude/hooks/pane-state.sh" ~/.claude/hooks/pane-state.sh

  settings="$HOME/.claude/settings.json"
  [[ -f "$settings" ]] || echo '{}' > "$settings"
  if ! jq -e '[.hooks.Stop[]?.hooks[]?.command // empty] | any(test("notify\\.sh"))' "$settings" >/dev/null; then
    tmp="$(mktemp)"
    jq '.hooks.Stop += [{"hooks": [{"type": "command", "command": "~/.claude/hooks/notify.sh", "timeout": 10}]}]' \
      "$settings" > "$tmp" && mv "$tmp" "$settings"
  fi

  # Turn state for the `prefix + s` picker: one entry per event, added where missing
  pane_state_filter='reduce ("UserPromptSubmit", "PreToolUse", "PermissionRequest", "PostToolUse",
    "PostToolUseFailure", "Notification", "Stop", "StopFailure",
    "SessionStart", "SessionEnd") as $e (.;
  if any(.hooks[$e][]?.hooks[]?.command; . == "~/.claude/hooks/pane-state.sh") then .
  else .hooks[$e] += [(if $e == "Notification"
      then {matcher: "permission_prompt|elicitation_dialog|idle_prompt"} else {} end)
    + {hooks: [{type: "command", command: "~/.claude/hooks/pane-state.sh", timeout: 5}]}]
  end)'
  if [[ "$(jq "$pane_state_filter" "$settings")" != "$(jq . "$settings")" ]]; then
    tmp="$(mktemp)"
    jq "$pane_state_filter" "$settings" > "$tmp" && mv "$tmp" "$settings"
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

# =============================================================================
# Plugins and summary (--update)
# =============================================================================
if [[ "$mode" == update ]]; then
  echo "Updating tmux plugins..."
  sync_tmux_plugins || echo "Warning: tmux plugins were not fully updated, see the output above"

  if command -v nvim &>/dev/null; then
    sync_nvim_plugins || echo "Warning: Neovim plugins were not fully updated, see the output above"
  fi

  if [[ "$(git -C "$DOTFILES" rev-parse HEAD)" == "$DOTFILES_PULLED" ]]; then
    echo "Dotfiles already up to date ($(git -C "$DOTFILES" rev-parse --short HEAD))"
  else
    echo "Dotfiles: $(git -C "$DOTFILES" rev-parse --short "$DOTFILES_PULLED")..$(git -C "$DOTFILES" rev-parse --short HEAD) ($(git -C "$DOTFILES" rev-list --count "$DOTFILES_PULLED..HEAD") commits)"
  fi
  echo "Open a new shell (or run tmux-reload) to load zsh changes."
fi

echo "Done."
