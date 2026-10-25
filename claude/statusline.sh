#!/bin/bash
# Claude Code status line: reads the session JSON on stdin, prints one row.
# Always exits 0: a non-zero exit or empty output blanks the row.

command -v jq >/dev/null || exit 0

G=$'\033[38;5;240m'
Y=$'\033[33m'
R=$'\033[31m'
RST=$'\033[0m'

filter='
(.workspace.current_dir // .cwd // ""),
(.workspace.git_worktree // .worktree.name // ""),
(.agent.name // ""),
(((.model.id // "") | capture("claude-(?<f>[a-z]+)-(?<maj>[0-9]+)(-(?<min>[0-9]{1,2})(?![0-9]))?") // null) as $m
  | if $m then $m.f + " " + $m.maj + (if ($m.min // "") != "" then "." + $m.min else "" end)
    else (.model.display_name // "" | ascii_downcase) end),
(.effort.level // ""),
(.context_window.used_percentage // 0 | floor),
(.rate_limits.five_hour.used_percentage // -1 | floor),
(.rate_limits.seven_day.used_percentage // -1 | floor)
'

{ IFS= read -r cwd; IFS= read -r wt; IFS= read -r agent; IFS= read -r model; IFS= read -r effort; IFS= read -r ctx; IFS= read -r h5; IFS= read -r d7; } < <(jq -r "$filter" 2>/dev/null)

# Empty ctx means jq failed on invalid input: print nothing.
[ -n "$ctx" ] || exit 0

out=""

add() {
  if [ -n "$out" ]; then out="$out · $1"; else out="$1"; fi
}

# Sets REPLY to the text, wrapped in yellow or red when val reaches a threshold.
tint() {
  local val=$1 yt=$2 rt=$3 text=$4
  if [ "$val" -ge "$rt" ]; then
    REPLY="$R$text$G"
  elif [ "$val" -ge "$yt" ]; then
    REPLY="$Y$text$G"
  else
    REPLY="$text"
  fi
}

# 1. Location
if [ "$cwd" = "$HOME" ]; then
  dir="~"
else
  dir="${cwd##*/}"
  [ -n "$dir" ] || dir="/"
fi

branch=""
if [ -d "$cwd" ]; then
  branch=$(git -C "$cwd" symbolic-ref --short -q HEAD 2>/dev/null)
  [ -n "$branch" ] || branch=$(git -C "$cwd" rev-parse --short HEAD 2>/dev/null)
fi
if [ "${#branch}" -gt 32 ]; then
  branch="${branch:0:31}…"
fi

loc="$dir"
[ -n "$branch" ] && loc="$loc  $branch"
[ -n "$wt" ] && loc="$loc ⎇ $wt"
add "$loc"

# 2. Agent
[ -n "$agent" ] && add "$agent"

# 3. Model and effort
me="$model"
if [ -n "$effort" ]; then
  if [ -n "$me" ]; then me="$me $effort"; else me="$effort"; fi
fi
[ -n "$me" ] && add "$me"

# 4. Context
tint "$ctx" 60 80 "${ctx}%"
add "$REPLY"

# 5-6. Rate limits, shown only near the cap
if [ "$h5" -ge 80 ]; then
  tint "$h5" 80 95 "5h ${h5}%"
  add "$REPLY"
fi
if [ "$d7" -ge 80 ]; then
  tint "$d7" 80 95 "7d ${d7}%"
  add "$REPLY"
fi

printf '%s%s%s\n' "$G" "$out" "$RST"
exit 0
