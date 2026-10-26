#!/bin/bash
# PostToolUse(Write|Edit|Bash): nag when an em dash lands in content I just authored.
# For Write/Edit it looks only at lines the edit actually adds: legacy em dashes already
# in the file, or carried along inside an Edit anchor (old_string), do not fire it.
# For Bash it looks only at heredoc bodies, because bypass-permissions sessions author
# files with `cat > f <<'EOF'` and would otherwise skip this guard entirely.
# The dash is built with an octal escape so this file itself stays ASCII.
set -u
EM=$(printf '\342\200\224')
payload=$(cat)

nag() {
    printf 'Em dash (%s) written to %s. Style rule: no em dash anywhere. Fix it now with a colon, comma, parentheses or a rewrite.\n' "$EM" "$1" >&2
    exit 2
}

# Drop lines where the dash sits inside a search/replace pattern: those are the fix
# (or a doc telling someone to run the fix), not authored prose.
strip_tooling() {
    grep -Fv -e 'replace(' -e 're.sub' -e 'sed ' -e 'sed -' -e "tr '" -e 'grep' -e 's/' || true
}

if [ "$(printf '%s' "$payload" | jq -r '.tool_name // ""')" = "Bash" ]; then
    body=$(printf '%s' "$payload" | jq -r '.tool_input.command // ""' \
        | awk 'seen { print } /<</ { seen = 1 }' | strip_tooling)
    case "$body" in
        *"$EM"*) nag "a file written by a Bash heredoc" ;;
    esac
    exit 0
fi

new=$(printf '%s' "$payload" | jq -r '
  [.tool_input.new_string?, .tool_input.content?, (.tool_input.edits[]?.new_string?)]
  | map(select(type == "string")) | join("\n")' 2>/dev/null) || exit 0
old=$(printf '%s' "$payload" | jq -r '
  [.tool_input.old_string?, (.tool_input.edits[]?.old_string?)]
  | map(select(type == "string")) | join("\n")' 2>/dev/null)
if [ -n "$old" ]; then
    text=$(printf '%s\n' "$new" | grep -Fxv -f <(printf '%s\n' "$old") || true)
else
    text=$new
fi
text=$(printf '%s\n' "$text" | strip_tooling)
case "$text" in
    *"$EM"*)
        path=$(printf '%s' "$payload" | jq -r '.tool_input.file_path // "the file"' 2>/dev/null)
        nag "$path"
        ;;
esac
exit 0
