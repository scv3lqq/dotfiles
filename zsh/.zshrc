# =============================================================================
# Options
# =============================================================================
setopt AUTO_CD
setopt HIST_IGNORE_DUPS
setopt HIST_IGNORE_SPACE
setopt SHARE_HISTORY
setopt EXTENDED_HISTORY
setopt GLOB_DOTS

# History
HISTFILE="$HOME/.zsh_history"
HISTSIZE=50000
SAVEHIST=50000

# =============================================================================
# Editor
# =============================================================================
export EDITOR=nvim
export VISUAL=nvim

# =============================================================================
# Path
# =============================================================================
[[ -x /opt/homebrew/bin/brew ]] && eval "$(/opt/homebrew/bin/brew shellenv)"
export PATH="$HOME/.local/bin:$PATH"
command -v go &>/dev/null && export PATH="$PATH:$(go env GOPATH)/bin"

# =============================================================================
# Aliases
# =============================================================================
alias ls='ls --color=auto'
alias ll='ls -lah'
alias la='ls -A'
alias ..='cd ..'
alias ...='cd ../..'

[[ -f "$ZDOTDIR/aliases.zsh" ]] && source "$ZDOTDIR/aliases.zsh"

# =============================================================================
# Key bindings
# =============================================================================
bindkey -e  # emacs mode (compatible with most tools)
bindkey '^[[A' history-search-backward
bindkey '^[[B' history-search-forward

# =============================================================================
# Completion
# =============================================================================
[[ -d /opt/homebrew/share/zsh-completions ]] && FPATH="/opt/homebrew/share/zsh-completions:$FPATH"
autoload -Uz compinit
[[ -d "$HOME/.cache/zsh" ]] || mkdir -p "$HOME/.cache/zsh"
compinit -u -d "$HOME/.cache/zsh/zcompdump"

zstyle ':completion:*' menu select
zstyle ':completion:*' matcher-list 'm:{a-z}={A-Z}'

# =============================================================================
# Plugins
# =============================================================================
# zsh-fast-syntax-highlighting
_fsh_paths=(
  /opt/homebrew/opt/zsh-fast-syntax-highlighting/share/zsh-fast-syntax-highlighting/fast-syntax-highlighting.plugin.zsh
  /usr/share/zsh-fast-syntax-highlighting/fast-syntax-highlighting.plugin.zsh
)
for _p in $_fsh_paths; do [[ -f "$_p" ]] && source "$_p" && break; done
unset _fsh_paths _p

# zsh-autosuggestions
_zas_paths=(
  /opt/homebrew/opt/zsh-autosuggestions/share/zsh-autosuggestions/zsh-autosuggestions.zsh
  /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh
)
for _p in $_zas_paths; do [[ -f "$_p" ]] && source "$_p" && break; done
unset _zas_paths _p

if command -v fzf &>/dev/null; then
  if _fzf_init="$(fzf --zsh 2>/dev/null)"; then
    eval "$_fzf_init"
  else
    # fzf < 0.48 (Ubuntu 24.04, Debian 12) has no --zsh: use the packaged script
    for _p in /usr/share/doc/fzf/examples/key-bindings.zsh /usr/share/fzf/shell/key-bindings.zsh; do
      [[ -f "$_p" ]] && source "$_p" && break
    done
  fi
  unset _fzf_init _p
fi

# fd, bat and eza come from Homebrew; the Linux install has none of them
if command -v fd &>/dev/null; then
  export FZF_DEFAULT_COMMAND="fd --type f --hidden --exclude .git"
  export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
  export FZF_ALT_C_COMMAND="fd --type d --hidden --exclude .git"
fi
command -v bat &>/dev/null && export FZF_CTRL_T_OPTS="--preview 'bat --color=always --line-range :500 {}'"
command -v eza &>/dev/null && export FZF_ALT_C_OPTS="--preview 'eza --tree --level=2 --color=always {}'"

# =============================================================================
# Tool completions
# =============================================================================
command -v gopass &>/dev/null && source <(gopass completion zsh)

# =============================================================================
# Yazi: cd on exit
# =============================================================================
function y() {
  local tmp="$(mktemp -t "yazi-cwd.XXXXXX")" cwd
  yazi "$@" --cwd-file="$tmp"
  if cwd="$(command cat -- "$tmp")" && [ -n "$cwd" ] && [ "$cwd" != "$PWD" ]; then
    builtin cd -- "$cwd"
  fi
  rm -f -- "$tmp"
}

# =============================================================================
# Starship prompt
# =============================================================================
eval "$(starship init zsh)"
