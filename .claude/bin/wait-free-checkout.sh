#!/bin/bash
# Waits until this checkout can take a new branch: on a clean main and no
# other Claude pane in the repo busy (the session picker's rule: waiting, or
# working/agents with window activity <= 5 s ago), twice in a row 10 s apart.
# Usage: wait-free-checkout.sh [own pane id, default $TMUX_PANE] [max checks, default 720]
# Exit 0 when free, 1 on timeout or when the own pane is unknown.
self="${1:-${TMUX_PANE-}}"
max="${2:-720}"
repo="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)" || exit 1
if [ -z "$self" ]; then
  echo "own pane unknown: pass it or run inside tmux" >&2
  exit 1
fi

free() {
  [ "$(git -C "$repo" branch --show-current)" = main ] || return 1
  [ -z "$(git -C "$repo" status --porcelain --untracked-files=no)" ] || return 1
  tmux list-panes -a -F "$(printf '%s\t' '#{pane_id}' '#{pane_current_path}' \
    '#{@claude_state}' '#{window_activity}')" |
    awk -F '\t' -v now="$(date +%s)" -v self="$self" -v repo="$repo" '
      $1 != self && ($2 == repo || index($2, repo "/") == 1) &&
      ($3 == "waiting" || (($3 == "working" || $3 == "agents") && now - $4 <= 5)) { busy = 1 }
      END { exit busy }'
}

ok=0
i=0
while [ "$i" -lt "$max" ]; do
  i=$((i + 1))
  if free; then ok=$((ok + 1)); else ok=0; fi
  if [ "$ok" -ge 2 ]; then
    echo "free after $i checks"
    exit 0
  fi
  sleep 10
done
echo "timeout after $i checks"
exit 1
