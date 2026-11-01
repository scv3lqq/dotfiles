#!/bin/zsh
# Usage: watch.zsh <slug> <status-file> [cap-hours=4]
# Prints exactly one line and exits: STATUS <content> | WINDOW GONE | TIMEOUT |
# PROMPT trust | PROMPT permission | IDLE api-error | STALL | CAPTURE FAILED.
# Presses Enter itself only on "Press enter to continue" (logged to <status-file>.log).
# Never approves a permission prompt or trust dialog.
# Test overrides: WATCH_INTERVAL (s, default 30), WATCH_STALL (s, default 1800), WATCH_CAP_SECS.
slug=$1 sfile=$2 cap=${3:-4}
[[ -n $slug && -n $sfile ]] || { print -u2 "usage: watch.zsh <slug> <status-file> [cap-hours]"; exit 2; }
[[ $slug =~ '^[A-Za-z0-9_-]+$' && ! $slug =~ '^[0-9]+$' ]] || { print -u2 "watch.zsh: bad slug (letters, digits, - _; not all digits)"; exit 2; }
[[ $cap =~ '^[0-9]+(\.[0-9]+)?$' ]] || { print -u2 "watch.zsh: cap-hours must be a number"; exit 2; }
interval=${WATCH_INTERVAL:-30}
stall=${WATCH_STALL:-1800}
capsecs=${WATCH_CAP_SECS:-$(( cap * 3600 ))}
log=$sfile.log apierr=$sfile.apierr entered=$sfile.entered
tgt=":=$slug"

# keep the Mac awake until this script ends
caffeinate -i -w $$ &
cafpid=$!
trap 'kill $cafpid 2>/dev/null' EXIT

start=$SECONDS lasthash= lastchange=$SECONDS
# let a restarted session show its spinner before the first poll
sleep $interval
while true; do
  if [[ -f $sfile ]]; then
    content=$(<$sfile)
    if [[ -n ${content//[[:space:]]/} ]]; then
      print -r -- "STATUS ${content//$'\n'/ }"; exit 0
    fi
  fi
  if ! tmux list-windows -F '#{window_name}' 2>/dev/null | grep -qxF -- "$slug"; then
    print "WINDOW GONE"; exit 0
  fi
  if (( SECONDS - start >= capsecs )); then
    print "TIMEOUT"; exit 0
  fi
  if ! pane=$(tmux capture-pane -p -t $tgt 2>/dev/null); then
    if tmux list-windows -F '#{window_name}' 2>/dev/null | grep -qxF -- "$slug"; then
      print "CAPTURE FAILED"
    else
      print "WINDOW GONE"
    fi
    exit 0
  fi
  tail25=$(print -r -- "$pane" | grep -v '^[[:space:]]*$' | tail -n 25)
  tail12=$(print -r -- "$tail25" | tail -n 12)
  # live dialogs only: question line plus its numbered menu within the last lines
  if print -r -- "$tail12" | grep -qE '[0-9]\. Yes, I trust this folder' \
     && print -r -- "$tail12" | grep -qiE 'trust'; then
    print "PROMPT trust"; exit 0
  fi
  if print -r -- "$tail12" | grep -qE '(Do you want|Would you like) .*\?' \
     && print -r -- "$tail12" | grep -qE '^[[:space:]]*[>❯]?[[:space:]]*1\. Yes'; then
    print "PROMPT permission"; exit 0
  fi
  # footer line right under "Your usage limit has reset"; the transcript form must not match
  if print -r -- "$tail25" | awk '/^[ \t]*Press enter to continue[ \t]*$/ && prev ~ /Your usage limit has reset/ {f=1} {prev=$0} END{exit !f}'; then
    if [[ ! -e $entered ]]; then
      tmux send-keys -t $tgt Enter
      print -r -- "$(date '+%F %T') pressed Enter on 'Press enter to continue' in $slug" >>$log
      : >$entered
      lasthash= lastchange=$SECONDS
      sleep $interval; continue
    fi
  else
    rm -f $entered
  fi
  busy=0
  print -r -- "$tail25" | grep -qE 'esc to interrupt|Waiting for [0-9]+ background' && busy=1
  errline=$(print -r -- "$tail25" | grep 'API Error:' | tail -n 1)
  if [[ -n $errline ]] && (( ! busy )) && [[ $errline != "$(cat $apierr 2>/dev/null)" ]]; then
    print -r -- "$errline" >$apierr
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
