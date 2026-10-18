#!/usr/bin/env bash
# Session tree for `prefix + s`: sessions collapsed, right/left expand and
# collapse, Enter opens a session's first window or the focused window.
# List lines are "<session_id>\t<window_id>\t<display>"; window lines carry
# their session's id in field 1, so --id-nth tracking lands on the session
# line after a collapse.
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
  # 0.71 added --id-nth
  [ "$major" -gt 0 ] || [ "$minor" -ge 71 ]
}

list() {
  local expanded
  expanded=$(tr '\n' ' ' <"$PICKER_STATE/expanded")
  tmux list-windows -a -F "$(printf '%s\t' '#{session_id}' '#{window_id}' \
    '#{session_name}' '#{session_windows}' '#{window_index}' '#{window_name}' \
    '#{pane_current_command}' '#{?#{==:#{pane_title},#{host}},,#{pane_title}}' \
    '#{pane_current_path}')" |
    LC_ALL=C awk -F '\t' -v cur="$PICKER_CURRENT" -v expd=" $expanded " \
      -v search="${FZF_QUERY:+1}" -v home="$HOME" '
      BEGIN {
        grey = "86;91;102"; dim = "71;82;102"; blue = "89;194;255"
        accent = "230;180;80"; green = "170;217;76"; yellow = "255;180;84"
        cyan = "149;230;203"; fg = "191;189;182"
        version = "^[0-9]+\\.[0-9]+\\.[0-9]+$"
      }
      function c(rgb, s) { return "\033[38;2;" rgb "m" s "\033[0m" }
      {
        n++; sid[n] = $1; wid[n] = $2; sname[n] = $3; swin[n] = $4
        widx[n] = $5; wname[n] = $6; cmd[n] = $7; title[n] = $8; path[n] = $9
        if (length($3) > width) width = length($3)
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
            printf "%s\t\t%s %s  %s%s\n", sid[i], c(grey, open ? "▾" : "▸"), name, c(dim, count), mark
          }
          if (!open) continue
          if (cmd[i] ~ version || cmd[i] == "claude") icon = c(yellow, "\363\260\232\251")
          else if (cmd[i] ~ /^n?vim$/) icon = c(green, "\356\230\253")
          else if (cmd[i] ~ /^(zsh|bash|sh|fish)$/) icon = c(cyan, "\356\236\225")
          else icon = c(fg, "\357\213\220")
          wn = wname[i] ~ version ? "claude" : wname[i]
          # Claude prefixes its title with a 3-byte glyph: idle mark or spinner
          t = title[i]
          if (substr(t, 1, 1) == "\342" && substr(t, 4, 1) == " ") t = substr(t, 5)
          p = path[i]
          if (p == home || index(p, home "/") == 1) p = "~" substr(p, length(home) + 1)
          info = t != "" ? t : p
          if (search) lead = c(dim, sname[i] " ›")
          else lead = c(dim, (i == n || sid[i + 1] != sid[i]) ? "  └─" : "  ├─")
          printf "%s\t%s\t%s %s  %s %-14s %s\n", sid[i], wid[i], lead, c(grey, widx[i]), icon, wn, c(grey, info)
        }
      }'
}

toggle() {
  if [ -n "${FZF_QUERY:-}" ]; then
    if [ "$1" = right ]; then echo forward-char; else echo backward-char; fi
    return
  fi
  [ -n "$2" ] || return 0
  grep -vxF -- "$2" "$PICKER_STATE/expanded" >"$PICKER_STATE/next"
  [ "$1" = right ] && echo "$2" >>"$PICKER_STATE/next"
  mv "$PICKER_STATE/next" "$PICKER_STATE/expanded"
  echo "track-current+reload-sync($self list)"
}

preview() {
  tmux capture-pane -ep -t "${2:-$1:^}" |
    awk '{ l[NR] = $0; s = $0; gsub(/\033\[[0-9;:]*[A-Za-z]/, "", s); if (s ~ /[^ \t]/) last = NR }
      END { for (i = 1; i <= last; i++) print l[i] }'
}

open_target() {
  [ -n "$1" ] || return 0
  tmux select-window -t "${2:-$1:^}" \; switch-client -t "$1"
}

kill_target() {
  [ -n "$1" ] || return 0
  if [ -n "$2" ]; then tmux kill-window -t "$2"; else tmux kill-session -t "$1"; fi
}

main() {
  local lines pos
  PICKER_STATE=$(mktemp -d) || exit 1
  PICKER_CURRENT=$(tmux display-message -p '#{session_id}')
  export PICKER_STATE PICKER_CURRENT
  trap 'rm -rf "$PICKER_STATE"' EXIT
  : >"$PICKER_STATE/expanded"
  lines=$(list)
  pos=$(printf '%s\n' "$lines" | awk -F '\t' -v cur="$PICKER_CURRENT" '$1 == cur { print NR; exit }')
  printf '%s\n' "$lines" | fzf --ansi --delimiter '\t' --with-nth 3.. --id-nth 1 \
    --layout reverse --style full:rounded --info inline-right --highlight-line \
    --prompt '❯ ' --pointer '▌' --gutter ' ' \
    --ghost 'search sessions and windows' \
    --list-label ' sessions ' --preview-label ' preview ' \
    --footer '↵ open   → expand   ← collapse   ^d kill   esc close' \
    --color 'bg:#0B0E14,bg+:#122133,fg:#BFBDB6,fg+:#E6E1CF,hl:#E6B450,hl+:#E6B450' \
    --color 'border:#475266,label:#E6B450,prompt:#59C2FF,pointer:#E6B450,query:#BFBDB6' \
    --color 'info:#565B66,footer:#565B66,ghost:#475266,spinner:#95E6CB' \
    --color 'scrollbar:#475266,gutter:#0B0E14,preview-bg:#0B0E14' \
    --preview "$self preview {1} {2}" \
    --preview-window 'right,55%,follow,<55(down,45%,follow)' \
    --bind "load:pos(${pos:-1})+unbind(load)" \
    --bind "right:transform($self right {1} {2})" \
    --bind "left:transform($self left {1} {2})" \
    --bind "change:untrack-current+reload-sync($self list)" \
    --bind "ctrl-d:execute-silent($self kill {1} {2})+track-current+reload-sync($self list)" \
    --bind "enter:become($self open {1} {2})"
}

case "${1:-}" in
  --supported) supported ;;
  list) list ;;
  right | left) toggle "$1" "${2:-}" ;;
  preview) preview "$2" "${3:-}" ;;
  open) open_target "$2" "${3:-}" ;;
  kill) kill_target "$2" "${3:-}" ;;
  *) main ;;
esac
