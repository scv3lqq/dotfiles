#!/bin/bash
# Claude Code hook: mirrors the turn state of the session in this tmux pane into
# pane options for the `prefix + s` picker (tmux/session-picker.sh):
#   @claude_state       working (mid-turn), waiting (mid-turn, blocked on the
#                       user: permission prompt or question) or agents (turn
#                       over, background subagents or workflows still running);
#                       unset when idle
#   @claude_since       epoch seconds when the turn started
#   @claude_wait_agent  agent whose prompt is pending ("main" or a subagent id)
# Esc and a denied prompt end the turn without any hook event; the picker drops
# such a stale "working" by window activity. Never writes to stdout
# (UserPromptSubmit stdout reaches the model) and always exits 0.

set -u

[ -n "${TMUX_PANE:-}" ] || exit 0
# Headless runs (claude -p, SDK) inherit TMUX_PANE from the session around them
[ "${CLAUDE_CODE_ENTRYPOINT:-cli}" = "cli" ] || exit 0
command -v jq >/dev/null 2>&1 && command -v tmux >/dev/null 2>&1 || exit 0
exec >/dev/null 2>&1

pane=$TMUX_PANE
# Background shells and monitors outlive any work (dev servers), so only
# subagents and workflows keep a finished turn listed
fields=$(jq -r '.hook_event_name // "", .notification_type // .tool_name // "", .agent_id // "",
  ([.background_tasks[]? | select(.type == "subagent" or .type == "workflow")] | length)') || exit 0
{ read -r event; read -r kind; read -r agent; read -r bg; } <<EOF
$fields
EOF
me=${agent:-main}
state=$(tmux display -p -t "$pane" '#{@claude_state}:#{@claude_wait_agent}') || exit 0
cur=${state%%:*}
waiter=${state#*:}

clear_state() {
  tmux set -pu -t "$pane" @claude_state \; set -pu -t "$pane" @claude_since \; \
    set -pu -t "$pane" @claude_wait_agent
}

# Waiting keeps the turn's start time; only a new turn starts the clock
wait_on_user() {
  [ -n "$cur" ] || tmux set -p -t "$pane" @claude_since "$(date +%s)"
  tmux set -p -t "$pane" @claude_state waiting \; set -p -t "$pane" @claude_wait_agent "$me"
}

case "$event" in
  UserPromptSubmit)
    tmux set -p -t "$pane" @claude_state working \; set -p -t "$pane" @claude_since "$(date +%s)" \; \
      set -pu -t "$pane" @claude_wait_agent ;;
  PermissionRequest) wait_on_user ;;
  PreToolUse)
    if [ "$kind" = AskUserQuestion ]; then
      wait_on_user
    # A main-agent tool call while idle or only background agents run: a turn
    # that began without a prompt
    elif [ -z "$agent" ] && { [ -z "$cur" ] || [ "$cur" = agents ]; }; then
      tmux set -p -t "$pane" @claude_state working \; set -p -t "$pane" @claude_since "$(date +%s)"
    fi ;;
  PostToolUse | PostToolUseFailure)
    # Another agent's tool finishing does not answer the pending prompt
    if [ "$cur" = waiting ] && [ "$me" = "${waiter:-main}" ]; then
      tmux set -p -t "$pane" @claude_state working \; set -pu -t "$pane" @claude_wait_agent
    fi ;;
  Notification)
    case "$kind" in
      idle_prompt) clear_state ;;
      permission_prompt | elicitation_dialog)
        [ "$cur" != working ] || tmux set -p -t "$pane" @claude_state waiting ;;
    esac ;;
  Stop)
    # Every hand-back or kill of a background agent starts a turn whose Stop
    # reports the agents still in flight
    if [ "${bg:-0}" -gt 0 ]; then
      [ -n "$cur" ] || tmux set -p -t "$pane" @claude_since "$(date +%s)"
      tmux set -p -t "$pane" @claude_state agents \; set -pu -t "$pane" @claude_wait_agent
    else
      clear_state
    fi ;;
  StopFailure | SessionStart | SessionEnd) clear_state ;;
esac
exit 0
