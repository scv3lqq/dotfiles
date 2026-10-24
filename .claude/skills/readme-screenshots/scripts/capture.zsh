#!/bin/zsh
# README screenshots: demo tmux server + Ghostty clone on AeroSpace workspace 5.
set -uo pipefail
R=${0:A:h}
S=${R:h}
L=dotfiles-demo
APP=$S/spike/GhosttyDemo.app
BID=com.mitchellh.ghostty.demo
CLAUDE=$S/spike/bin/claude
RAW=$R/raw
OUT=$HOME/dotfiles/assets/screenshots
PORT=16266
LSREG=/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister
STARTED=0
CLEANED=0
typeset -a WINS
t() { env -u TMUX tmux -L $L "$@"; }
die() { print -u2 "capture: $*"; exit 1; }

env_snapshot() { # env_snapshot <file>
  {
    print '# tmux sessions'
    env -u TMUX tmux list-sessions -F '#{session_name}' 2>/dev/null
    print '# focused'
    aerospace list-workspaces --focused
    print '# visible per monitor'
    local m
    for m in ${(f)"$(aerospace list-monitors --format '%{monitor-id}')"}; do
      print "$m=$(aerospace list-workspaces --monitor $m --visible)"
    done
    print '# windows'
    aerospace list-windows --all --format '%{window-id} %{app-bundle-id}' | awk -v b=$BID '$2 != b {print $1}' | sort
    print '# nvim sessions'
    ls ~/.local/share/nvim/sessions 2>/dev/null || print ''
    print '# ghostty keeps'
    defaults read com.mitchellh.ghostty NSQuitAlwaysKeepsWindows 2>/dev/null || print unset
  } >$1
}

clone_pids() { pgrep -f "$APP/Contents/MacOS/ghostty"; }

