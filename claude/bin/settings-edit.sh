#!/bin/bash
# Safe in-place edit of a JSON settings file.
# usage: settings-edit.sh <file.json> '<jq filter>'
# Backs up to ~/.claude/backups/, applies the filter, validates, prints the
# resulting diff, and restores the backup if the result is not valid JSON.
set -u
file="${1:-}"; filter="${2:-}"
if [ -z "$file" ] || [ -z "$filter" ]; then
    echo "usage: settings-edit.sh <file.json> '<jq filter>'" >&2; exit 64
fi
[ -f "$file" ] || { echo "no such file: $file" >&2; exit 66; }
jq empty "$file" || { echo "target is not valid JSON, refusing" >&2; exit 65; }

mkdir -p ~/.claude/backups
backup=~/.claude/backups/"$(basename "$file").bak.$(date +%Y%m%d-%H%M%S)"
cp -p "$file" "$backup"

tmp="$(mktemp)"
if ! jq "$filter" "$file" > "$tmp"; then
    rm -f "$tmp"; echo "jq filter failed, file untouched" >&2; exit 1
fi
# Write through: settings.json may be a link into ~/dotfiles, and mv would replace the link
cat "$tmp" > "$file" && rm -f "$tmp"

if ! jq empty "$file" 2>/dev/null; then
    cp -p "$backup" "$file"
    echo "result was not valid JSON, restored $backup" >&2; exit 1
fi

echo "backup: $backup"
diff <(jq -S . "$backup") <(jq -S . "$file") && echo "no change"
exit 0
