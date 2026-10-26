#!/bin/bash
# PostToolUse(Write|Edit|Bash): a skill or command must have a line in the Obsidian index note.
# Fires only when the written file is a SKILL.md or commands/<name>.md AND the note has no
# entry for that name, so editing an already-documented skill stays silent.
# Bash is matched too because bypass-permissions sessions author files with heredocs.
set -u
# The vault root is personal, so its path lives outside the repo
NOTE="$(cat "$HOME/.claude/private/vault" 2>/dev/null)/meta/claude-code/Claude Code Skills.md"
payload=$(cat)
[ -f "$NOTE" ] || exit 0

tool=$(printf '%s' "$payload" | jq -r '.tool_name // ""')
if [ "$tool" = "Bash" ]; then
    candidates=$(printf '%s' "$payload" | jq -r '.tool_input.command // ""' \
        | grep -oE "[^ \"'>]*(/skills/[^ \"']*/SKILL\.md|/commands/[^ \"']*\.md)" | sort -u)
else
    candidates=$(printf '%s' "$payload" | jq -r '.tool_input.file_path // ""')
fi
[ -n "$candidates" ] || exit 0

missing=""
while IFS= read -r path; do
    [ -n "$path" ] || continue
    case "$path" in
        */skills/synced/*|*/plugins/*) continue ;;
        */skills/*/SKILL.md) name=$(basename "$(dirname "$path")") ;;
        */commands/*.md) name=$(basename "$path" .md) ;;
        *) continue ;;
    esac
    # a glob (`skills/*/SKILL.md` in wc/cat/grep) names no skill
    case "$name" in *[\*\?\[]*|'$'*) continue ;; esac
    grep -qF -- "\`/$name" "$NOTE" || missing="$missing /$name"
done <<EOF
$candidates
EOF

[ -n "$missing" ] || exit 0

printf 'Not in the skills index yet:%s. Add one line per entry to %s, in that note s style: Russian, grouped by scope (personal / vault / built-in), a star after the name when Claude may trigger it itself (no disable-model-invocation).\n' "$missing" "$NOTE" >&2
exit 2
