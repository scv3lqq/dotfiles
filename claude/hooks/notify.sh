#!/bin/bash
# macOS notification for assistant Stop hooks.
# Stays silent when the originating tmux pane is already on screen.
# Never writes to stdout and always exits 0 so it cannot disturb the session.

set -u

# Linux servers have no desktop to notify; install.sh wires the hook on macOS only.
[ "$(uname -s)" = "Darwin" ] || exit 0

GHOSTTY_BUNDLE_ID="com.mitchellh.ghostty"
SELF="${BASH_SOURCE[0]}"
case "$SELF" in /*) ;; *) SELF="$PWD/$SELF" ;; esac

# Click handler: bring Ghostty forward and jump back to the pane that fired.
if [ "${1:-}" = "--focus" ]; then
    open -b "$GHOSTTY_BUNDLE_ID" >/dev/null 2>&1
    pane="${2:-}"
    if [ -n "$pane" ] && command -v tmux >/dev/null 2>&1; then
        sess=$(tmux display-message -p -t "$pane" '#{session_name}' 2>/dev/null)
        if [ -n "$sess" ]; then
            tmux list-clients -F '#{client_name}' 2>/dev/null | while read -r client; do
                tmux switch-client -c "$client" -t "$sess" >/dev/null 2>&1
            done
        fi
        tmux select-window -t "$pane" >/dev/null 2>&1
        tmux select-pane -t "$pane" >/dev/null 2>&1
    fi
    exit 0
fi

# Keep the invocation path: resolving the shared symlink loses client identity.
agent=claude
case "$SELF" in */.codex/hooks/*) agent=codex ;; esac
if [ "${1:-}" = "--agent" ]; then agent="${2:-}"; fi
case "$agent" in
    codex) title="Codex: готово"; group_prefix=codex ;;
    claude) title="Claude Code: готово"; group_prefix=claude-code ;;
    *) exit 0 ;;
esac

[ "${CLAUDE_NOTIFY_DEBUG:-0}" = "1" ] || exec 2>/dev/null
exec >/dev/null

payload=$(cat)

read_field() {
    local key="$1"
    if command -v jq >/dev/null 2>&1; then
        printf '%s' "$payload" | jq -r --arg k "$key" '.[$k] // empty' 2>/dev/null
    else
        printf '%s' "$payload" | python3 -c '
import json, sys
try:
    print(json.load(sys.stdin).get(sys.argv[1], "") or "")
except Exception:
    pass
' "$key" 2>/dev/null
    fi
}

event=$(read_field hook_event_name)
message=$(read_field message)
cwd=$(read_field cwd)
transcript=$(read_field transcript_path)

# Headless runs (claude -p, SDK) inherit TMUX_PANE but nobody is waiting on them.
if [ "$agent" = claude ]; then
    [ "${CLAUDE_CODE_ENTRYPOINT:-cli}" = "cli" ] || exit 0
fi

# A turn that ends while background agents, workflows or shells are still running
# is not the end of the work: their task-notification will start another turn.
has_pending_tasks() {
    [ -n "$transcript" ] && [ -f "$transcript" ] || return 1
    python3 - "$transcript" <<'PY'
import json, re, sys

launched, finished, workflows = set(), set(), set()
prefixes = ("Async agent launched", "Command running in background")
with open(sys.argv[1], encoding="utf-8") as fh:
    for line in fh:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("type") == "queue-operation":
            finished.update(re.findall(r"<tool-use-id>([^<]+)</tool-use-id>", rec.get("content") or ""))
            continue
        content = (rec.get("message") or {}).get("content")
        if isinstance(content, str):
            if "<task-notification>" in content:
                finished.update(re.findall(r"<tool-use-id>([^<]+)</tool-use-id>", content))
            elif rec.get("type") == "user" and not rec.get("isMeta"):
                # A new human prompt: a task that never reported back (killed, lost)
                # must not silence the rest of the session.
                launched.clear()
            continue
        for block in content or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                finished.update(re.findall(r"<tool-use-id>([^<]+)</tool-use-id>", block.get("text", "")))
            elif block.get("type") == "tool_use" and block.get("name") == "Workflow":
                workflows.add(block.get("id"))
            elif block.get("type") == "tool_result":
                body = block.get("content")
                if isinstance(body, list):
                    body = " ".join(b.get("text", "") for b in body if isinstance(b, dict))
                tid = block.get("tool_use_id")
                if tid in workflows and not block.get("is_error"):
                    launched.add(tid)
                elif (body or "").lstrip().startswith(prefixes):
                    launched.add(tid)
sys.exit(0 if launched - finished else 1)
PY
}

[ "$agent" = claude ] && [ "$event" = "Stop" ] && has_pending_tasks && exit 0
[ -n "$cwd" ] || cwd="$PWD"

project=$(basename "$cwd")
context="$project"
pane="${TMUX_PANE:-}"
in_tmux=0
if [ -n "${TMUX:-}" ] && [ -n "$pane" ] && command -v tmux >/dev/null 2>&1; then
    in_tmux=1
    where=$(tmux display-message -p -t "$pane" '#{session_name}:#{window_index}' 2>/dev/null)
    [ -n "$where" ] && context="$project · $where"
fi

frontmost_bundle_id() {
    local asn
    asn=$(lsappinfo front 2>/dev/null) || return 1
    [ -n "$asn" ] || return 1
    lsappinfo info -only bundleid "$asn" 2>/dev/null |
        sed -n 's/.*"CFBundleIdentifier"="\([^"]*\)".*/\1/p'
}

# True only when we can positively prove the pane is already in view.
pane_is_visible() {
    [ "$(frontmost_bundle_id)" = "$GHOSTTY_BUNDLE_ID" ] || return 1
    [ "$in_tmux" = "1" ] || return 0
    local state
    state=$(tmux display-message -p -t "$pane" \
        '#{pane_active} #{window_active} #{session_attached}' 2>/dev/null) || return 1
    case "$state" in
        "1 1 0"|"") return 1 ;;
        "1 1 "*) return 0 ;;
        *) return 1 ;;
    esac
}

if [ "${CLAUDE_NOTIFY_FORCE:-0}" != "1" ] && pane_is_visible; then
    exit 0
fi

# Only end-of-turn is worth an alert; Notification events are noise.
[ "$event" = "Notification" ] && exit 0

body="${message:-Ответ готов}"
sound="Glass"

if command -v terminal-notifier >/dev/null 2>&1; then
    args=(-title "$title" -subtitle "$context" -message "$body"
          -sound "$sound" -group "${group_prefix}-${pane:-nopane}")
    if [ "$in_tmux" = "1" ]; then
        args+=(-execute "$(printf '%q %q %q' "$SELF" --focus "$pane")")
    else
        args+=(-activate "$GHOSTTY_BUNDLE_ID")
    fi
    # Exit 3 means macOS denied notification permission: fall back to osascript.
    terminal-notifier "${args[@]}" && exit 0
fi

esc() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }
osascript -e "display notification \"$(esc "$body")\" with title \"$(esc "$title")\" subtitle \"$(esc "$context")\" sound name \"$sound\""
exit 0
