#!/bin/zsh
# Usage: watch.zsh <slug> <status-file> [cap-hours=4]
# Prints exactly one line and exits: STATUS <content> | WINDOW GONE | TIMEOUT |
# PROMPT trust | PROMPT permission | IDLE api-error | STALL.
# Presses Enter itself only on "Press enter to continue" (logged to <status-file>.log).
# Never approves a permission prompt or trust dialog.
# Test overrides: WATCH_INTERVAL (s, default 30), WATCH_STALL (s, default 1800), WATCH_CAP_SECS.
slug=$1 sfile=$2 cap=${3:-4}
[[ -n $slug && -n $sfile ]] || { print -u2 "usage: watch.zsh <slug> <status-file> [cap-hours]"; exit 2; }
interval=${WATCH_INTERVAL:-30}
stall=${WATCH_STALL:-1800}
capsecs=${WATCH_CAP_SECS:-$(( cap * 3600 ))}
log=$sfile.log

# keep the Mac awake until this script ends
caffeinate -i -w $$ &
cafpid=$!
trap 'kill $cafpid 2>/dev/null' EXIT

start=$SECONDS lasthash= lastchange=$SECONDS
while true; do
  if [[ -s $sfile ]]; then
    print -r -- "STATUS ${$(<$sfile)//$'\n'/ }"; exit 0
  fi
  if ! tmux list-windows -a -F '#{window_name}' 2>/dev/null | grep -qxF -- "$slug"; then
    print "WINDOW GONE"; exit 0
  fi
  if (( SECONDS - start >= capsecs )); then
    print "TIMEOUT"; exit 0
  fi
  pane=$(tmux capture-pane -p -t ":=$slug" 2>/dev/null)
  tail25=$(print -r -- "$pane" | grep -v '^[[:space:]]*$' | tail -n 25)
  if print -r -- "$tail25" | grep -qiE 'Yes, I trust this folder|trust the files in this folder'; then
    print "PROMPT trust"; exit 0
  fi
  if print -r -- "$tail25" | grep -qE 'Do you want to proceed\?'; then
    print "PROMPT permission"; exit 0
  fi
  if print -r -- "$tail25" | grep -qi 'Press enter to continue'; then
    tmux send-keys -t ":=$slug" Enter
    print -r -- "$(date '+%F %T') pressed Enter on 'Press enter to continue' in $slug" >>$log
    lasthash= lastchange=$SECONDS
    sleep $interval; continue
  fi
  if print -r -- "$tail25" | grep -q 'API Error:' && ! print -r -- "$tail25" | grep -q 'esc to interrupt'; then
    print "IDLE api-error"; exit 0
  fi
  h=$(print -r -- "$pane" | md5)
  if [[ $h != $lasthash ]]; then
    lasthash=$h lastchange=$SECONDS
  elif (( SECONDS - lastchange >= stall )); then
    print "STALL"; exit 0
  fi
  sleep $interval
done
