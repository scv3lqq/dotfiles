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
# Path
# =============================================================================
eval "$(/opt/homebrew/bin/brew shellenv)"
export PATH="$HOME/.local/bin:$PATH"

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
FPATH="/opt/homebrew/share/zsh-completions:$FPATH"
autoload -Uz compinit
compinit -d "$HOME/.cache/zsh/zcompdump"

zstyle ':completion:*' menu select
zstyle ':completion:*' matcher-list 'm:{a-z}={A-Z}'

# =============================================================================
# Plugins
# =============================================================================
source /opt/homebrew/opt/zsh-fast-syntax-highlighting/share/zsh-fast-syntax-highlighting/fast-syntax-highlighting.plugin.zsh
source /opt/homebrew/opt/zsh-autosuggestions/share/zsh-autosuggestions/zsh-autosuggestions.zsh
eval "$(fzf --zsh)"

export FZF_DEFAULT_COMMAND="fd --type f --hidden --exclude .git"
export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
export FZF_ALT_C_COMMAND="fd --type d --hidden --exclude .git"
export FZF_CTRL_T_OPTS="--preview 'bat --color=always --line-range :500 {}'"
export FZF_ALT_C_OPTS="--preview 'eza --tree --level=2 --color=always {}'"

# =============================================================================
# Starship prompt
# =============================================================================
eval "$(starship init zsh)"
