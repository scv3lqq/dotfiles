#!/bin/zsh
# $1 prompt file, $2 session name, $3 permission mode
exec "$HOME/.local/bin/claude" --permission-mode "${3:-manual}" --name "$2" "$(<"$1")"
