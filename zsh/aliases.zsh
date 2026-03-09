# Custom aliases
alias n='nvim'
alias lzd='lazydocker'
alias gst='git status'
alias gp='git push'
alias gl='git log --graph --decorate --pretty=format:"%C(yellow)%h%C(reset) %C(auto)%d%C(reset) %s%n%w(0,4,4)%b"'

# fzf
alias nf='nvim $(fzf --preview "bat --color=always {}")'
alias gcof='git branch --all | fzf --preview "git log --oneline -10 {}" | xargs git checkout'
alias fkill='ps aux | fzf | awk "{print \$2}" | xargs kill'
