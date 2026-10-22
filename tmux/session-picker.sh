#!/usr/bin/env bash
# Session tree for `prefix + s`: sessions collapsed, right/left expand and
# collapse, Enter opens a session's first window or the focused window.
# Claude panes that are mid-turn or waiting on background agents are listed in
# a section pinned to the bottom of the list, refreshed every 2 s.
# State: pane options from claude/hooks/pane-state.sh.
# List lines are "<session_id>\t<target>\t<aux>\t<display>":
#   session line  $sid  (empty)   (empty)          tree row
#   window line   $sid  @wid      session row N    tree row under an open session
#   active row    $sid  %pid      (empty)          Claude pane mid-turn
#   filler/rule   (empty)(empty)  U:D              non-selectable, U/D = rows to
#                                                  jump to when moving up/down
# --id-nth 1,2 gives every selectable line a unique key, so a reload that
# keeps the focused key fires no focus event. No reload is tracked (tracking
# blocks the UI and drops keys): an untracked reload keeps the cursor index,
# collapse, kill and right on a window line move to the session row (aux).
set -u

self=$0

supported() {
  local v major minor
  v=$(fzf --version 2>/dev/null) || return 1
  v=${v%% *}
  major=${v%%.*}
  minor=${v#*.}
  minor=${minor%%.*}
  case "$major$minor" in '' | *[!0-9]*) return 1 ;; esac
  # 0.73 added the every(N) event (0.71 --id-nth)
  [ "$major" -gt 0 ] || [ "$minor" -ge 73 ]
}

# List rows for an fzf of $1 lines whose preview content starts at row $2
# (0-based, as $FZF_PREVIEW_TOP): input 3 + list border 2 + footer 3 rows,
# plus the preview and its border when the preview sits below the list.
list_height() {
  case "$1$2" in '' | *[!0-9]*) echo 0; return ;; esac
  if [ "$1" -le 0 ]; then echo 0
  elif [ "$2" -gt 1 ]; then echo $(($2 - 9))
  else echo $(($1 - 8)); fi
}

# Height before fzf runs (it exports no size to the input command): mirrors
# --preview-window 'right,55%,...,<55(down,45%,...)'. The load tick fixes a miss.
estimate_height() {
  local size rows cols top=1
  size=$(stty size </dev/tty 2>/dev/null) || { echo 0; return; }
  rows=${size% *}
  cols=${size#* }
  case "$rows$cols" in '' | *[!0-9]*) echo 0; return ;; esac
  [ $((cols * 55 / 100)) -lt 55 ] && top=$((rows - rows * 45 / 100 + 1))
  list_height "$rows" "$top"
}

