# claude-picker-done

## Goal

The `prefix + s` picker's claude section also lists Claude panes whose turn
finished less than 10 minutes ago, below the active rows, newest end first,
with their own marker and the age since the end. A session with background
subagents or workflows stays listed as `agents` across a `StopFailure`, across
`/clear`, and after one of its agents' permission prompts is answered while
main's turn is over (the three known limitations of
`plans/claude-picker-bg-agents.md`).

## Current behavior

`claude/hooks/pane-state.sh` clears every pane option on `Stop` with no
counted background agents, on any `StopFailure`, `SessionStart`,
`SessionEnd` and `idle_prompt`, so a finished session leaves the picker at
once. An answered background agent prompt sets `working` even when main's turn
is over. `tmux/session-picker.sh` lists only busy panes
(`waiting`, or `working`/`agents` with window activity in the last 5 s).

## Spike findings (Claude Code 2.1.309, evidence in `$S/spike-a/` and `$S/spike-b/`, not committed)

Hook schemas (binary `~/.local/share/claude/versions/2.1.309`):

- `background_tasks` exists only on `Stop` and `SubagentStop`. `StopFailure`
  is `{error, error_details?, last_assistant_message?}` (5 payloads observed,
  none with the field). `SessionStart.source`: `startup`, `resume`, `clear`,
  `compact`, `fork`. `SessionEnd.reason`: `clear`, `resume`, `logout`,
  `prompt_input_exit`, `other`. Neither carries background work.
- The idle notification timer returns early while any background agent
  (`local_agent`, `remote_agent`, `in_process_teammate`, `local_workflow`, not
  terminal, not paused) exists.

Events:

- `StopFailure` also comes from subagents (`agent_id` + `agent_type`, instead
  of `SubagentStop`) and from agent summary forks (`agent_id`, no
  `agent_type`). The current hook clears the pane on each of them, even while
  main's agents run (spike-a E1: state cleared at +72.2 by a fork's
  StopFailure, agent ran on until +283.9).
- Main's `StopFailure` on the last agent's hand-back turn: `+284.1
  StopFailure`, then `idle_prompt` at `+344.1` (60.0 s later, no agents left).
  While an agent ran, no `idle_prompt` for 210 s after a main `StopFailure`.
- `idle_prompt` comes 60.0 to 60.9 s after the end of main's turn (`Stop`,
  `StopFailure`, `/clear`, end of `/compact`), never while background agents
  run (also not during a 108 s pending background agent dialog), never after
  Esc mid-turn or a denied main prompt (77 to 87 s observed, no event at all).
- `/clear` with an agent running: `SessionEnd reason=clear` (old session id),
  `SessionStart source=clear` (new id); neither reports the agent. The agent's
  running Bash is killed (exit 137); its loop survives, its hand-back
  (`UserPromptSubmit` + `Stop`) arrives under the new session id. `/clear`
  without agents: the same two events.
- `/compact`: `PreCompact`, a fork's `SubagentStop`, `SessionStart
  source=compact` (same session id), `PostCompact`; no turn events.
- Background agent permission prompt while main is idle: `PreToolUse(agent)`,
  `PermissionRequest(agent)`, `Notification permission_prompt` 6 s later
  (no `agent_id`); approve: `PostToolUse(agent)`; deny: only `PostToolBatch`
  (not wired), then the agent hands back on its own. Main's input box is
  replaced by the dialog (typed `/hel` had no effect), so `/clear` cannot run
  while such a dialog is pending.
- `AskUserQuestion` is not available to background subagents (three tries).
- Agent calls go to the background even with `run_in_background: false`
  (`backgroundLaunchByDefault`).
- Typing a draft without submitting moves `#{window_activity}` and fires no
  hook event.

## Design

`@claude_state` gets a fourth value `done`: main's turn is over and nothing of
it runs. `@claude_since` holds the end time for `done` (the turn's start for
the other states). Two hook-internal options: `@claude_wait_from` (state before
the first pending prompt, `none` when unset) and `@claude_agents` (the count of
background subagents and workflows in the last `Stop`).

Transitions (main = no `agent_id`):

| Event | New state |
| --- | --- |
| `UserPromptSubmit` | `working`, since now (unchanged) |
| `PreToolUse` main, state unset, `agents` or `done` | `working`, since now |
| `PermissionRequest`, `PreToolUse(AskUserQuestion)` | `waiting`; since now unless the state was `working`/`waiting`/`agents`; `@claude_wait_from` = previous state unless already `waiting` |
| `PostToolUse(Failure)` of the waiter | `agents` if the waiter is a subagent and `@claude_wait_from` is `agents`, `done` or `none`; else `working` |
| `Stop`, count > 0 | `agents`, count stored, since kept when the state was `working`/`waiting`/`agents` |
| `Stop`, count 0 or field missing | `done`, since now |
| `StopFailure` with `agent_id` | no change |
| `StopFailure` main | `agents` with the stored count when it is > 0, else `done` |
| `idle_prompt`, state `working` or `agents` | `done`, since now - 60 |
| `idle_prompt`, other states | no change |
| `permission_prompt`, `elicitation_dialog` | unchanged (`working` -> `waiting`) |
| `SessionStart source=compact` | no change |
| `SessionEnd`/`SessionStart` `clear`, state `agents` | no change |
| any other `SessionStart`/`SessionEnd` | all options unset |

Picker: a pane running Claude with state `done`, a numeric since and
`now - since < 600` gets a finished row: below the active rows, sorted by end
time descending, marker green U+F00C (check), name and window grey, age
`ago(since)` in the active rows' age column, title grey. The section (fillers
plus the rule) shows when there is at least one active or finished row.

Decisions:

