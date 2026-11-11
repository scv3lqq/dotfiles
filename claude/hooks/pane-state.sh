#!/bin/bash
# Claude Code hook: mirrors the turn state of the session in this tmux pane into
# pane options for the `prefix + s` picker (tmux/session-picker.sh):
#   @claude_state       working (mid-turn), waiting (blocked on the user:
#                       permission prompt or question), agents (turn over,
#                       background subagents or workflows still running) or
#                       done (turn over, nothing of it running); unset when
#                       the session starts, is cleared or exits
#   @claude_since       epoch seconds when the turn started; for done, when it
#                       ended
#   @claude_wait_agent  agent whose prompt is pending ("main" or a subagent id)
#   @claude_wait_from   state before that prompt ("none" when unset)
#   @claude_agents      subagents and workflows in flight at the last Stop
#   @agent_unseen       1 when a finished turn's result was not opened yet
#   @agent_failed       1 when that turn ended in StopFailure
#   @agent_report       path of its final text; the three feed tmux/agent-inbox.sh
# Esc and a denied prompt end the turn without any hook event, idle_prompt
# included; the picker drops such a stale "working" by window activity and
# never lists it as finished. Never writes to stdout (UserPromptSubmit stdout
# reaches the model) and always exits 0.

set -u

[ -n "${TMUX_PANE:-}" ] || exit 0
# Codex calls this file through its own link: a pane started from Claude
# Desktop hands Codex its CLAUDE_* env, which says nothing about Codex
case "${BASH_SOURCE[0]:-}" in
  */.codex/hooks/*) ;;
  # Headless runs (claude -p, SDK) inherit TMUX_PANE from the session around them
  *) [ "${CLAUDE_CODE_ENTRYPOINT:-cli}" = "cli" ] || exit 0 ;;
esac
command -v jq >/dev/null 2>&1 && command -v tmux >/dev/null 2>&1 || exit 0
exec >/dev/null 2>&1

pane=$TMUX_PANE
# The shared Codex app-server daemon keeps the TMUX_PANE of the pane that
# started it: only a process below the pane's own process speaks for it
origin=$(tmux display -p -t "$pane" '#{pane_pid}') || exit 0
case "$origin" in '' | *[!0-9]*) exit 0 ;; esac
[ "$origin" -gt 1 ] || exit 0
pid=$PPID
steps=0
while [ "$pid" != "$origin" ]; do
  [ "$pid" -gt 1 ] && [ "$steps" -lt 64 ] || exit 0
  pid=$(ps -o ppid= -p "$pid") || exit 0
  pid=${pid//[[:space:]]/}
  case "$pid" in '' | *[!0-9]*) exit 0 ;; esac
  steps=$((steps + 1))
done
now=$(date +%s)
payload=$(cat) || exit 0
# kind: notification type, tool name, SessionStart source or SessionEnd reason.
# Background shells and monitors outlive any work (dev servers), so only
# subagents and workflows keep a finished turn listed
fields=$(printf '%s' "$payload" | jq -r '.hook_event_name // "", .notification_type // .tool_name // .source // .reason // "", .agent_id // "",
  ([.background_tasks[]? | select(.type == "subagent" or .type == "workflow")] | length)') || exit 0
{ read -r event; read -r kind; read -r agent; read -r bg; } <<EOF
$fields
EOF
me=${agent:-main}
state=$(tmux display -p -t "$pane" '#{@claude_state}:#{@claude_wait_agent}:#{@claude_wait_from}:#{@claude_agents}') || exit 0
IFS=: read -r cur waiter from inflight <<EOF
$state
EOF
# A turn or its background agents still run
case "$cur" in working | waiting | agents) active=1 ;; *) active= ;; esac

clear_state() {
  tmux set -pu -t "$pane" @claude_state \; set -pu -t "$pane" @claude_since \; \
    set -pu -t "$pane" @claude_wait_agent \; set -pu -t "$pane" @claude_wait_from \; \
    set -pu -t "$pane" @claude_agents
  clear_result
  old=$(tmux display -p -t "$pane" '#{@agent_report}')
  [ -z "$old" ] || rm -f "$old"
  tmux set -pu -t "$pane" @agent_report
}

# Turn over and nothing of it runs: the picker lists it as finished since $1
finish() {
  tmux set -p -t "$pane" @claude_state done \; set -p -t "$pane" @claude_since "$1" \; \
    set -pu -t "$pane" @claude_wait_agent \; set -pu -t "$pane" @claude_wait_from \; \
    set -pu -t "$pane" @claude_agents
}

# Turn over while $1 background agents run; the clock keeps the turn's start
await_agents() {
  [ -n "$active" ] || tmux set -p -t "$pane" @claude_since "$now"
  tmux set -p -t "$pane" @claude_state agents \; set -p -t "$pane" @claude_agents "$1" \; \
    set -pu -t "$pane" @claude_wait_agent \; set -pu -t "$pane" @claude_wait_from
}

# Waiting keeps the turn's start time; only a new turn starts the clock. The
# state before the first pending prompt comes back once it is answered
wait_on_user() {
  [ -n "$active" ] || tmux set -p -t "$pane" @claude_since "$now"
  [ "$cur" = waiting ] || tmux set -p -t "$pane" @claude_wait_from "${cur:-none}"
  tmux set -p -t "$pane" @claude_state waiting \; set -p -t "$pane" @claude_wait_agent "$me"
}

clear_result() {
  tmux set -pu -t "$pane" @agent_unseen \; set -pu -t "$pane" @agent_failed
}

# The turn's final text for tmux/agent-inbox.sh. Unseen unless the pane is in
# front of an attached client. $1: 1 when the turn failed
record_result() {
  local dir=${XDG_STATE_HOME:-$HOME/.local/state}/agent-inbox
  local file old
  old=$(tmux display -p -t "$pane" '#{@agent_report}')
  umask 077
  if mkdir -p "$dir"; then
    file="$dir/${pane#%}-$now.txt"
    printf '%s' "$payload" |
      jq -j '[(.error // empty | tostring), (.last_assistant_message // empty)] | join("\n\n")' |
      head -c 65536 >"$file"
    if [ -s "$file" ]; then
      tmux set -p -t "$pane" @agent_report "$file"
      [ -z "$old" ] || [ "$old" = "$file" ] || rm -f "$old"
    else
      rm -f "$file"
      [ -z "$old" ] || rm -f "$old"
      tmux set -pu -t "$pane" @agent_report
    fi
  fi
  if [ "${1:-}" = 1 ]; then tmux set -p -t "$pane" @agent_failed 1
  else tmux set -pu -t "$pane" @agent_failed; fi
  if [ "$(tmux display -p -t "$pane" '#{pane_active}#{window_active}#{?session_attached,1,0}')" = 111 ]; then
    tmux set -pu -t "$pane" @agent_unseen
  else
    tmux set -p -t "$pane" @agent_unseen 1
  fi
}

case "$event" in
  UserPromptSubmit)
    tmux set -p -t "$pane" @claude_state working \; set -p -t "$pane" @claude_since "$now" \; \
      set -pu -t "$pane" @claude_wait_agent \; set -pu -t "$pane" @claude_wait_from
    [ -n "$agent" ] || clear_result ;;
  PermissionRequest) wait_on_user ;;
  PreToolUse)
    if [ "$kind" = AskUserQuestion ]; then
      wait_on_user
    # A main-agent tool call while idle, finished or only background agents
    # run: a turn that began without a prompt
    elif [ -z "$agent" ] && [ "$cur" != working ] && [ "$cur" != waiting ]; then
      tmux set -p -t "$pane" @claude_state working \; set -p -t "$pane" @claude_since "$now"
    fi ;;
  PostToolUse | PostToolUseFailure)
    # Another agent's tool finishing does not answer the pending prompt. A
    # background agent answered after main's turn ended runs on as agents
    if [ "$cur" = waiting ] && [ "$me" = "${waiter:-main}" ]; then
      next=working
      if [ "$me" != main ]; then
        case "$from" in agents | done | none) next=agents ;; esac
      fi
      tmux set -p -t "$pane" @claude_state "$next" \; set -pu -t "$pane" @claude_wait_agent \; \
        set -pu -t "$pane" @claude_wait_from
    fi ;;
  Notification)
    case "$kind" in
      # Sent 60 s after main's turn ended, never while background agents run:
      # a turn or agents still claimed then are over
      idle_prompt) case "$cur" in working | agents) finish $((now - 60)) ;; esac ;;
      permission_prompt | elicitation_dialog)
        [ "$cur" != working ] || tmux set -p -t "$pane" @claude_state waiting ;;
    esac ;;
  Stop)
    # Every hand-back or kill of a background agent starts a turn whose Stop
    # reports the agents still in flight
    if [ "${bg:-0}" -gt 0 ]; then await_agents "$bg"
    else
      finish "$now"
      [ -n "$agent" ] || record_result
    fi ;;
  StopFailure)
    # Subagents and summary forks report their own API errors here (agent_id
    # set). Main's payload has no background_tasks: the last Stop's count stands in
    if [ -n "$agent" ]; then :
    elif [ "${inflight:-0}" -gt 0 ]; then await_agents "$inflight"
    else finish "$now"; record_result 1; fi ;;
  SessionStart | SessionEnd)
    case "$kind" in
      # Compaction, manual or automatic, is not a turn
      compact) ;;
      # Background agents outlive /clear and hand back into the new
      # conversation; a finished row goes with the old one
      clear) [ "$cur" = agents ] || clear_state ;;
      *) clear_state ;;
    esac ;;
esac
exit 0