# $1 list height (0: unknown, no fillers), $2 file for the non-selectable count
render() {
  local expanded
  expanded=$(tr '\n' ' ' <"$PICKER_STATE/expanded")
  tmux list-panes -a -F "$(printf '%s\t' '#{session_id}' '#{window_id}' '#{pane_id}' \
    '#{pane_active}' '#{session_name}' '#{session_windows}' '#{window_index}' \
    '#{pane_index}' '#{window_name}' '#{pane_current_command}' \
    '#{?#{==:#{pane_title},#{host}},,#{pane_title}}' '#{pane_current_path}' \
    '#{@claude_state}' '#{@claude_since}' '#{window_activity}')" |
    LC_ALL=C awk -F '\t' -v cur="$PICKER_CURRENT" -v expd=" $expanded " \
      -v search="${FZF_QUERY:+1}" -v home="$HOME" -v height="$1" \
      -v skipfile="$2" -v now="$(date +%s)" '
      BEGIN {
        grey = "86;91;102"; dim = "71;82;102"; blue = "89;194;255"
        accent = "230;180;80"; green = "170;217;76"; yellow = "255;180;84"
        cyan = "149;230;203"; fg = "191;189;182"; orange = "255;143;64"
        version = "^[0-9]+\\.[0-9]+\\.[0-9]+$"
      }
      function c(rgb, s) { return "\033[38;2;" rgb "m" s "\033[0m" }
      # Claude prefixes its title with a 3-byte glyph: idle mark or spinner
      function strip(t) {
        if (substr(t, 1, 1) == "\342" && substr(t, 4, 1) == " ") return substr(t, 5)
        return t
      }
      function short(p) {
        if (p == home || index(p, home "/") == 1) p = "~" substr(p, length(home) + 1)
        return p
      }
      function ago(s, d) {
        if (s !~ /^[0-9]+$/) return "?"
        d = now - s; if (d < 0) d = 0
        if (d < 60) return d "s"
        if (d < 3600) return int(d / 60) "m"
        return sprintf("%dh%02dm", int(d / 3600), int(d % 3600 / 60))
      }
      {
        claude = $10 ~ version || $10 == "claude"
        # Esc or a denied prompt ends a turn without a hook event; a working
        # Claude redraws its spinner (its background agents their timer) every
        # second, so a silent window is idle
        busy = $13 == "waiting" || (($13 == "working" || $13 == "agents") && now - $15 <= 5)
        if (busy && claude) {
          na++; asid[na] = $1; apid[na] = $3; aname[na] = $5; aw[na] = $7 "." $8
          ast[na] = $13; asince[na] = $14; atitle[na] = strip($11); apath[na] = $12
        }
        if ($4 != 1) next
        n++; sid[n] = $1; wid[n] = $2; sname[n] = $5; swin[n] = $6
        widx[n] = $7; wname[n] = $9; cmd[n] = $10; title[n] = $11; path[n] = $12
        if (length($5) > width) width = length($5)
      }
      END {
        for (i = 1; i <= n; i++) {
          if (sid[i] != prev) {
            prev = sid[i]
            open = search || index(expd, " " sid[i] " ")
            name = sprintf("%-" width "s", sname[i])
            name = sid[i] == cur ? "\033[1m" c(accent, name) : c(blue, name)
            count = swin[i] (swin[i] == 1 ? " window" : " windows")
            mark = sid[i] == cur ? "  " c(green, "●") : ""
            printf "%s\t\t\t%s %s  %s%s\n", sid[i], c(grey, open ? "▾" : "▸"), name, c(dim, count), mark
            out++; srow = out
          }
          if (!open) continue
          if (cmd[i] ~ version || cmd[i] == "claude") icon = c(yellow, "\363\260\232\251")
          else if (cmd[i] ~ /^n?vim$/) icon = c(green, "\356\230\253")
          else if (cmd[i] ~ /^(zsh|bash|sh|fish)$/) icon = c(cyan, "\356\236\225")
          else icon = c(fg, "\357\213\220")
          wn = wname[i] ~ version ? "claude" : wname[i]
          t = strip(title[i])
          info = t != "" ? t : short(path[i])
          if (search) lead = c(dim, sname[i] " ›")
          else lead = c(dim, (i == n || sid[i + 1] != sid[i]) ? "  └─" : "  ├─")
          printf "%s\t%s\t%s\t%s %s  %s %-14s %s\n", sid[i], wid[i], srow, lead, c(grey, widx[i]), icon, wn, c(grey, info)
          out++
        }
        skip = 0
        if (na && !search) {
          fill = height - out - 1 - na
          if (fill < 0) fill = 0
          ud = out ":" (out + fill + 2)
          for (i = 1; i <= fill; i++) printf "\t\t%s\t\n", ud
          printf "\t\t%s\t%s\n", ud, c(dim, "  ── claude ──")
          skip = fill + 1
        }
        for (i = 1; i <= na; i++) {
          w = ast[i] == "waiting"
          if (w) mk = c(orange, "\357\203\263")
          else if (ast[i] == "agents") mk = c(cyan, "\357\203\200")
          else mk = c(cyan, "\357\204\220")
          t = atitle[i] != "" ? atitle[i] : short(apath[i])
          printf "%s\t%s\t\t  %s %s  %s  %s\n", asid[i], apid[i], mk,
            c(w ? orange : fg, sprintf("%-" width "s › %-5s", aname[i], aw[i])),
            c(grey, sprintf("%5s", ago(asince[i]))), c(w ? orange : grey, t)
        }
        if (skipfile != "") print skip > skipfile
      }'
}

# $1 list height (default: from the fzf environment)
list() {
  local h=${1:-$(list_height "${FZF_LINES:-0}" "${FZF_PREVIEW_TOP:-1}")}
  render "$h" "$PICKER_STATE/skip.new" >"$PICKER_STATE/shown.new"
  mv "$PICKER_STATE/skip.new" "$PICKER_STATE/skip"
  mv "$PICKER_STATE/shown.new" "$PICKER_STATE/shown"
  cat "$PICKER_STATE/shown"
}