cleanup() {
  (( CLEANED )) && return
  CLEANED=1
  (( STARTED )) || return
  trap - EXIT INT TERM
  curl -s -m 2 -XPOST 127.0.0.1:$PORT -d abort >/dev/null 2>&1
  t set-environment -gu FZF_DEFAULT_OPTS >/dev/null 2>&1
  t kill-server >/dev/null 2>&1
  local i
  for i in {1..50}; do clone_pids >/dev/null || break; sleep 0.2; done
  clone_pids >/dev/null && pkill -f "$APP/Contents/MacOS/ghostty"
  for i in {1..25}; do
    [[ -z $(aerospace list-windows --monitor all --app-bundle-id $BID --format '%{window-id}') ]] && break
    sleep 0.2
  done
  local line
  for line in ${(f)"$(sed -n '/^# visible per monitor/,/^# windows/p' $R/env-before.txt | grep '=')"}; do
    aerospace workspace ${line#*=}
  done
  aerospace workspace "$FOCUS_BEFORE"
  $LSREG -u $APP >/dev/null 2>&1
  defaults delete $BID >/dev/null 2>&1
  local now
  now=$(defaults read com.mitchellh.ghostty NSQuitAlwaysKeepsWindows 2>/dev/null || print unset)
  if [[ $KEEPS_BEFORE == 1 && $now != 1 ]]; then
    defaults write com.mitchellh.ghostty NSQuitAlwaysKeepsWindows -bool true
  fi
  [[ -f $R/zsh_history.orig ]] && cp $R/zsh_history.orig $R/zsh_history
  [[ -e $HOME/code ]] && mv $HOME/code $R/code.$(date +%s)
  sleep 0.5
  env_snapshot $R/env-after.txt
}
trap cleanup EXIT
trap 'exit 1' INT TERM

# 1. preflight
[[ -d $HOME/code ]] || die '~/code missing'
for tool in magick swiftc yazi nvim go; do
  command -v $tool >/dev/null || die "missing $tool"
done
[[ -x $HOME/.local/share/nvim/mason/bin/gopls ]] || die 'missing gopls'
RETINA=$(aerospace list-monitors | awk -F' \\| ' '$2 == "Built-in Retina Display" {print $1}')
[[ -n $RETINA ]] || die 'no Built-in Retina Display monitor'
[[ -z $(aerospace list-windows --workspace 5) ]] || die 'workspace 5 not empty'
nc -z 127.0.0.1 $PORT 2>/dev/null && die "port $PORT in use"
[[ -x $R/bin/ocr && -x $S/spike/bin/winbounds && -x $CLAUDE && -d $APP ]] || die 'missing helper binaries'

# 2. environment before
mkdir -p $RAW $OUT
env_snapshot $R/env-before.txt
FOCUS_BEFORE=$(aerospace list-workspaces --focused)
KEEPS_BEFORE=$(defaults read com.mitchellh.ghostty NSQuitAlwaysKeepsWindows 2>/dev/null || print unset)
rm -f $R/env-after.txt
cp $R/zsh_history $R/zsh_history.orig
STARTED=1

# 3. tmux server
{
  sed '/^# Plugins/,$d' $HOME/dotfiles/tmux/tmux.conf | sed "s|^bind r source-file .*|bind r source-file $R/tmux.conf \\\; display \"Reloaded\"|"
  print '# Plugins: direct run-shell, no TPM'
  print 'set -g @tmux-dotbar-bg "#0B0E14"'
  print 'run-shell ~/.tmux/plugins/tmux-dotbar/dotbar.tmux'
  print 'run-shell ~/.tmux/plugins/vim-tmux-navigator/vim-tmux-navigator.tmux'
} >$R/tmux.conf
t kill-server >/dev/null 2>&1
env -u TMUX DEMO_HIST=$R/zsh_history tmux -L $L -f $R/tmux.conf new-session -d -s orders -n editor -c ~/code/orders-api || die 'tmux start failed'
t new-window -d -t orders: -n shell -c ~/code/orders-api
t new-window -d -t orders: -n claude -c ~/code/orders-api
t new-session -d -s billing -n files -c ~/code/billing-worker
t new-window -d -t billing: -n claude -c ~/code/billing-worker
t new-session -d -s gateway -n shell -c ~/code/api-gateway
sleep 2

open_win() { # open_win <target> -> prints the new window id
  local before id= i
  before=$(aerospace list-windows --monitor all --app-bundle-id $BID --format '%{window-id}' | sort)
  open -na $APP --args --window-save-state=never --auto-update=off \
    -e /opt/homebrew/bin/tmux -L $L attach -t $1
  for i in {1..50}; do
    id=$(comm -13 <(print -r -- $before) <(aerospace list-windows --monitor all --app-bundle-id $BID --format '%{window-id}' | sort) | head -1)
    [[ -n $id ]] && break
    sleep 0.2
  done
  print -r -- $id
}

client_of() { t list-clients -F '#{client_name} #{client_session}' | awk -v s=$1 '$2 == s {print $1; exit}'; }

# 4. first window: orders:editor
aerospace workspace 5
[[ $(aerospace list-workspaces --monitor $RETINA --visible) == 5 ]] || die 'workspace 5 not on the Retina display'
W_ORDERS=$(open_win orders:editor)
[[ -n $W_ORDERS ]] || die 'no orders window'
sleep 2
C_ORDERS=$(client_of orders)
[[ -n $C_ORDERS ]] || die 'no orders client'

for p in orders:editor orders:shell billing:claude orders:claude billing:files; do
  t send-keys -t $p ' fc -p $DEMO_HIST 1000 1000; clear' Enter
done
sleep 1
for p in orders:claude billing:claude; do
  t send-keys -t $p " clear; exec $CLAUDE" Enter
done
sleep 1
t set -p -t orders:claude @claude_state waiting
t select-pane -t orders:claude -T '✳ Add idempotency keys to order creation'
t set -p -t billing:claude @claude_state done
t select-pane -t billing:claude -T '✳ Retry failed invoice webhooks'
t send-keys -t billing:files ' yazi internal/worker/retry.go' Enter
t send-keys -t orders:editor " nvim -i NONE -c 'silent AutoSession disable' -O +/Idempotency-Key internal/handler/orders.go internal/handler/orders_test.go" Enter
sleep 8
t send-keys -t orders:editor zz
t send-keys -t orders:editor ':nohlsearch | echo' Enter
sleep 1
for p in orders:editor orders:shell billing:claude orders:claude; do t clear-history -t $p; done
cap=$(t capture-pane -p -t orders:editor)
[[ $cap == *Idempotency-Key* ]] || die 'nvim pane lacks Idempotency-Key'
[[ $(print -r -- $cap | tail -1) != *Session* ]] || die 'nvim last line shows Session'
screencapture -x -o -l $W_ORDERS $RAW/nvim.png || die 'nvim capture failed'

# 5. picker
now=$(date +%s)
t set -p -t billing:claude @claude_since $(( now - 120 ))
t set -p -t orders:claude @claude_since $(( now - 45 ))
fzf_orig=$(t show-environment -g FZF_DEFAULT_OPTS 2>/dev/null)
if [[ $fzf_orig == FZF_DEFAULT_OPTS=* ]]; then
  fzf_new="${fzf_orig#FZF_DEFAULT_OPTS=} --listen=127.0.0.1:$PORT"
else
  fzf_new="--listen=127.0.0.1:$PORT"
fi
t set-environment -g FZF_DEFAULT_OPTS $fzf_new
(t send-keys -K -c $C_ORDERS C-a s >/dev/null 2>&1 &)
for _ in {1..50}; do nc -z 127.0.0.1 $PORT 2>/dev/null && break; sleep 0.2; done
if [[ $fzf_orig == FZF_DEFAULT_OPTS=* ]]; then
  t set-environment -g FZF_DEFAULT_OPTS ${fzf_orig#FZF_DEFAULT_OPTS=}
else
  t set-environment -gu FZF_DEFAULT_OPTS
fi
nc -z 127.0.0.1 $PORT 2>/dev/null || die 'picker did not start'
# sessions sort by name, so `first` would land on billing: jump to the orders row
opos=$(curl -s "127.0.0.1:$PORT?limit=30" | jq -r '[.matches[].text] | map(test("[▸▾] orders ")) | index(true) // empty')
[[ -n $opos ]] || die 'orders row not in picker'
curl -s -XPOST 127.0.0.1:$PORT -d "pos($((opos + 1)))"
curl -s -XPOST 127.0.0.1:$PORT -d "transform($HOME/dotfiles/tmux/session-picker.sh right {1} {2} {3})"
sleep 1
lst=$(curl -s "127.0.0.1:$PORT?limit=30")
print -r -- $lst >$R/picker-debug.txt
for w in editor idempotency invoice; do
  [[ ${lst:l} == *$w* ]] || die "picker lacks $w"
done
sleep 1
screencapture -x -o -l $W_ORDERS $RAW/picker.png || die 'picker capture failed'
curl -s -XPOST 127.0.0.1:$PORT -d abort >/dev/null
sleep 1

# 6. yazi
t switch-client -c $C_ORDERS -t billing:files
sleep 2
[[ $(t capture-pane -p -t billing:files) == *retry.go* ]] || die 'yazi pane lacks retry.go'
screencapture -x -o -l $W_ORDERS $RAW/yazi.png || die 'yazi capture failed'
t switch-client -c $C_ORDERS -t orders:editor
sleep 1

# 7. layout
W_BILLING=$(open_win billing:files)
[[ -n $W_BILLING ]] || die 'no billing window'
W_GATEWAY=$(open_win gateway:shell)
[[ -n $W_GATEWAY ]] || die 'no gateway window'
sleep 2
t send-keys -t gateway:shell ' fc -p $DEMO_HIST 1000 1000; clear' Enter
sleep 1
aerospace flatten-workspace-tree --workspace 5
aerospace layout --workspace 5 --root tiles horizontal
aerospace join-with --window-id $W_GATEWAY left
sleep 2
sizes=$(t list-clients -F '#{client_session}=#{client_width}x#{client_height}' | sort | xargs)
print "client sizes: $sizes"
szchk() { # szchk <session> <w> <h>
  local s
  s=$(t list-clients -F '#{client_session} #{client_width} #{client_height}' | awk -v n=$1 '$1 == n')
  local cw=${${=s}[2]} ch=${${=s}[3]}
  (( cw >= $2 - 6 && cw <= $2 + 6 && ch >= $3 - 4 && ch <= $3 + 4 )) || die "client $1 is ${cw}x${ch}, expected about $2x$3"
}
szchk orders 77 42
szchk billing 77 20
szchk gateway 77 20
# gateway output only now: tab-separated go test output reflows when the window shrinks
t send-keys -t gateway:shell ' clear' Enter
sleep 1
t clear-history -t gateway:shell
t send-keys -t gateway:shell 'go test ./...' Enter
sleep 6
t send-keys -t gateway:shell 'git log --oneline -5' Enter
sleep 2
gw=$(t capture-pane -p -t gateway:shell)
print -r -- $gw | grep -Eq 'internal/ratelimit[[:space:]]+([0-9.]+s|\(cached\))' || die 'gateway output reflowed'
compose() { # compose <out.png> <window-id>...
  local out=$1; shift
  local args=(-size 2880x1740 'xc:#2A2F3A') id x y w h
  while read -r id x y w h; do
    screencapture -x -o -l $id $RAW/w$id.png
    args+=($RAW/w$id.png -geometry +$((x * 2))+$(((y - 30) * 2)) -composite)
  done < <($S/spike/bin/winbounds "$@")
  magick $args $out
}
compose $RAW/layout.png $W_ORDERS $W_BILLING $W_GATEWAY || die 'compose failed'

# 8. post-process
for n in layout nvim picker yazi; do
  magick $RAW/$n.png -strip -resize 1800x $OUT/$n.png || die "resize $n failed"
  # no optimizer installed: fall back to a 256-color palette when over the 1.5 MiB cap
  if (( $(stat -f %z $OUT/$n.png) > 1572864 )); then
    magick $RAW/$n.png -strip -resize 1800x -colors 256 -define png:compression-level=9 $OUT/$n.png || die "quantize $n failed"
  fi
done
print 'capture: done'
