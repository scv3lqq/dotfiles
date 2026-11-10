#!/usr/bin/env bash
# Agent inbox for `prefix + a`: agent panes (Claude Code, Codex) that need you,
# work, or finished with a result nobody opened, in an fzf popup. `status`
# prints the status bar counters and keeps the window marks.
# State: pane options from claude/hooks/pane-state.sh (@claude_state,
# @claude_since, @claude_agents, @agent_unseen, @agent_failed, @agent_report);
# `status` writes the window option @agent_mark. A wrapper shell hides the agent
# from pane_current_command, so a pane also counts when one process snapshot
# shows an agent at most 4 levels below the pane process. Codex served by the
# shared app-server has no hook state at all: its pane is working while its
# window is active.
# List lines are "<session_id>\t<pane_id>\t<class>\t<display>":
#   agent row      $sid  %pid  blocked|failed|ready|working|seen  one text line
#   header/filler  (empty)(empty)  U:D  non-selectable, U/D = rows to jump to
#                                       when moving up/down
# No reload is tracked (tracking blocks the UI and drops keys): an untracked
# reload keeps the cursor index.
set -u

self=$0
reports=${XDG_STATE_HOME:-$HOME/.local/state}/agent-inbox

# Classified agent panes, most urgent first, one tab-separated line each:
#   session_id pane_id window_id class clear tag since title path agents
# $1: now (epoch seconds). $2: 1 for `status`, where a ready or failed pane in
# front of an attached client counts as seen: it is reclassified, clear=1. One
# left idle is still listed, with an empty class, so that its marks get cleared.
# The tag comes from pane_current_command, else from the process snapshot.
panes() {
  {
    # One snapshot per call: `status` runs every 5 s. A failed ps leaves the
    # tree empty, which is the plain command filter
    ps -A -o pid=,ppid=,comm= 2>/dev/null
    echo panes
    tmux list-panes -a -F "$(printf '%s\t' '#{session_id}' '#{window_id}' '#{pane_id}' \
      '#{pane_active}' '#{window_active}' '#{session_attached}' '#{pane_current_command}' \
      '#{?#{==:#{pane_title},#{host}},,#{pane_title}}' '#{pane_current_path}' \
      '#{@claude_state}' '#{@claude_since}' '#{window_activity}' '#{@agent_unseen}' \
      '#{@agent_failed}' '#{@claude_agents}' '#{pane_pid}')"
  } | LC_ALL=C awk -F '\t' -v now="$1" -v clearfront="${2:-}" '
      BEGIN {
        OFS = "\t"
        version = "^[0-9]+\\.[0-9]+\\.[0-9]+$"
        split("blocked failed ready working seen", names, " ")
        for (i = 1; i <= 5; i++) rank[names[i]] = i
        # The empty class of a cleared idle pane sorts last
        rank[""] = 6
      }
      # First match wins; the empty string is idle: never shown or counted
      function classify(unseen, failed) {
        if (state == "waiting") return "blocked"
        if (unseen == "1" && failed == "1") return "failed"
        if (unseen == "1") return "ready"
        # Esc or a denied prompt ends a turn without a hook event; a working
        # agent redraws every second, so a silent window is idle. A Codex pane
        # served by the shared app-server never gets hook state: output is its
        # only signal
        if ((state == "working" || state == "agents" || (state == "" && client == "cx")) && act ~ /^[0-9]+$/ && now - act <= 5) return "working"
        if (state == "done") return "seen"
        return ""
      }
      # 1 when row a sorts after row b: a later rank, or the same rank and older
      function later(a, b) {
        if (rank[kls[a]] != rank[kls[b]]) return rank[kls[a]] > rank[kls[b]]
        return sec[a] < sec[b]
      }
      # Every process up to 4 hops above an agent learns the tag of the nearest
      # agent; on equal distance cc wins, so that the result does not depend on
      # the order of for-in
      function resolve(   p, q, d) {
        for (p in kind) {
          q = p
          for (d = 0; d <= 4 && q + 0 > 1; d++) {
            if (!(q in near) || d < near[q] || (d == near[q] && kind[p] == "cc")) { near[q] = d; via[q] = kind[p] }
            if (!(q in par)) break
            q = par[q]
          }
        }
      }
      # The snapshot comes first, then the marker, then the pane rows. The tag of
      # a process is its comm without the directory: macOS prints full paths,
      # blanks included
      !rows && $0 == "panes" { rows = 1; resolve(); next }
      !rows {
        if (split($0, f, " ") < 3 || f[1] !~ /^[0-9]+$/ || f[2] !~ /^[0-9]+$/) next
        c = $0
        sub(/^[ \t]*[0-9]+[ \t]+[0-9]+[ \t]+/, "", c)
        sub(/.*\//, "", c)
        par[f[1]] = f[2]
        if (c == "codex") kind[f[1]] = "cx"
        else if (c == "claude") kind[f[1]] = "cc"
        next
      }
      {
        if ($7 == "codex") client = "cx"
        else if ($7 ~ version || $7 == "claude") client = "cc"
        else if ($16 in via) client = via[$16]
        else next
        state = $10; act = $12
        cls = classify($13, $14)
        clr = 0
        if (clearfront != "" && (cls == "ready" || cls == "failed") && $4 == "1" && $5 == "1" && $6 + 0 > 0) {
          clr = 1
          cls = classify("", "")
        }
        if (cls == "" && !clr) next
        n++
        sid[n] = $1; wid[n] = $2; pid[n] = $3; kls[n] = cls; cl[n] = clr; tg[n] = client
        since[n] = $11; sec[n] = ($11 ~ /^[0-9]+$/) ? $11 + 0 : 0
        title[n] = $8; path[n] = $9; agents[n] = $15
      }
      END {
        # Insertion sort, stable on ties
        for (i = 1; i <= n; i++) {
          for (j = i; j > 1 && later(ord[j - 1], i); j--) ord[j] = ord[j - 1]
          ord[j] = i
        }
        for (k = 1; k <= n; k++) {
          i = ord[k]
          print sid[i], pid[i], wid[i], kls[i], cl[i], tg[i], since[i], title[i], path[i], agents[i]
        }
      }'
}

# The popup list (see the header); the file $AGENT_INBOX_STATE/show-seen unfolds
# the seen rows, an unset AGENT_INBOX_STATE keeps them folded
render() {
  local now show=0
  now=$(date +%s)
  [ -n "${AGENT_INBOX_STATE:-}" ] && [ -e "$AGENT_INBOX_STATE/show-seen" ] && show=1
  panes "$now" | LC_ALL=C awk -F '\t' -v now="$now" -v show="$show" '
    BEGIN {
      dim = "122;130;144"; fg = "191;189;182"; red = "240;113;120"; amber = "230;180;80"
    }
    function c(rgb, s) { return "\033[38;2;" rgb "m" s "\033[0m" }
    # Claude prefixes its title with a 3-byte glyph: idle mark or spinner
    function strip(t) {
      if (substr(t, 1, 1) == "\342" && substr(t, 4, 1) == " ") return substr(t, 5)
      return t
    }
    function base(p,   n, parts) {
      if (p ~ /^\/+$/) return "/"
      sub(/\/+$/, "", p)
      n = split(p, parts, "/")
      return parts[n]
    }
    function age(s,   d) {
      if (s !~ /^[0-9]+$/) return "-"
      d = now - s; if (d < 0) d = 0
      if (d < 60) return "<1m"
      if (d < 3600) return int(d / 60) "m"
      if (d < 86400) return int(d / 3600) "h"
      return int(d / 86400) "d"
    }
    # Columns first, the title last: fzf truncates the title, not the columns
    function text(i,   k, glyph, gcol, tcol, proj, t, subs) {
      k = kls[i]
      if (k == "blocked") { glyph = "!"; gcol = red; tcol = fg }
      else if (k == "failed") { glyph = "✗"; gcol = red; tcol = fg }
      else if (k == "ready") { glyph = "●"; gcol = amber; tcol = fg }
      else if (k == "working") { glyph = "◌"; gcol = dim; tcol = dim }
      else { glyph = " "; gcol = dim; tcol = dim }
      proj = base(path[i])
      t = strip(title[i])
      if (t == "") t = proj
      # awk counts bytes here: cut only pure ASCII, never inside a multibyte name
      if (length(proj) > 14 && proj !~ /[^ -~]/) proj = substr(proj, 1, 14)
      subs = ""
      if (agents[i] ~ /^[0-9]+$/ && agents[i] + 0 > 0) subs = " +" (agents[i] + 0)
      return c(gcol, glyph) " " c(tcol, sprintf("%3s", age(since[i])) " " tg[i] " " sprintf("%-14s", proj) " " t subs)
    }
    function add(f1, f2, f3, f4) {
      total++
      r1[total] = f1; r2[total] = f2; r3[total] = f3; r4[total] = f4
      selectable[total] = (f1 != "")
    }
    function agent(i) { add(sid[i], pid[i], kls[i], text(i)) }
    function plain(s) { add("", "", "", c(dim, s)) }
    $4 == "" { next }
    {
      n++
      sid[n] = $1; pid[n] = $2; kls[n] = $4; tg[n] = $6; since[n] = $7
      title[n] = $8; path[n] = $9; agents[n] = $10
      cnt[$4]++
    }
    END {
      needs = cnt["blocked"] + cnt["failed"] + cnt["ready"]
      plain("needs you " needs)
      for (i = 1; i <= n; i++) if (kls[i] == "blocked" || kls[i] == "failed" || kls[i] == "ready") agent(i)
      if (needs == 0) plain("nothing to open")
      plain("working " (cnt["working"] + 0))
      for (i = 1; i <= n; i++) if (kls[i] == "working") agent(i)
      if (cnt["seen"] > 0) {
        plain((show == 1 ? "hide seen " : "show seen ") cnt["seen"])
        if (show == 1) for (i = 1; i <= n; i++) if (kls[i] == "seen") agent(i)
      }
      # Non-selectable rows carry the nearest selectable rows above and below
      last = 0
      for (r = 1; r <= total; r++) { above[r] = last; if (selectable[r]) last = r }
      last = 0
      for (r = total; r >= 1; r--) { below[r] = last; if (selectable[r]) last = r }
      for (r = 1; r <= total; r++) {
        if (selectable[r]) { printf "%s\t%s\t%s\t%s\n", r1[r], r2[r], r3[r], r4[r]; continue }
        u = above[r]; d = below[r]
        if (!u) u = d
        if (!d) d = u
        if (!u) u = d = r
        printf "\t\t%d:%d\t%s\n", u, d, r4[r]
      }
    }'
}

# Counters for the status bar, and the @agent_mark of every window: a blocked
# or failed pane wins over a ready one. A write redraws the bar, so a mark is
# written only when it changes.
status() {
  local now op a b
  now=$(date +%s)
  {
    panes "$now" 1
    echo windows
    tmux list-windows -a -F "$(printf '#{window_id}\t#{@agent_mark}')"
  } | LC_ALL=C awk -F '\t' '
    BEGIN {
      alert = " #[fg=#F07178]!"; accent = " #[fg=#E6B450]●"
    }
    function sync(w,   v) {
      v = (w in hot) ? alert : ((w in warm) ? accent : "")
      if (v == cur[w]) return
      if (v == "") print "unset" FS w
      else print "set" FS w FS v
    }
    $0 == "windows" { inwin = 1; next }
    NF == 0 { next }
    !inwin {
      if ($5 == "1") print "clear" FS $2
      if ($4 == "") next
      if ($4 == "blocked" || $4 == "failed") { n1++; hot[$3] = 1 }
      else if ($4 == "ready") { n2++; warm[$3] = 1 }
      else if ($4 == "working") n3++
      if (!($3 in known)) { known[$3] = 1; order[++no] = $3 }
      next
    }
    {
      cur[$1] = $2
      if (!($1 in known)) { known[$1] = 1; order[++no] = $1 }
    }
    END {
      for (i = 1; i <= no; i++) sync(order[i])
      seg = ""
      if (n1 > 0) seg = "#[fg=#F07178,bold]! " n1 "#[nobold]"
      if (n2 > 0) seg = seg (seg == "" ? "" : "  ") "#[fg=#E6B450,bold]● " n2 "#[nobold]"
      if (n3 > 0) seg = seg (seg == "" ? "" : "  ") "#[fg=#7A8290]◌ " n3
      if (seg != "") print "out" FS seg
    }' |
    while IFS=$'\t' read -r op a b; do
      case "$op" in
        clear) seen "$a" </dev/null ;;
        set) tmux set -w -t "$a" @agent_mark "$b" </dev/null ;;
        unset) tmux set -wu -t "$a" @agent_mark </dev/null ;;
        out) printf '%s\n' "$a" ;;
      esac
    done
}

