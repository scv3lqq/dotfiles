# Login shells (launchd jobs) never source .zshrc: tool PATH must live here.
[[ -x /opt/homebrew/bin/brew ]] && eval "$(/opt/homebrew/bin/brew shellenv)"
export PATH="$HOME/.local/bin:$PATH:$HOME/go/bin"
[[ -d /Applications/Obsidian.app/Contents/MacOS ]] && export PATH="$PATH:/Applications/Obsidian.app/Contents/MacOS"