# every(2), resize and the first load ($1 $2: key of the focused line): reload
# only when the list changed, never tracked (a tracked reload blocks the UI
# and drops keys typed meanwhile). An untracked reload keeps the cursor index;
# when the focused tree line moved, the next load event moves it (loaded).
tick() {
  local next="$PICKER_STATE/next" diff m act
  render "$(list_height "${FZF_LINES:-0}" "${FZF_PREVIEW_TOP:-1}")" "$next.skip" \
    >"$next" 2>/dev/null || return 0
  [ -s "$next" ] || return 0
  diff=$(LC_ALL=C awk -F '\t' '
    FILENAME == ARGV[1] { a[FNR] = $0; k[FNR] = $1 FS $2; n = FNR; next }
    { if ($0 != a[FNR]) d = 1; if ($1 FS $2 != k[FNR]) kd = 1; m = FNR }
    END { print (kd || m != n) ? "keys" : d ? "text" : "same" }' \
    "$PICKER_STATE/shown" "$next" 2>/dev/null)
  [ "$diff" = same ] && return 0
  mv "$next.skip" "$PICKER_STATE/skip"
  mv "$next" "$PICKER_STATE/shown"
  # single quotes: $PICKER_STATE expands in fzf's child shell
  act='reload-sync(cat "$PICKER_STATE/shown")'
  if [ "$diff" = keys ] && [ -z "${FZF_QUERY:-}" ] && [ -n "${1:-}" ]; then
    # the focused line's new row; if it is gone and a filler takes its row,
    # the filler's down target (fzf < 0.74.5 fires no focus event there)
    m=$(LC_ALL=C awk -F '\t' -v s="$1" -v w="${2:-}" -v p="${FZF_POS:-0}" '
      $1 == s && $2 == w { print NR; found = 1; exit }
      NR == p && $1 == "" { split($3, ud, ":"); alt = ud[2] }
      END { if (!found && alt != "") print alt }' "$PICKER_STATE/shown")
    if [ -n "$m" ] && [ "$m" != "${FZF_POS:-0}" ]; then
      echo "$m" >"$PICKER_STATE/pos"
      act="rebind(load)+$act"
    fi
  fi
  echo "$act"
}

# load (bound once, re-armed by tick): the initial cursor and the first tick,
# or the position a tick left for the reloaded list
loaded() {
  local m out=
  if read -r m 2>/dev/null <"$PICKER_STATE/pos"; then
    rm -f "$PICKER_STATE/pos"
    [ -z "${FZF_QUERY:-}" ] && out="pos($m)"
  fi
  if [ -f "$PICKER_STATE/first" ]; then
    rm -f "$PICKER_STATE/first"
    out="${out:+$out+}transform($self tick {1} {2})"
  fi
  echo "$out"
}

# Never rest on a filler or the rule: jump to the row above or below it
skip_row() {
  [ -z "$1" ] || return 0
  case "$2" in *:*) ;; *) return 0 ;; esac
  local up=${2%%:*} down=${2#*:} pos=${FZF_POS:-0}
  case "${FZF_ACTION:-}" in
    *up*) echo "pos($up)" ;;
    *click*) if [ $((pos - up)) -le $((down - pos)) ]; then echo "pos($up)"; else echo "pos($down)"; fi ;;
    *) echo "pos($down)" ;;
  esac
}

toggle() {
  if [ -n "${FZF_QUERY:-}" ]; then
    if [ "$1" = right ]; then echo forward-char; else echo backward-char; fi
    return
  fi
  [ -n "$2" ] || return 0
  case "$3" in %*) return 0 ;; esac
  # right on a window line keeps its old effect: the cursor goes to the session line
  if [ "$1" = right ] && [ -n "$4" ]; then echo "pos($4)"; return; fi
  grep -vxF -- "$2" "$PICKER_STATE/expanded" >"$PICKER_STATE/expanded.new"
  [ "$1" = right ] && echo "$2" >>"$PICKER_STATE/expanded.new"
  mv "$PICKER_STATE/expanded.new" "$PICKER_STATE/expanded"
  # untracked: only rows below the session line change, so its index holds
  # (a tracked reload would drop a key typed right after the arrow)
  if [ "$1" = left ] && [ -n "$4" ]; then echo "pos($4)+reload-sync($self list)"
  else echo "reload-sync($self list)"; fi
}