# The result was opened (or is in front of you): drop the unread marks
seen() {
  case "${1:-}" in
    %*) tmux set -pu -t "$1" @agent_unseen \; set -pu -t "$1" @agent_failed ;;
  esac
}

open_target() {
  [ -n "${2:-}" ] || return 0
  seen "$2"
  tmux select-window -t "$2" \; select-pane -t "$2" \; switch-client -t "$1"
}

toggle_seen() {
  [ -n "${AGENT_INBOX_STATE:-}" ] || return 0
  if [ -e "$AGENT_INBOX_STATE/show-seen" ]; then rm -f "$AGENT_INBOX_STATE/show-seen"
  else : >"$AGENT_INBOX_STATE/show-seen"; fi
}

# Never rest on a header or filler: jump to the row above or below it
skip_row() {
  [ -z "${1:-}" ] || return 0
  case "${2:-}" in *:*) ;; *) return 0 ;; esac
  local up=${2%%:*} down=${2#*:} pos=${FZF_POS:-0}
  case "${FZF_ACTION:-}" in
    *up*) echo "pos($up)" ;;
    *click*) if [ $((pos - up)) -le $((down - pos)) ]; then echo "pos($up)"; else echo "pos($down)"; fi ;;
    *) echo "pos($down)" ;;
  esac
}

