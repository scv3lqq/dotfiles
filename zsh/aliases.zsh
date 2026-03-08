# Custom aliases
alias n='nvim'
alias lzd='lazydocker'
alias gst='git status'

# fzf
alias nf='nvim $(fzf --preview "bat --color=always {}")'
alias gcof='git branch --all | fzf --preview "git log --oneline -10 {}" | xargs git checkout'
alias fkill='ps aux | fzf | awk "{print \$2}" | xargs kill'