- `/clear` drops a finished row: the user reset that pane's conversation, the
  finished output is gone from its screen, so the row would point at an empty
  conversation. With agents running, `/clear` keeps `agents` (they hand back
  into the new conversation; their hand-back turn's `Stop` recounts).
- Esc and a denied prompt do not count as finished, and the picker keeps its
  busy rule unchanged: no event marks such an end (no `idle_prompt` either,
  re-checked on 2.1.309), and `#{window_activity}` is window-wide and moves on
  typing and on sibling panes' output, so an end taken from it, and the 600 s
  window after it, would drift and bring old sessions back. The user ended
  that turn in that pane, so there is nothing to discover.
- tmux-resurrect restore: tmux-resurrect saves no user pane options, so
  restored panes start without them, and tmux-assistant-resurrect's
  `claude --resume` fires `SessionStart source=resume`, which unsets
  everything. Sessions finished before the restore are not listed; the next
  turn end lists them again. A picker on a server whose pane options predate
  the change shows `working`/`waiting`/`agents` exactly as before; `done`
  appears with each session's next `Stop`. A prompt pending under the old hook
  has no `@claude_wait_from`, so its answer gives `working`, the old behavior.
- `idle_prompt` is the one event that proves nothing runs: it converts a
  leftover `working` or `agents` into `done` 60 s back. It never touches
  `waiting` (no evidence about long pending main dialogs) and never creates
  a row from unset (after `/clear`).
- `/compact` (and auto-compact) is not a turn: `SessionStart source=compact`
  changes nothing, so a compaction neither drops a working pane nor a
  finished row.
- No new hook events: `PostToolBatch` would report a denied agent prompt but
  is not wired, see Known limitations. `install.sh` and
  `~/.claude/settings.json` stay unchanged.

## Workflow sections

### Shared definitions

- `S=/private/tmp/claude-501/-Users-me-dotfiles/86355d25-2161-4d7c-841d-28af616b9eae/scratchpad`
  (this session's scratchpad: test scripts, spikes; not in the repo).
- `O=/private/tmp/claude-501/-Users-me-dotfiles/cd429fbc-0e3f-470f-8ab5-6d3bae06538f/scratchpad`
  (previous session's scratchpad: the original suites; read only, never
  written).
- State literal `done` (lowercase, exact) in `@claude_state`; for `done`,
  `@claude_since` is the epoch second the turn ended. T1 writes it, T2 reads
  it. Other literals unchanged: `working`, `waiting`, `agents`.
- Hook-internal pane options (T1 only): `@claude_wait_from` (`working`,
  `agents`, `done` or `none`), `@claude_agents` (positive integer or unset).
- Finished-row window: listed while `now - @claude_since < 600`.
- Marker bytes in the picker's awk (octal escapes, ASCII in the source):
  finished `\357\200\214` (U+F00C), color `green` (`170;217;76`, the awk
  variable that already exists); unchanged: working `\357\204\220` (U+F110),
  waiting `\357\203\263` (U+F0F3), agents `\357\203\200` (U+F0C0).
- tmux sockets of the test scripts: `-L hooktest`, `-L hookbgtest`,
  `-L hookdonetest`, `-L pickerbgtest`, `-L pickerdonetest`, `-L fzfspike`
  (harness). Runs of one script must not overlap, so mutation runs go one
  after another.
- `$S/hook-test.sh`, `$S/hook-bg-test.sh`, `$S/picker-bg-test.sh` are copies
  of the `$O` files (already in place, identical to `$O`). T1 edits the first
  two exactly as listed in T1; `picker-bg-test.sh` stays identical.

### Gates

Run from `~/dotfiles`.

1. `for f in claude/hooks/pane-state.sh tmux/session-picker.sh; do bash -n "$f" && /bin/bash -n "$f" || echo "BAD $f"; done`
   prints nothing.
2. `git ls-files -s claude/hooks/pane-state.sh tmux/session-picker.sh | awk '{print $1}'`
   prints `100755` twice.
3. `for f in claude/hooks/pane-state.sh tmux/session-picker.sh README.md plans/claude-picker-done.md; do printf '%s:' "$f"; LC_ALL=C grep -F -c "$(printf '\342\200\224')" "$f"; done`
   prints `:0` for every file.
4. `bash $S/hook-test.sh | tail -1` prints `FAILS=0`.
5. `bash $S/hook-bg-test.sh | tail -1` prints `FAILS=0`.
6. `bash $S/hook-done-test.sh | tail -1` prints `FAILS=0`.
7. `bash $S/picker-bg-test.sh | tail -1` prints `FAILS=0`.
8. `bash $S/picker-done-test.sh | tail -1` prints `FAILS=0`.
9. `PICKER=$HOME/dotfiles/tmux/session-picker.sh bash $S/spike-fzf/harness.sh | tail -1`
   prints `FAILS=0` (the first picker's fzf harness, 69 PASS and 2 SKIP on
   main; takes a few minutes).

### Acceptance criteria

- AC1 (hook): Gates 4, 5, 6.
- AC2 (picker): Gates 7, 8, 9.
- AC3 (static): Gates 1-3; `grep -c '357\\200\\214' tmux/session-picker.sh`
  prints `1`; `LC_ALL=C grep -c "$(printf '\357\200\214')" tmux/session-picker.sh`
  prints `0`.
- AC4 (scope): `git diff --name-only main...HEAD` prints exactly
  `README.md`, `claude/hooks/pane-state.sh`, `plans/claude-picker-done.md`,
  `tmux/session-picker.sh`.
- AC5 (suites changed only as listed): `diff $O/hook-test.sh $S/hook-test.sh | grep '^[0-9]'`
  prints exactly `40,43c40,43`, `45,46c45,46`, `48c48`;
  `diff $O/hook-bg-test.sh $S/hook-bg-test.sh | grep '^[0-9]'` prints exactly
  `42,43c42,43`, `46c46`, `60c60`, `62,63c62,63`, `67,68c67,68`, `70,72c70,72`;
  every `>` line equals the new line T1 lists for that line number;
  `cmp $O/picker-bg-test.sh $S/picker-bg-test.sh` exits 0.
- AC6 (fenced blocks): `claude/hooks/pane-state.sh`, `$S/hook-done-test.sh`
  and `$S/picker-done-test.sh` equal their fenced blocks in this plan
  (extract the block, `diff` against the file: no output); the picker edits
  and the README substring are present as written.
- AC7 (README): `grep -F -c 'panes whose turn finished in the last 10 minutes below them' README.md`
  prints `1`.
- AC8 (live `agents`, run last by the validator, which runs as a background
  agent of the orchestrator's session after the orchestrator's turn ended):
  `tmux display -p -t "$TMUX_PANE" '#{@claude_state}'` prints `agents`, and
  `d=$(mktemp -d); : >"$d/expanded"; PICKER_STATE=$d PICKER_CURRENT=$(tmux display -p '#{session_id}') tmux/session-picker.sh list | LC_ALL=C awk -F '\t' -v p="$TMUX_PANE" -v g="$(printf '\357\203\200')" '$2 == p && index($0, g) { f = 1 } END { exit !f }'; echo $?`
  prints `0`.
- AC9 (live finished row, same run): poll the live server (until-loop, 20 s
  step, at most 600 s) until
  `tmux list-panes -a -F '#{pane_id}	#{pane_current_command}	#{@claude_state}	#{@claude_since}' | awk -F '\t' -v now="$(date +%s)" '($2 ~ /^[0-9]+\.[0-9]+\.[0-9]+$/ || $2 == "claude") && $3 == "done" && $4 ~ /^[0-9]+$/ && now - $4 < 570 { print $1; exit }'`
  prints a pane id `$n`; then
  `d=$(mktemp -d); : >"$d/expanded"; PICKER_STATE=$d PICKER_CURRENT=$(tmux display -p '#{session_id}') tmux/session-picker.sh list | LC_ALL=C awk -F '\t' -v p="$n" -v g="$(printf '\033[38;2;170;217;76m\357\200\214')" '$2 == p && index($0, g) { f = 1 } END { exit !f }'; echo $?`
  prints `0`. Read-only: never set pane options on the live server.

### Tasks

One wave: T1 and T2 in parallel (disjoint files).

#### T1: `claude/hooks/pane-state.sh` (+ three scratch test scripts)

Files: `claude/hooks/pane-state.sh` (keep mode 755); edit `$S/hook-test.sh`
and `$S/hook-bg-test.sh`; create `$S/hook-done-test.sh` (scratch files, not
committed; never write to `$O`).

1. Replace the whole content of `claude/hooks/pane-state.sh` with exactly
   this (it keeps the shebang, the early exits, no stdout, exit 0; bash 3.2
   compatible):

   ```bash
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
   # Esc and a denied prompt end the turn without any hook event, idle_prompt
   # included; the picker drops such a stale "working" by window activity and
   # never lists it as finished. Never writes to stdout (UserPromptSubmit stdout
   # reaches the model) and always exits 0.

   set -u

   [ -n "${TMUX_PANE:-}" ] || exit 0
   # Headless runs (claude -p, SDK) inherit TMUX_PANE from the session around them
   [ "${CLAUDE_CODE_ENTRYPOINT:-cli}" = "cli" ] || exit 0
   command -v jq >/dev/null 2>&1 && command -v tmux >/dev/null 2>&1 || exit 0
   exec >/dev/null 2>&1

   pane=$TMUX_PANE
   now=$(date +%s)
   # kind: notification type, tool name, SessionStart source or SessionEnd reason.
   # Background shells and monitors outlive any work (dev servers), so only
   # subagents and workflows keep a finished turn listed
   fields=$(jq -r '.hook_event_name // "", .notification_type // .tool_name // .source // .reason // "", .agent_id // "",
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

   case "$event" in
     UserPromptSubmit)
       tmux set -p -t "$pane" @claude_state working \; set -p -t "$pane" @claude_since "$now" \; \
         set -pu -t "$pane" @claude_wait_agent \; set -pu -t "$pane" @claude_wait_from ;;
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
       if [ "${bg:-0}" -gt 0 ]; then await_agents "$bg"; else finish "$now"; fi ;;
     StopFailure)
       # Subagents and summary forks report their own API errors here (agent_id
       # set). Main's payload has no background_tasks: the last Stop's count stands in
       if [ -n "$agent" ]; then :
       elif [ "${inflight:-0}" -gt 0 ]; then await_agents "$inflight"
       else finish "$now"; fi ;;
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
   ```

2. `$S/hook-test.sh`: replace these lines (1:1, nothing else changes; line
   numbers as in `$O/hook-test.sh`):

   | Line | Old | New |
   | --- | --- | --- |
   | 40 | `step "$(ev Stop)" ''` | `step "$(ev Stop)" done` |
   | 41 | `if [ -z "$(state since)" ] && [ -z "$(state wait_agent)" ]; then ok "stop clears all options"; else bad "stop clears all options"; fi` | `s=$(state since); if [ -n "$s" ] && [ $(($(date +%s) - s)) -le 2 ] && [ -z "$(state wait_agent)" ]; then ok "stop sets the end, clears wait_agent"; else bad "stop sets the end, clears wait_agent"; fi` |
   | 42 | `step "$(ev Notification '"notification_type":"permission_prompt"')" ''` | `step "$(ev Notification '"notification_type":"permission_prompt"')" done` |
   | 43 | `step "$(ev PreToolUse '"tool_name":"Bash","agent_id":"bg1"')" ''` | `step "$(ev PreToolUse '"tool_name":"Bash","agent_id":"bg1"')" done` |
   | 45 | `step "$(ev StopFailure '"error":"rate_limit"')" ''` | `step "$(ev StopFailure '"error":"rate_limit"')" done` |
   | 46 | `step "$(ev UserPromptSubmit '"prompt":"x"')" '' sdk-cli` | `step "$(ev UserPromptSubmit '"prompt":"x"')" done sdk-cli` |
   | 48 | `step "$(ev Notification '"notification_type":"idle_prompt"')" ''` | `step "$(ev Notification '"notification_type":"idle_prompt"')" done` |

3. `$S/hook-bg-test.sh`: replace these lines (1:1, nothing else changes; line
   numbers as in `$O/hook-bg-test.sh`):

   | Line | Old | New |
   | --- | --- | --- |
   | 42 | `step "$(ev Stop "$(bg '')")" ''` | `step "$(ev Stop "$(bg '')")" done` |
   | 43 | `check "B3 empty background_tasks clears since" "$(state since)" ""` | `check "B3 empty background_tasks clears the agent count" "$(state agents)" ""` |
   | 46 | `step "$(ev Stop "$(bg "$SH,$MON")")" ''` | `step "$(ev Stop "$(bg "$SH,$MON")")" done` |
   | 60 | `# B8 Stop without the field (older Claude Code) clears` | `# B8 Stop without the field (older Claude Code) ends as done` |
   | 62 | `step "$(ev Stop)" ''` | `step "$(ev Stop)" done` |
   | 63 | `# B9 running agents reported while no state is set: agents with a fresh since` | `# B9 running agents reported after done: agents with a fresh since` |
   | 67 | `# B10 StopFailure and SessionStart still clear` | `# B10 StopFailure and /clear keep the agents counted by the last Stop` |
   | 68 | `step "$(ev StopFailure '"error":"rate_limit"')" ''` | `step "$(ev StopFailure '"error":"rate_limit"')" agents` |
   | 70 | `step "$(ev SessionStart '"source":"clear"')" ''` | `step "$(ev SessionStart '"source":"clear"')" agents` |
   | 71 | `# B11 an agent tool call never creates state from unset` | `# B11 an agent tool call leaves agents alone` |
   | 72 | `step "$(ev PreToolUse '"tool_name":"Bash","agent_id":"a1"')" ''` | `step "$(ev PreToolUse '"tool_name":"Bash","agent_id":"a1"')" agents` |

   (The "agent tool call from unset" case moves to D22 below.)

4. `$S/hook-done-test.sh`, verbatim:

   ```bash
   #!/usr/bin/env bash
   # pane-state.sh finished turns, StopFailure, /clear, compaction and answered agent prompts on an isolated tmux server; prints PASS/FAIL and FAILS=<n>
   set -u
   HOOK=${HOOK:-$HOME/dotfiles/claude/hooks/pane-state.sh}
   t() { env -u TMUX tmux -L hookdonetest -f /dev/null "$@"; }
   t kill-server 2>/dev/null
   t new-session -d -s h -x 80 -y 20 'sleep 600'
   P=$(t display -p -t h '#{pane_id}')
   SOCK=$(t display -p -t h '#{socket_path}')
   [ -n "$P" ] && [ -n "$SOCK" ] || { echo "FAIL no test server"; exit 1; }
   fails=0
   ok() { echo "PASS $1"; }
   bad() { echo "FAIL $1"; fails=$((fails + 1)); }
   check() { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1: want '$3', got '$2'"; fi; }
   state() { t show -pqv -t "$P" "@claude_${1:-state}"; }
   ev() { printf '{"hook_event_name":"%s"%s}' "$1" "${2:+,$2}"; }
   # $1 payload, $2 expected @claude_state ('' = unset)
   step() {
     local out rc
     out=$(printf '%s' "$1" | env TMUX="$SOCK,0,0" TMUX_PANE="$P" CLAUDE_CODE_ENTRYPOINT=cli "$HOOK"); rc=$?
     if [ "$rc" = 0 ] && [ -z "$out" ] && [ "$(state)" = "$2" ]; then ok "$1 -> '$2'"
     else bad "$1 -> want '$2', got '$(state)' rc=$rc stdout='$out'"; fi
   }
   # $1 name, $2 seconds back from now that @claude_since must hold (+-2 s)
   since_ago() {
     local s d
     s=$(state since)
     case "$s" in '' | *[!0-9]*) bad "$1 (since '$s')"; return ;; esac
     d=$(($(date +%s) - ${2:-0} - s))
     if [ "$d" -ge -2 ] && [ "$d" -le 2 ]; then ok "$1"; else bad "$1 (since $s, off by $d s)"; fi
   }
   reset() {
     t set -pu -t "$P" @claude_state \; set -pu -t "$P" @claude_since \; set -pu -t "$P" @claude_wait_agent \; \
       set -pu -t "$P" @claude_wait_from \; set -pu -t "$P" @claude_agents
   }
   bg() { printf '"background_tasks":[%s]' "$1"; }
   SUB='{"id":"a1","type":"subagent","status":"running","description":"d","agent_type":"general-purpose"}'
   WF='{"id":"w1","type":"workflow","status":"running","description":"d","name":"review"}'
   PR='"prompt":"x"'

   # D1 a turn with nothing left running ends as done, since = the end
   step "$(ev UserPromptSubmit "$PR")" working
   t set -p -t "$P" @claude_since 100 \; set -p -t "$P" @claude_wait_agent main \; \
     set -p -t "$P" @claude_wait_from working \; set -p -t "$P" @claude_agents 2
   step "$(ev Stop "$(bg '')")" done
   since_ago "D1 done since is the end"
   check "D1 done unsets wait_agent" "$(state wait_agent)" ""
   check "D1 done unsets wait_from" "$(state wait_from)" ""
   check "D1 done unsets the agent count" "$(state agents)" ""
   # D2 idle_prompt 60 s after the end keeps the row and its end
   t set -p -t "$P" @claude_since 100
   step "$(ev Notification '"notification_type":"idle_prompt"')" done
   check "D2 idle_prompt keeps the end" "$(state since)" 100
   # D3 a new prompt replaces the finished row
   step "$(ev UserPromptSubmit "$PR")" working
   since_ago "D3 new turn restarts since"
   # D4 a main tool call after done starts a turn
   step "$(ev Stop)" done
   t set -p -t "$P" @claude_since 100
   step "$(ev PreToolUse '"tool_name":"Bash"')" working
   since_ago "D4 main tool call after done restarts since"
   # D5 agent tool calls and dialog notifications leave done alone
   step "$(ev Stop)" done
   step "$(ev PreToolUse '"tool_name":"Bash","agent_id":"a1"')" done
   step "$(ev PostToolUse '"tool_name":"Bash","agent_id":"a1"')" done
   step "$(ev Notification '"notification_type":"permission_prompt"')" done
   # D6 a subagent prompt after done starts the clock; answered, the agent runs on
   t set -p -t "$P" @claude_since 100
   step "$(ev PermissionRequest '"tool_name":"Bash","agent_id":"a1"')" waiting
   since_ago "D6 waiting from done restarts since"
   check "D6 wait_from" "$(state wait_from)" done
   step "$(ev PostToolUse '"tool_name":"Bash","agent_id":"a1"')" agents
   check "D6 answer unsets wait_agent" "$(state wait_agent)" ""
   check "D6 answer unsets wait_from" "$(state wait_from)" ""
   # D7 StopFailure with no agents counted: done
   step "$(ev UserPromptSubmit "$PR")" working
   step "$(ev StopFailure '"error":"rate_limit"')" done
   since_ago "D7 StopFailure done since is the end"
   # D8 StopFailure keeps the agents counted by the last Stop
   step "$(ev UserPromptSubmit "$PR")" working
   step "$(ev Stop "$(bg "$SUB,$WF")")" agents
   check "D8 Stop stores the count" "$(state agents)" 2
   step "$(ev UserPromptSubmit "$PR")" working
   t set -p -t "$P" @claude_since 100
   step "$(ev StopFailure '"error":"server_error"')" agents
   check "D8 StopFailure keeps the turn start" "$(state since)" 100
   check "D8 StopFailure keeps the count" "$(state agents)" 2
   # D9 StopFailure of a subagent or a summary fork changes nothing
   step "$(ev StopFailure '"error":"server_error","agent_id":"a1","agent_type":"general-purpose"')" agents
   step "$(ev UserPromptSubmit "$PR")" working
   step "$(ev StopFailure '"error":"server_error","agent_id":"f1"')" working
   # D10 idle_prompt ends a leftover agents or working: done, ended 60 s back
   step "$(ev Stop "$(bg "$SUB")")" agents
   step "$(ev Notification '"notification_type":"idle_prompt"')" done
   since_ago "D10 idle_prompt end is 60 s back" 60
   check "D10 idle_prompt unsets the count" "$(state agents)" ""
   step "$(ev UserPromptSubmit "$PR")" working
   step "$(ev Notification '"notification_type":"idle_prompt"')" done
   # D11 idle_prompt leaves waiting and unset alone
   step "$(ev PreToolUse '"tool_name":"Bash"')" working
   step "$(ev PermissionRequest '"tool_name":"Bash"')" waiting
   step "$(ev Notification '"notification_type":"idle_prompt"')" waiting
   reset
   step "$(ev Notification '"notification_type":"idle_prompt"')" ''
   # D12 a background agent's prompt while only agents run: answered, agents again
   step "$(ev UserPromptSubmit "$PR")" working
   step "$(ev Stop "$(bg "$SUB")")" agents
   t set -p -t "$P" @claude_since 100
   step "$(ev PermissionRequest '"tool_name":"Bash","agent_id":"a1"')" waiting
   check "D12 wait_from" "$(state wait_from)" agents
   check "D12 wait_agent" "$(state wait_agent)" a1
   step "$(ev PostToolUse '"tool_name":"Read","agent_id":"a2"')" waiting
   step "$(ev PostToolUse '"tool_name":"Bash","agent_id":"a1"')" agents
   check "D12 answer keeps since" "$(state since)" 100
   check "D12 answer unsets wait_agent" "$(state wait_agent)" ""
   check "D12 answer unsets wait_from" "$(state wait_from)" ""
   # D13 a failed tool answers too
   step "$(ev PermissionRequest '"tool_name":"Bash","agent_id":"a1"')" waiting
   step "$(ev PostToolUseFailure '"tool_name":"Bash","agent_id":"a1"')" agents
   # D14 a subagent prompt while main is mid-turn: working again
   step "$(ev UserPromptSubmit "$PR")" working
   step "$(ev PermissionRequest '"tool_name":"Bash","agent_id":"a1"')" waiting
   check "D14 wait_from" "$(state wait_from)" working
   step "$(ev PostToolUse '"tool_name":"Bash","agent_id":"a1"')" working
   # D15 a second prompt keeps the state from before the first
   step "$(ev Stop "$(bg "$SUB")")" agents
   step "$(ev PermissionRequest '"tool_name":"Bash","agent_id":"a1"')" waiting
   step "$(ev PermissionRequest '"tool_name":"Bash","agent_id":"a2"')" waiting
   check "D15 wait_from kept" "$(state wait_from)" agents
   check "D15 wait_agent is the latest" "$(state wait_agent)" a2
   step "$(ev PostToolUse '"tool_name":"Bash","agent_id":"a2"')" agents
   # D16 main's question while only agents run is a turn: answered, working
   step "$(ev PreToolUse '"tool_name":"AskUserQuestion"')" waiting
   check "D16 wait_from" "$(state wait_from)" agents
   step "$(ev PostToolUse '"tool_name":"AskUserQuestion"')" working
   # D17 /clear while agents run keeps them
   step "$(ev UserPromptSubmit "$PR")" working
   step "$(ev Stop "$(bg "$SUB")")" agents
   t set -p -t "$P" @claude_since 100
   step "$(ev SessionEnd '"reason":"clear"')" agents
   step "$(ev SessionStart '"source":"clear"')" agents
   check "D17 /clear keeps since" "$(state since)" 100
   check "D17 /clear keeps the count" "$(state agents)" 1
   step "$(ev UserPromptSubmit '"prompt":"<task-notification>"')" working
   step "$(ev Stop "$(bg '')")" done
   # D18 /clear drops a finished row
   step "$(ev SessionEnd '"reason":"clear"')" ''
   check "D18 /clear unsets since" "$(state since)" ""
   step "$(ev Stop)" done
   step "$(ev SessionStart '"source":"clear"')" ''
   # D19 /clear drops a stale working (a turn ended by Esc)
   step "$(ev UserPromptSubmit "$PR")" working
   step "$(ev SessionEnd '"reason":"clear"')" ''
   # D20 compaction leaves every state alone
   step "$(ev UserPromptSubmit "$PR")" working
   step "$(ev SessionStart '"source":"compact"')" working
   step "$(ev Stop)" done
   t set -p -t "$P" @claude_since 100
   step "$(ev SessionStart '"source":"compact"')" done
   check "D20 compact keeps the end" "$(state since)" 100
   step "$(ev UserPromptSubmit "$PR")" working
   step "$(ev Stop "$(bg "$SUB")")" agents
   step "$(ev SessionStart '"source":"compact"')" agents
   # D21 exit, startup and resume unset everything
   step "$(ev SessionEnd '"reason":"prompt_input_exit"')" ''
   check "D21 exit unsets the count" "$(state agents)" ""
   step "$(ev Stop)" done
   step "$(ev SessionStart '"source":"startup"')" ''
   step "$(ev Stop "$(bg "$SUB")")" agents
   step "$(ev SessionStart '"source":"resume"')" ''
   # D22 agent events never create state from unset
   step "$(ev PreToolUse '"tool_name":"Bash","agent_id":"a1"')" ''
   step "$(ev PostToolUse '"tool_name":"Bash","agent_id":"a1"')" ''
   step "$(ev StopFailure '"error":"server_error","agent_id":"a1"')" ''
   # D23 agents reported after done start a fresh clock
   step "$(ev Stop)" done
   t set -p -t "$P" @claude_since 100
   step "$(ev Stop "$(bg "$SUB")")" agents
   since_ago "D23 agents after done restart since"
   t kill-server
   echo "FAILS=$fails"
   exit "$fails"
   ```

Named mutations (file `claude/hooks/pane-state.sh`, each on a fresh copy of
the commit; mutation command, from the copy's root:
`bash -n claude/hooks/pane-state.sh && HOOK=claude/hooks/pane-state.sh bash $S/hook-done-test.sh`;
each must print at least one FAIL, in the named case; a `step` FAIL line
prints the payload instead of the case name, so those mutations quote the
FAIL text):

- M1 Stop without agents clears: old
  `    if [ "${bg:-0}" -gt 0 ]; then await_agents "$bg"; else finish "$now"; fi ;;`,
  new `    if [ "${bg:-0}" -gt 0 ]; then await_agents "$bg"; else clear_state; fi ;;`.
  Fails D1.
- M2 idle_prompt clears a finished row: old
  `      idle_prompt) case "$cur" in working | agents) finish $((now - 60)) ;; esac ;;`,
  new `      idle_prompt) clear_state ;;`. Fails D2.
- M3 StopFailure ignores the count: old
  `    elif [ "${inflight:-0}" -gt 0 ]; then await_agents "$inflight"`, new
  `    elif false; then await_agents "$inflight"`. Fails D8.
- M4 an agent's StopFailure counts as main's: old
  `    if [ -n "$agent" ]; then :`, new `    if false; then :`. Fails D9
  (`"agent_id":"f1"} -> want 'working', got 'agents'`).
- M5 an answered background agent goes back to working: old
  `        case "$from" in agents | done | none) next=agents ;; esac`, new
  `        case "$from" in agents | done | none) next=working ;; esac`. Fails D12
  (`"tool_name":"Bash","agent_id":"a1"} -> want 'agents', got 'working'`).
- M6 main's answered question restores agents: old
  `      if [ "$me" != main ]; then`, new `      if true; then`. Fails D16
  (`"tool_name":"AskUserQuestion"} -> want 'working', got 'agents'`).
- M7 a mid-turn subagent prompt restores agents: old
  `        case "$from" in agents | done | none) next=agents ;; esac`, new
  `        case "$from" in *) next=agents ;; esac`. Fails D14
  (`"tool_name":"Bash","agent_id":"a1"} -> want 'working', got 'agents'`).
- M8 a nested prompt overwrites wait_from: old
  `  [ "$cur" = waiting ] || tmux set -p -t "$pane" @claude_wait_from "${cur:-none}"`,
  new `  tmux set -p -t "$pane" @claude_wait_from "${cur:-none}"`. Fails D15.
- M9 /clear drops agents: old
  `      clear) [ "$cur" = agents ] || clear_state ;;`, new
  `      clear) clear_state ;;`. Fails D17.
- M10 /clear keeps a finished row: old
  `      clear) [ "$cur" = agents ] || clear_state ;;`, new
  `      clear) [ "$cur" = agents ] || [ "$cur" = done ] || clear_state ;;`. Fails D18.
- M11 compaction clears: old `      compact) ;;`, new
  `      compact) clear_state ;;`. Fails D20.
- M12 done counts as a running turn: old
  `case "$cur" in working | waiting | agents) active=1 ;; *) active= ;; esac`,
  new `case "$cur" in working | waiting | agents | done) active=1 ;; *) active= ;; esac`.
  Fails D6 and D23.
- M13 idle_prompt end not shifted: old `finish $((now - 60))`, new
  `finish "$now"`. Fails D10.
- M14 idle_prompt ends a pending prompt: old
  `case "$cur" in working | agents) finish`, new
  `case "$cur" in working | agents | waiting) finish`. Fails D11
  (`"notification_type":"idle_prompt"} -> want 'waiting', got 'done'`).
- M15 finish keeps the agent count: in `finish()`, old
  `    set -pu -t "$pane" @claude_wait_agent \; set -pu -t "$pane" @claude_wait_from \; \`
  + newline + `    set -pu -t "$pane" @claude_agents` (the two lines after the
  `@claude_state done` line), new the single line
  `    set -pu -t "$pane" @claude_wait_agent \; set -pu -t "$pane" @claude_wait_from`.
  Fails D1.
- M16 a main tool call after done is ignored: old
  `    elif [ -z "$agent" ] && [ "$cur" != working ] && [ "$cur" != waiting ]; then`,
  new `    elif [ -z "$agent" ] && { [ -z "$cur" ] || [ "$cur" = agents ]; }; then`.
  Fails D4.

Task gates (from `~/dotfiles`): `bash -n claude/hooks/pane-state.sh && /bin/bash -n claude/hooks/pane-state.sh`,
`test -x claude/hooks/pane-state.sh`, Gate 3 for this file, Gates 4, 5, 6,
and the AC5 `diff` checks for the two edited suites.

Definition of done: the file replaced, the two suites edited as listed, the
new suite saved, task gates green (paste the three `FAILS=` lines and the two
`diff | grep '^[0-9]'` outputs).

#### T2: `tmux/session-picker.sh` and the `README.md` keymap row (+ one scratch test script)

Files: `tmux/session-picker.sh` (keep mode 755), `README.md` line 380 only;
create `$S/picker-done-test.sh` (scratch, not committed).

Edits to `tmux/session-picker.sh` (line numbers as of the branch base):

1. Header, lines 4-5, replace

   ```
   # Claude panes that are mid-turn or waiting on background agents are listed in
   # a section pinned to the bottom of the list, refreshed every 2 s.
   ```

   with

   ```
   # Claude panes that are mid-turn or waiting on background agents are listed in
   # a section pinned to the bottom of the list, refreshed every 2 s; below them,
   # panes whose turn finished in the last 10 minutes, newest first.
   ```

2. Line 10, replace

   ```
   #   active row    $sid  %pid      (empty)          Claude pane mid-turn
   ```

   with

   ```
   #   active row    $sid  %pid      (empty)          Claude pane mid-turn or finished
   ```

3. Lines 96-100, replace

   ```
           if (busy && claude) {
             na++; asid[na] = $1; apid[na] = $3; aname[na] = $5; aw[na] = $7 "." $8
             ast[na] = $13; asince[na] = $14; atitle[na] = strip($11); apath[na] = $12
           }
           if ($4 != 1) next
   ```

   with

   ```
           if (busy && claude) {
             na++; asid[na] = $1; apid[na] = $3; aname[na] = $5; aw[na] = $7 "." $8
             ast[na] = $13; asince[na] = $14; atitle[na] = strip($11); apath[na] = $12
           }
           # A finished turn stays listed for 10 minutes after its end
           if (claude && $13 == "done" && $14 ~ /^[0-9]+$/ && now - $14 < 600) {
             nd++; dsid[nd] = $1; dpid[nd] = $3; dname[nd] = $5; dw[nd] = $7 "." $8
             dend[nd] = $14 + 0; dtitle[nd] = strip($11); dpath[nd] = $12
           }
           if ($4 != 1) next
   ```

4. Lines 131-132, replace

   ```
           if (na && !search) {
             fill = height - out - 1 - na
   ```

   with

   ```
           if (na + nd && !search) {
             fill = height - out - 1 - na - nd
   ```

5. Lines 147-149, replace

   ```
               c(grey, sprintf("%5s", ago(asince[i]))), c(w ? orange : grey, t)
           }
           if (skipfile != "") print skip > skipfile
   ```

   with

   ```
               c(grey, sprintf("%5s", ago(asince[i]))), c(w ? orange : grey, t)
           }
           # Finished rows, newest end first (insertion sort, stable on ties)
           for (i = 1; i <= nd; i++) {
             for (j = i; j > 1 && dend[ord[j - 1]] < dend[i]; j--) ord[j] = ord[j - 1]
             ord[j] = i
           }
           for (k = 1; k <= nd; k++) {
             i = ord[k]
             t = dtitle[i] != "" ? dtitle[i] : short(dpath[i])
             printf "%s\t%s\t\t  %s %s  %s  %s\n", dsid[i], dpid[i], c(green, "\357\200\214"),
               c(grey, sprintf("%-" width "s › %-5s", dname[i], dw[i])),
               c(grey, sprintf("%5s", ago(dend[i]))), c(grey, t)
           }
           if (skipfile != "") print skip > skipfile
   ```

   The octal escapes stay ASCII in the source (Nerd Font glyphs typed into
   Edit vanish); check with `grep -c '357\\200\\214' tmux/session-picker.sh`
   (prints `1`).

Edit to `README.md` line 380: replace the substring
`or waiting on background agents are listed live at the bottom, `
with
`or waiting on background agents are listed live at the bottom, panes whose turn finished in the last 10 minutes below them, `.
Nothing else in `README.md` changes.

Must not change: the busy rule (line 95), the active rows' layout and colors,
fillers' up/down targets, the rule row, every other function, fzf options and
bindings.

`$S/picker-done-test.sh`, verbatim:

```bash
#!/usr/bin/env bash
# session-picker.sh list: finished rows of the claude section on an isolated tmux server; prints PASS/FAIL and FAILS=<n>
set -u
PICKER=${PICKER:-$HOME/dotfiles/tmux/session-picker.sh}
t() { env -u TMUX tmux -L pickerdonetest -f /dev/null "$@"; }
W=$(mktemp -d)
# pane_current_command must read "claude": a signed copy of sleep
cp /bin/sleep "$W/claude" && codesign -s - -f "$W/claude" 2>/dev/null
t kill-server 2>/dev/null
t new-session -d -s p -x 160 -y 40 "$W/claude 600"
# a printing sibling keeps window 0 active; windows 1-4 stay silent
t split-window -d -t p:0 'while :; do printf .; sleep 1; done'
t new-window -d -t p:1 "$W/claude 600"
t new-window -d -t p:2 "$W/claude 600"
t new-window -d -t p:3 "$W/claude 600"
t new-window -d -t p:4 'sleep 600'
A=$(t display -p -t p:0.0 '#{pane_id}')
B=$(t display -p -t p:1.0 '#{pane_id}')
C=$(t display -p -t p:2.0 '#{pane_id}')
D=$(t display -p -t p:3.0 '#{pane_id}')
E=$(t display -p -t p:4.0 '#{pane_id}')
SOCK=$(t display -p -t p '#{socket_path}')
SID=$(t display -p -t p '#{session_id}')
[ -n "$A" ] && [ -n "$E" ] && [ -n "$SOCK" ] || { echo "FAIL no test server"; exit 1; }
for i in 1 2 3 4 5 6 7 8 9 10; do
  [ "$(t list-panes -s -t p -F '#{pane_current_command}' | grep -c '^claude$')" = 4 ] && break
  sleep 0.3
done
fails=0
ok() { echo "PASS $1"; }
bad() { echo "FAIL $1"; fails=$((fails + 1)); }
now=$(date +%s)
# $1 pane, $2 state, $3 since
setst() { t set -p -t "$1" @claude_state "$2" \; set -p -t "$1" @claude_since "$3"; }
G_DONE=$(printf '\357\200\214')
GREEN_DONE=$(printf '\033[38;2;170;217;76m\357\200\214')
G_AGENTS=$(printf '\357\203\200')
G_WORK=$(printf '\357\204\220')
G_WAIT=$(printf '\357\203\263')
RULE='── claude ──'
# extra args: VAR=value pairs for the picker's environment
list() {
  local d
  d=$(mktemp -d)
  : >"$d/expanded"
  env TMUX="$SOCK,0,0" PICKER_STATE="$d" PICKER_CURRENT="$SID" "$@" "$PICKER" list
  rm -rf "$d"
}
# $1 pane: line number of its row in the list, 0 when absent
rowno() { list | LC_ALL=C awk -F '\t' -v p="$1" '$2 == p { print NR; f = 1; exit } END { if (!f) print 0 }'; }
rowof() { list | LC_ALL=C awk -F '\t' -v p="$1" '$2 == p'; }
has() { case "$1" in *"$2"*) return 0 ;; esac; return 1; }

setst "$A" working "$now"
setst "$B" done $((now - 125))
setst "$C" done $((now - 300))
setst "$D" done $((now - 610))
setst "$E" done $((now - 30))
sleep 6
r=$(rowof "$B")
if has "$r" "$GREEN_DONE" && ! has "$r" "$G_WORK" && ! has "$r" "$G_AGENTS" && ! has "$r" "$G_WAIT"; then
  ok "P1 finished row with the green check marker"
else bad "P1 finished row with the green check marker: '$r'"; fi
if has "$r" "   2m"; then ok "P2 age since the end"; else bad "P2 age since the end: '$r'"; fi
a=$(rowno "$A"); b=$(rowno "$B"); c=$(rowno "$C")
if [ "$a" -gt 0 ] && [ "$b" -gt "$a" ] && [ "$c" -gt "$b" ]; then ok "P3 active row, then finished rows newest first"
else bad "P3 active row, then finished rows newest first (a=$a b=$b c=$c)"; fi
if [ "$(rowno "$D")" = 0 ]; then ok "P4 finished 610 s ago is not listed"; else bad "P4 finished 610 s ago is not listed"; fi
setst "$D" done $(($(date +%s) - 590))
if [ "$(rowno "$D")" -gt 0 ]; then ok "P5 finished 590 s ago is listed"; else bad "P5 finished 590 s ago is listed"; fi
setst "$D" done "$(($(date +%s) - 30))x"
if [ "$(rowno "$D")" = 0 ]; then ok "P6 a non-numeric end is not listed"; else bad "P6 a non-numeric end is not listed"; fi
if [ "$(rowno "$E")" = 0 ]; then ok "P7 a pane not running claude is not listed"; else bad "P7 a pane not running claude is not listed"; fi
setst "$D" working "$(date +%s)"
if [ "$(rowno "$D")" = 0 ]; then ok "P8 working in a silent window is not shown as finished"; else bad "P8 working in a silent window is not shown as finished"; fi
t set -pu -t "$A" @claude_state
t set -pu -t "$D" @claude_state
if list | grep -qF "$RULE" && [ "$(rowno "$B")" -gt 0 ]; then ok "P9 the section shows with finished rows only"
else bad "P9 the section shows with finished rows only"; fi
n=$(list FZF_LINES=30 FZF_PREVIEW_TOP=1 | wc -l | tr -d ' ')
if [ "$n" = 22 ]; then ok "P10 fillers leave the last finished row on the bottom edge"
else bad "P10 fillers leave the last finished row on the bottom edge ($n lines, want 22)"; fi
r=$(list FZF_QUERY=x)
if printf '%s\n' "$r" | LC_ALL=C awk -F '\t' -v p="$B" '$2 == p { f = 1 } END { exit !f }' &&
  ! printf '%s\n' "$r" | grep -qF "$RULE"; then ok "P11 search mode lists finished rows without the rule"
else bad "P11 search mode lists finished rows without the rule"; fi
t kill-server
rm -rf "$W"
echo "FAILS=$fails"
exit "$fails"
```

Named mutations (file `tmux/session-picker.sh`, each on a fresh copy of the
commit; mutation command, from the copy's root:
`bash -n tmux/session-picker.sh && PICKER=tmux/session-picker.sh bash $S/picker-done-test.sh`;
each must print at least one FAIL, in the named case):

- M17 finished rows never listed: old `$13 == "done" && $14`, new
  `$13 == "finished" && $14`. Fails P1.
- M18 no expiry: old `now - $14 < 600`, new `now - $14 < 6000`. Fails P4.
- M19 no command filter: old `if (claude && $13 == "done"`, new
  `if ($13 == "done"`. Fails P7.
- M20 oldest first: old `dend[ord[j - 1]] < dend[i]`, new
  `dend[ord[j - 1]] > dend[i]`. Fails P3.
- M21 fillers ignore finished rows: old `fill = height - out - 1 - na - nd`,
  new `fill = height - out - 1 - na`. Fails P10.
- M22 no section without active rows: old `if (na + nd && !search) {`, new
  `if (na && !search) {`. Fails P9.
- M23 working marker on finished rows: old `c(green, "\357\200\214")`, new
  `c(green, "\357\204\220")`. Fails P1.
- M24 non-numeric end accepted: old `$13 == "done" && $14 ~ /^[0-9]+$/ && `,
  new `$13 == "done" && `. Fails P6.
- M25 a stale working counts as finished: old `$13 == "done" && $14`, new
  `($13 == "done" || $13 == "working") && $14`. Fails P8.

Task gates (from `~/dotfiles`): `bash -n tmux/session-picker.sh && /bin/bash -n tmux/session-picker.sh`,
`test -x tmux/session-picker.sh`, Gate 3 for `tmux/session-picker.sh` and
`README.md`, Gates 7, 8, 9, AC3's two `grep -c` checks, AC7.

Definition of done: the five script edits and the README substring applied,
the test script saved, task gates green (paste the three `FAILS=` lines).

### Seams

| Producer | Consumer | Shared definition |
| --- | --- | --- |
| T1 (`@claude_state` = `done`, `@claude_since` = end) | T2 (finished-row condition and age in `render`) | State literal `done`; Finished-row window |
| T1 (`agents` kept across StopFailure and /clear) | T2 (unchanged busy rule) | Other literals unchanged |

### Edge cases

- macOS vs Linux: the hook is wired on macOS only and the picker runs only
  with fzf >= 0.73; both unchanged.
- `/bin/bash` 3.2 runs the hook: `IFS=: read`, nested `case`, `$(( ))`,
  `[ ]` only.
- Older Claude Code (no `background_tasks`, no `agent_id` on StopFailure):
  `Stop` gives `done`, `StopFailure` gives `done` unless a count is stored.
- Missing `jq`/`tmux`: the existing early exits still apply.
- First run: running sessions pick up the edited hook at once through the
  `~/.claude/hooks/pane-state.sh` symlink; pane options from the old hook
  work as before (Design, Decisions).
- Clock: `ago` clamps a future end to `0s`; a non-numeric since is never
  listed.
- Two Claude panes in one window: finished rows do not depend on window
  activity; active rows keep the per-window guard.
- Dirty worktree: the branch starts from a clean `main` (78f2c69).

### Known limitations (reported, not fixed)

- A turn that launches background agents and then fails (`StopFailure`
  before any `Stop` reports them): `done` until the first hand-back's `Stop`
  recounts; the stored count predates the launch.
- `StopFailure` on the last agent's hand-back turn: the stored count is stale,
  so `agents` (hidden by the activity guard once the agent timer stops) until
  `idle_prompt` 60 s later turns it into `done` ended 60 s back.
- A denied background agent prompt: `waiting` until that agent's next
  answered prompt or its hand-back; its only event is `PostToolBatch`, which
  is not wired (wiring it needs `install.sh` and `~/.claude/settings.json`).
- Esc mid-turn and a denied main prompt: no event, no `idle_prompt`
  (re-checked on 2.1.309); a stale `working` is hidden by the activity guard,
  a stale `waiting` stays listed until the next prompt; neither becomes a
  finished row.
- The end set by `idle_prompt` assumes Claude Code's 60 s idle delay
  (measured 60.0 to 60.9 s).
- `/clear` kills a background agent's running tool call (exit 137); the agent
  may give up and hand back at once, which then ends as `done`.

### Not doing

- Dropping a finished row when the user visits the pane, notifications, a
  config knob for the 600 s.
- Finished rows for Esc-ended or denied turns, or from `#{window_activity}`.
- Reading transcripts or `~/.claude` files from the hook
  (`pendingBackgroundAgentCount`, agent `meta.json`): internal formats.
- New hook events (`PostToolBatch`, `SubagentStop`), changes to `install.sh`,
  `~/.claude/settings.json`, `.tmux.conf`, `everything.md`, README line 264,
  or the earlier plan files.