preview() {
  [ -n "$1" ] || return 0
  tmux capture-pane -ep -t "${2:-$1:^}" |
    awk '{ l[NR] = $0; s = $0; gsub(/\033\[[0-9;:]*[A-Za-z]/, "", s); if (s ~ /[^ \t]/) last = NR }
      END { for (i = 1; i <= last; i++) print l[i] }'
}

enter() {
  [ -n "$1" ] && echo "become($self open {1} {2})"
}

open_target() {
  [ -n "$1" ] || return 0
  case "$2" in
    %*) tmux select-window -t "$2" \; select-pane -t "$2" \; switch-client -t "$1" ;;
    *) tmux select-window -t "${2:-$1:^}" \; switch-client -t "$1" ;;
  esac
}

kill_target() {
  [ -n "$1" ] || return 0
  case "$2" in %*) return 0 ;; esac
  if [ -n "$2" ]; then tmux kill-window -t "$2"; else tmux kill-session -t "$1"; fi
  if [ -n "$2" ] && [ -n "$3" ] && [ -z "${FZF_QUERY:-}" ]; then
    echo "pos($3)+reload-sync($self list)"
  else
    echo "reload-sync($self list)"
  fi
}

main() {
  local lines pos
  PICKER_STATE=$(mktemp -d) || exit 1
  PICKER_CURRENT=$(tmux display-message -p '#{session_id}')
  export PICKER_STATE PICKER_CURRENT
  trap 'rm -rf "$PICKER_STATE"' EXIT
  : >"$PICKER_STATE/expanded"
  lines=$(list "$(estimate_height)")
  pos=$(printf '%s\n' "$lines" | awk -F '\t' -v cur="$PICKER_CURRENT" '$1 == cur { print NR; exit }')
  echo "${pos:-1}" >"$PICKER_STATE/pos"
  : >"$PICKER_STATE/first"
  printf '%s\n' "$lines" | fzf --ansi --delimiter '\t' --with-nth 4.. --id-nth 1,2 \
    --layout reverse --style full:rounded --info inline-right --highlight-line \
    --prompt '❯ ' --pointer '▌' --gutter ' ' \
    --ghost 'search sessions and windows' \
    --list-label ' sessions ' --preview-label ' preview ' \
    --footer '↵ open   → expand   ← collapse   ^d kill   esc close' \
    --color 'bg:#0B0E14,bg+:#122133,fg:#BFBDB6,fg+:#E6E1CF,hl:#E6B450,hl+:#E6B450' \
    --color 'border:#475266,label:#E6B450,prompt:#59C2FF,pointer:#E6B450,query:#BFBDB6' \
    --color 'info:#565B66,footer:#565B66,ghost:#475266,spinner:#95E6CB' \
    --color 'scrollbar:#475266,gutter:#0B0E14,preview-bg:#0B0E14' \
    --info-command 'n=0; { read -r n <"$PICKER_STATE/skip"; } 2>/dev/null
      echo "$((FZF_MATCH_COUNT - n))/$((FZF_TOTAL_COUNT - n))"' \
    --preview "$self preview {1} {2}" \
    --preview-window 'right,55%,follow,<55(down,45%,follow)' \
    --bind "load:transform($self loaded)+unbind(load)" \
    --bind "every(2):transform($self tick {1} {2})" \
    --bind "resize:transform($self tick {1} {2})" \
    --bind "focus:transform([ -n {1} ] || $self skip {1} {3})" \
    --bind "right:transform($self right {1} {2} {3})" \
    --bind "left:transform($self left {1} {2} {3})" \
    --bind "change:untrack-current+reload-sync($self list)" \
    --bind "ctrl-d:transform($self kill {1} {2} {3})" \
    --bind "enter:transform($self enter {1})"
}

case "${1:-}" in
  --supported) supported ;;
  list) list ;;
  tick) tick "${2:-}" "${3:-}" ;;
  loaded) loaded ;;
  skip) skip_row "${2:-}" "${3:-}" ;;
  right | left) toggle "$1" "${2:-}" "${3:-}" "${4:-}" ;;
  preview) preview "${2:-}" "${3:-}" ;;
  enter) enter "${2:-}" ;;
  open) open_target "$2" "${3:-}" ;;
  kill) kill_target "${2:-}" "${3:-}" "${4:-}" ;;
  *) main ;;
esac