# every(2) and resize: reload only when the list changed, never tracked
tick() {
  [ -n "${AGENT_INBOX_STATE:-}" ] || return 0
  local next="$AGENT_INBOX_STATE/next"
  render >"$next" 2>/dev/null || return 0
  [ -s "$next" ] || return 0
  cmp -s "$next" "$AGENT_INBOX_STATE/shown" && return 0
  mv "$next" "$AGENT_INBOX_STATE/shown"
  # single quotes: $AGENT_INBOX_STATE expands in fzf's child shell
  echo 'reload-sync(cat "$AGENT_INBOX_STATE/shown")'
}

# $1 pane, $2 class: label, location, blank line, then the final text of a
# finished turn or the tail of the screen
preview() {
  [ -n "${1:-}" ] || return 0
  local pane=$1 class=${2:-} label rgb report
  case "$class" in
    blocked) label='needs your answer'; rgb='240;113;120' ;;
    failed) label=failed; rgb='240;113;120' ;;
    ready) label=done; rgb='230;180;80' ;;
    working) label=working; rgb='122;130;144' ;;
    seen) label=seen; rgb='122;130;144' ;;
    *) label=$class; rgb='122;130;144' ;;
  esac
  printf '\033[38;2;%sm%s\033[0m\n' "$rgb" "$label"
  printf '\033[38;2;122;130;144m%s\033[0m\n\n' \
    "$(tmux display-message -p -t "$pane" '#{session_name}:#{window_index}.#{pane_index}  #{pane_current_path}')"
  case "$class" in
    failed | ready | seen)
      report=$(tmux display-message -p -t "$pane" '#{@agent_report}')
      case "$report" in
        */../* | */..) report= ;;
        "$reports"/*) ;;
        *) report= ;;
      esac
      if [ -n "$report" ] && [ -f "$report" ] && [ -r "$report" ]; then
        cat -- "$report"
        return 0
      fi ;;
  esac
  # Trailing blank rows go first: in a tall pane with short content the last 40
  # rows would all be blank
  tmux capture-pane -ep -t "$pane" |
    LC_ALL=C awk '{ l[NR] = $0; s = $0; gsub(/\033\[[0-9;:]*[A-Za-z]/, "", s); if (s ~ /[^ \t]/) last = NR }
      END { for (i = 1; i <= last; i++) print l[i] }' |
    tail -n 40
}

main() {
  local rc
  AGENT_INBOX_STATE=$(mktemp -d) || exit 1
  export AGENT_INBOX_STATE
  trap 'rm -rf "$AGENT_INBOX_STATE"' EXIT
  [ ! -d "$reports" ] || find "$reports" -type f -name '*.txt' -mtime +7 -delete 2>/dev/null
  render >"$AGENT_INBOX_STATE/shown"
  fzf --ansi --delimiter '\t' --with-nth 4.. --layout reverse --no-sort \
    --info inline-right --prompt '> ' \
    --color 'bg:#0B0E14,bg+:#122133,fg:#BFBDB6,fg+:#E6E1CF,hl:#E6B450,hl+:#E6B450' \
    --color 'border:#475266,label:#E6B450,prompt:#59C2FF,pointer:#E6B450,query:#BFBDB6' \
    --color 'info:#565B66,footer:#565B66,ghost:#475266,spinner:#95E6CB' \
    --color 'scrollbar:#475266,gutter:#0B0E14,preview-bg:#0B0E14' \
    --footer 'enter open   ctrl-x seen   tab seen list   esc close' \
    --preview "$self preview {2} {3}" \
    --preview-window 'right,55%,wrap,<55(down,45%,wrap)' \
    --bind 'load:unbind(load)+pos(2)' \
    --bind "every(2):transform($self tick)" \
    --bind "resize:transform($self tick)" \
    --bind "focus:transform($self skip {1} {3})" \
    --bind "enter:become($self open {1} {2})" \
    --bind "ctrl-x:execute-silent($self seen {2})+transform($self tick)" \
    --bind "tab:execute-silent($self toggle-seen)+transform($self tick)" \
    <"$AGENT_INBOX_STATE/shown"
  rc=$?
  # fzf exits 130 on esc: closing the popup is not an error
  [ "$rc" -ne 130 ] || rc=0
  exit "$rc"
}

case "${1:-}" in
  --supported) exec "$(dirname "$self")/session-picker.sh" --supported ;;
  render) render ;;
  status) status ;;
  seen) seen "${2:-}" ;;
  open) open_target "${2:-}" "${3:-}" ;;
  toggle-seen) toggle_seen ;;
  skip) skip_row "${2:-}" "${3:-}" ;;
  tick) tick ;;
  preview) preview "${2:-}" "${3:-}" ;;
  *) main ;;
esac
