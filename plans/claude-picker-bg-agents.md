# claude-picker-bg-agents

## Goal

A Claude session whose main turn is over while background subagents or
workflows still run stays listed in the `prefix + s` picker's claude section,
with its own marker, until the last of them hands back or is killed.

## Current behavior

`claude/hooks/pane-state.sh` clears `@claude_state` on every `Stop` and never
creates state from tool events that carry `agent_id`
(`plans/claude-activity-picker.md`, Edge cases: "background subagents: skipped
by `agent_id`"). A session that launched background agents and ended its turn
(screen: "Waiting for N background agents", footer agent timer running) is
absent from the picker for as long as the agents run. Agent calls run in the
background by default (fork mode), so this is the common case.

## Spike findings (Claude Code 2.1.308, evidence in `$S/spike-bg/`, not committed)

- The `Stop` payload carries `background_tasks`: the in-flight background work
  of the session, each entry `{id, type, status, description, agent_type?,
  command?, server?, tool?, name?}`. `type` is a label: `shell`, `subagent`,
  `monitor`, `workflow` (hook input schema in the binary: "Lets hooks
  distinguish 'session is done' from 'session is paused waiting for background
  work to wake it'. Empty array when nothing is in flight."). Non-empty on the
  Stop that ends the launching turn; `[]` on the Stop after the last agent
  finished or was killed. `StopFailure` has no such field.
- Every agent hand-back fires `UserPromptSubmit` (prompt
  `<agent-message from=...>`) and then `Stop`; a kill (TaskStop or the UI
  agents panel, `x`) fires `UserPromptSubmit` (`<task-notification>`) and then
  `Stop`. So every change of the running set is followed by a `Stop` that
  carries the new set. Two agents finishing 0.6 s apart: two such turns.
- `SubagentStop` never fires for a killed agent, and an unmatched
  `SubagentStop` (`agent_type: ""`, internal helper) fires without a
  `SubagentStart`. Counting start/stop events is unreliable: not used.
- Main idle, background agent running: the footer agent timer redraws every
  second, max `now - #{window_activity}` 1.7 s (0.5 s sampling). The picker's
  5 s activity guard holds; after all work ends the gap grows unbounded.
- `Notification` `idle_prompt` did not fire while an agent ran; it fired 60 s
  after the final `Stop`.
- `/clear` with an agent running: `SessionEnd` + `SessionStart` clear the
  state; the agent survives, its hand-back turn sets the state again.
- Esc on main or on a foreground subagent fires no event (as in the first
  spike).

## Design

- New `@claude_state` value `agents`: main turn over, at least one
  `background_tasks` entry of type `subagent` or `workflow`. `shell` and
  `monitor` entries do not count: dev servers and monitors outlive any work and
  would pin the pane as busy.
- `Stop`: count > 0: state `agents`, `@claude_since` kept (set to now only when
  unset), `@claude_wait_agent` unset. Count 0 or field missing: clear, as
  today.
- `PreToolUse` from main (no `agent_id`) while the state is unset or `agents`:
  `working` with a fresh `@claude_since` (a turn that began without a prompt).
- Unchanged: `UserPromptSubmit` (hand-back and kill turns too) sets `working`;
  `StopFailure`, `SessionStart`, `SessionEnd` clear; agent tool events never
  create state from unset; `waiting` handling.
- Picker: `agents` is busy under the same 5 s window-activity guard as
  `working`; marker cyan U+F0C0 (Font Awesome users) instead of the working
  spinner U+F110.
- No new hook events: `install.sh` and `~/.claude/settings.json` stay as they
  are.

## Workflow sections

### Shared definitions

- `S=/private/tmp/claude-501/-Users-demonr-dotfiles/cd429fbc-0e3f-470f-8ab5-6d3bae06538f/scratchpad`
  (session scratchpad; test scripts live there, not in the repo).
- State literal: `agents` (lowercase, exact) in the pane option
  `@claude_state`. T1 writes it, T2 reads it.
- Counted task types: `subagent`, `workflow`. jq for the count (one line):
  `([.background_tasks[]? | select(.type == "subagent" or .type == "workflow")] | length)`
- Marker bytes in the picker's awk (octal escapes, ASCII in the source):
  agents `\357\203\200` (U+F0C0); unchanged: working `\357\204\220` (U+F110),
  waiting `\357\203\263` (U+F0F3).
- Test scripts: tmux sockets `-L hooktest` (old suite), `-L hookbgtest`,
  `-L pickerbgtest`. Runs of one script must not overlap (shared socket), so
  mutation runs go one after another.

### Gates

Run from `~/dotfiles`.

1. `for f in claude/hooks/pane-state.sh tmux/session-picker.sh; do bash -n "$f" && /bin/bash -n "$f" || echo "BAD $f"; done`
   prints nothing.
2. `git ls-files -s claude/hooks/pane-state.sh tmux/session-picker.sh | awk '{print $1}'`
   prints `100755` twice.
3. `for f in claude/hooks/pane-state.sh tmux/session-picker.sh README.md plans/claude-picker-bg-agents.md; do printf '%s:' "$f"; LC_ALL=C grep -F -c "$(printf '\342\200\224')" "$f"; done`
   prints `:0` for every file.
4. `bash $S/hook-test.sh | tail -1` prints `FAILS=0` (the first spike's suite,
   regression).
5. `bash $S/hook-bg-test.sh | tail -1` prints `FAILS=0`.
6. `bash $S/picker-bg-test.sh | tail -1` prints `FAILS=0`.

### Acceptance criteria

- AC1 (hook): Gates 4 and 5.
- AC2 (picker): Gate 6.
- AC3 (static): Gates 1-3.
- AC4 (scope): `git diff --name-only main...HEAD` prints exactly
  `README.md`, `claude/hooks/pane-state.sh`, `plans/claude-picker-bg-agents.md`,
  `tmux/session-picker.sh`.
- AC5 (live, run last by the validator, which runs as a background agent of
  the orchestrator's session after the orchestrator's turn ended):
  `tmux display -p -t "$TMUX_PANE" '#{@claude_state}'` prints `agents`, and
  `d=$(mktemp -d); : >"$d/expanded"; PICKER_STATE=$d PICKER_CURRENT=$(tmux display -p '#{session_id}') tmux/session-picker.sh list | LC_ALL=C awk -F '\t' -v p="$TMUX_PANE" -v g="$(printf '\357\203\200')" '$2 == p && index($0, g) { f = 1 } END { exit !f }'; echo $?`
  prints `0`.

### Tasks

One wave: T1 and T2 in parallel (disjoint files).

#### T1: `claude/hooks/pane-state.sh` (+ two scratch test scripts)

Files: `claude/hooks/pane-state.sh` (keep mode 755); create
`$S/hook-test.sh` and `$S/hook-bg-test.sh` (scratch, not committed).

Edits (line numbers as of `main`):

1. Header, lines 4-5, replace

   ```
   #   @claude_state       working (mid-turn) or waiting (mid-turn, blocked on the
   #                       user: permission prompt or question); unset when idle
   ```

   with

   ```
   #   @claude_state       working (mid-turn), waiting (mid-turn, blocked on the
   #                       user: permission prompt or question) or agents (turn
   #                       over, background subagents or workflows still running);
   #                       unset when idle
   ```

2. Lines 21-22, replace

   ```
   fields=$(jq -r '.hook_event_name // "", .notification_type // .tool_name // "", .agent_id // ""') || exit 0
   { read -r event; read -r kind; read -r agent; } <<EOF
   ```

   with

   ```
   # Background shells and monitors outlive any work (dev servers), so only
   # subagents and workflows keep a finished turn listed
   fields=$(jq -r '.hook_event_name // "", .notification_type // .tool_name // "", .agent_id // "",
     ([.background_tasks[]? | select(.type == "subagent" or .type == "workflow")] | length)') || exit 0
   { read -r event; read -r kind; read -r agent; read -r bg; } <<EOF
   ```

3. `PreToolUse` branch, lines 49-50, replace

   ```
       # A main-agent tool call while idle: a turn that began without a prompt
       elif [ -z "$cur" ] && [ -z "$agent" ]; then
   ```

   with

   ```
       # A main-agent tool call while idle or only background agents run: a turn
       # that began without a prompt
       elif [ -z "$agent" ] && { [ -z "$cur" ] || [ "$cur" = agents ]; }; then
   ```

4. Line 64, replace

   ```
     Stop | StopFailure | SessionStart | SessionEnd) clear_state ;;
   ```

   with

   ```
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
   ```

Must not change: everything else in the file (shebang `#!/bin/bash`: the code
stays bash 3.2 compatible; the early exits; `wait_on_user`, `clear_state`,
`PostToolUse`, `Notification` branches; no stdout; exit 0).

Test scripts:

- `$S/hook-test.sh`: the first spike's suite, extracted verbatim:
  `sed -n '107,176p' plans/claude-activity-picker.md | sed 's/^  //' >"$S/hook-test.sh"`
  (first line must be `#!/usr/bin/env bash`, last `exit "$fails"`).
- `$S/hook-bg-test.sh`, verbatim:

  ```bash
  #!/usr/bin/env bash
  # pane-state.sh background-agent cases on an isolated tmux server; prints PASS/FAIL and FAILS=<n>
  set -u
  HOOK=${HOOK:-$HOME/dotfiles/claude/hooks/pane-state.sh}
  t() { env -u TMUX tmux -L hookbgtest -f /dev/null "$@"; }
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
  bg() { printf '"background_tasks":[%s]' "$1"; }
  SUB='{"id":"a1","type":"subagent","status":"running","description":"d","agent_type":"general-purpose"}'
  WF='{"id":"w1","type":"workflow","status":"running","description":"d","name":"review"}'
  SH='{"id":"b1","type":"shell","status":"running","description":"d","command":"npm run dev"}'
  MON='{"id":"m1","type":"monitor","status":"running","description":"d","server":"s","tool":"t"}'

  # B1 a turn that leaves a background subagent running
  step "$(ev UserPromptSubmit '"prompt":"hi"')" working
  t set -p -t "$P" @claude_since 100
  t set -p -t "$P" @claude_wait_agent main
  step "$(ev Stop "$(bg "$SUB")")" agents
  check "B1 agents keeps since" "$(state since)" 100
  check "B1 agents unsets wait_agent" "$(state wait_agent)" ""
  # B2 the agent's own tool calls leave the state alone
  step "$(ev PreToolUse '"tool_name":"Bash","agent_id":"a1"')" agents
  step "$(ev PostToolUse '"tool_name":"Bash","agent_id":"a1"')" agents
  # B3 hand-back turn, then nothing left in flight
  step "$(ev UserPromptSubmit '"prompt":"<agent-message from=a1>"')" working
  step "$(ev Stop "$(bg '')")" ''
  check "B3 empty background_tasks clears since" "$(state since)" ""
  # B4 shells and monitors do not count
  step "$(ev UserPromptSubmit '"prompt":"x"')" working
  step "$(ev Stop "$(bg "$SH,$MON")")" ''
  # B5 a workflow counts, also next to a shell
  step "$(ev UserPromptSubmit '"prompt":"x"')" working
  step "$(ev Stop "$(bg "$SH,$WF")")" agents
  # B6 a main tool call while only agents run starts a turn
  t set -p -t "$P" @claude_since 100
  step "$(ev PreToolUse '"tool_name":"Bash"')" working
  s=$(state since)
  if [ "${s:-0}" -gt 100 ]; then ok "B6 main tool call restarts since"; else bad "B6 main tool call restarts since ($s)"; fi
  # B7 a permission prompt while only agents run: waiting, since kept
  step "$(ev Stop "$(bg "$SUB")")" agents
  t set -p -t "$P" @claude_since 100
  step "$(ev PermissionRequest '"tool_name":"Bash","agent_id":"a1"')" waiting
  check "B7 waiting keeps since" "$(state since)" 100
  # B8 Stop without the field (older Claude Code) clears
  step "$(ev UserPromptSubmit '"prompt":"x"')" working
  step "$(ev Stop)" ''
  # B9 running agents reported while no state is set: agents with a fresh since
  step "$(ev Stop "$(bg "$SUB")")" agents
  s=$(state since)
  if [ -n "$s" ] && [ $(($(date +%s) - s)) -le 2 ]; then ok "B9 agents from unset sets since"; else bad "B9 agents from unset sets since ($s)"; fi
  # B10 StopFailure and SessionStart still clear
  step "$(ev StopFailure '"error":"rate_limit"')" ''
  step "$(ev Stop "$(bg "$SUB")")" agents
  step "$(ev SessionStart '"source":"clear"')" ''
  # B11 an agent tool call never creates state from unset
  step "$(ev PreToolUse '"tool_name":"Bash","agent_id":"a1"')" ''
  t kill-server
  echo "FAILS=$fails"
  exit "$fails"
  ```

Named mutations (file `claude/hooks/pane-state.sh`, each on a fresh copy;
mutation command, from the copy's root:
`HOOK=claude/hooks/pane-state.sh bash $S/hook-bg-test.sh`; build check
`bash -n claude/hooks/pane-state.sh`):

- M1 Stop ignores the agents: old `    if [ "${bg:-0}" -gt 0 ]; then`, new
  `    if false; then`. Fails B1.
- M2 shells count: old `select(.type == "subagent" or .type == "workflow")`,
  new `select(.type != null)`. Fails B4.
- M3 main tool call ignores `agents`: old
  `    elif [ -z "$agent" ] && { [ -z "$cur" ] || [ "$cur" = agents ]; }; then`,
  new `    elif [ -z "$agent" ] && [ -z "$cur" ]; then`. Fails B6.
- M4 `agents` restarts the clock: old (two lines)
  `      [ -n "$cur" ] || tmux set -p -t "$pane" @claude_since "$(date +%s)"` +
  newline + `      tmux set -p -t "$pane" @claude_state agents \; set -pu -t "$pane" @claude_wait_agent`,
  new: the same two lines with `[ -n "$cur" ] || ` removed from the first.
  Fails "B1 agents keeps since".

Task gates (from `~/dotfiles`): Gate 1 for this file only
(`bash -n claude/hooks/pane-state.sh && /bin/bash -n claude/hooks/pane-state.sh`),
`test -x claude/hooks/pane-state.sh`, Gate 3 for this file, Gates 4 and 5.

Definition of done: the four edits applied, the two scripts saved, task gates
green (paste the `FAILS=` lines).

#### T2: `tmux/session-picker.sh` and the `README.md` keymap row (+ one scratch test script)

Files: `tmux/session-picker.sh` (keep mode 755), `README.md` line 380 only;
create `$S/picker-bg-test.sh` (scratch, not committed).

Edits to `tmux/session-picker.sh` (line numbers as of `main`):

1. Header, lines 4-5, replace

   ```
   # Claude panes that are mid-turn are listed in a section pinned to the bottom
   # of the list, refreshed every 2 s.
   ```

   with

   ```
   # Claude panes that are mid-turn or waiting on background agents are listed in
   # a section pinned to the bottom of the list, refreshed every 2 s.
   ```

2. Lines 92-94, replace

   ```
           # Esc or a denied prompt ends a turn without a hook event; a working
           # Claude redraws its spinner every second, so a silent window is idle
           busy = $13 == "waiting" || ($13 == "working" && now - $15 <= 5)
   ```

   with

   ```
           # Esc or a denied prompt ends a turn without a hook event; a working
           # Claude redraws its spinner (its background agents their timer) every
           # second, so a silent window is idle
           busy = $13 == "waiting" || (($13 == "working" || $13 == "agents") && now - $15 <= 5)
   ```

3. Lines 139-140, replace

   ```
             w = ast[i] == "waiting"
             mk = w ? c(orange, "\357\203\263") : c(cyan, "\357\204\220")
   ```

   with

   ```
             w = ast[i] == "waiting"
             if (w) mk = c(orange, "\357\203\263")
             else if (ast[i] == "agents") mk = c(cyan, "\357\203\200")
             else mk = c(cyan, "\357\204\220")
   ```

   The octal escapes stay ASCII in the source (Nerd Font glyphs typed into
   Edit vanish); check with `grep -c '357\\203\\200' tmux/session-picker.sh`
   (prints `1`).

Edit to `README.md` line 380: replace the substring
`Claude panes mid-turn (working, or waiting on you) are listed live at the bottom`
with
`Claude panes mid-turn (working, or waiting on you) or waiting on background agents are listed live at the bottom`.
Nothing else in `README.md` changes.

Must not change: the rest of `render` (row layout, colors, fillers, rule
row), every other function, fzf options and bindings.

`$S/picker-bg-test.sh`, verbatim:

```bash
#!/usr/bin/env bash
# session-picker.sh list: claude section rows per @claude_state on an isolated tmux server; prints PASS/FAIL and FAILS=<n>
set -u
PICKER=${PICKER:-$HOME/dotfiles/tmux/session-picker.sh}
t() { env -u TMUX tmux -L pickerbgtest -f /dev/null "$@"; }
W=$(mktemp -d)
# pane_current_command must read "claude": a signed copy of sleep
cp /bin/sleep "$W/claude" && codesign -s - -f "$W/claude" 2>/dev/null
t kill-server 2>/dev/null
t new-session -d -s p -x 160 -y 40 "$W/claude 600"
# a printing sibling keeps window 0 active; window 1 stays silent
t split-window -d -t p:0 'while :; do printf .; sleep 1; done'
t new-window -d -t p: "$W/claude 600"
A=$(t display -p -t p:0.0 '#{pane_id}')
B=$(t display -p -t p:1.0 '#{pane_id}')
SOCK=$(t display -p -t p '#{socket_path}')
SID=$(t display -p -t p '#{session_id}')
[ -n "$A" ] && [ -n "$B" ] && [ -n "$SOCK" ] || { echo "FAIL no test server"; exit 1; }
for i in 1 2 3 4 5 6 7 8 9 10; do
  [ "$(t display -p -t "$A" '#{pane_current_command}')$(t display -p -t "$B" '#{pane_current_command}')" = claudeclaude ] && break
  sleep 0.3
done
fails=0
ok() { echo "PASS $1"; }
bad() { echo "FAIL $1"; fails=$((fails + 1)); }
now=$(date +%s)
setst() { t set -p -t "$1" @claude_state "$2" \; set -p -t "$1" @claude_since "$now"; }
G_AGENTS=$(printf '\357\203\200')
G_WORK=$(printf '\357\204\220')
G_WAIT=$(printf '\357\203\263')
list() {
  local d
  d=$(mktemp -d)
  : >"$d/expanded"
  env TMUX="$SOCK,0,0" PICKER_STATE="$d" PICKER_CURRENT="$SID" "$PICKER" list
  rm -rf "$d"
}
# $1 name, $2 pane id, $3 marker the pane's active row must hold ('' = no active row)
row() {
  if list | LC_ALL=C awk -F '\t' -v p="$2" -v g="$3" '
      $2 == p { found = 1; if (g != "" && index($0, g)) hit = 1 }
      END { exit (g == "" ? found : !hit) }'; then ok "$1"
  else bad "$1"; fi
}

setst "$A" agents
setst "$B" agents
sleep 6
row "P1 agents row with the users marker" "$A" "$G_AGENTS"
row "P2 agents in a silent window is not listed" "$B" ""
setst "$A" working
row "P3 working marker unchanged" "$A" "$G_WORK"
setst "$A" waiting
row "P4 waiting marker unchanged" "$A" "$G_WAIT"
setst "$B" waiting
row "P5 waiting is listed in a silent window" "$B" "$G_WAIT"
setst "$B" working
row "P6 working in a silent window is not listed" "$B" ""
t kill-server
rm -rf "$W"
echo "FAILS=$fails"
exit "$fails"
```

Named mutations (file `tmux/session-picker.sh`, each on a fresh copy;
mutation command, from the copy's root:
`PICKER=tmux/session-picker.sh bash $S/picker-bg-test.sh`; build check
`bash -n tmux/session-picker.sh`):

- M5 `agents` not busy: old `(($13 == "working" || $13 == "agents") && now - $15 <= 5)`,
  new `(($13 == "working") && now - $15 <= 5)`. Fails P1.
- M6 `agents` skips the activity guard: old
  `busy = $13 == "waiting" || (($13 == "working" || $13 == "agents") && now - $15 <= 5)`,
  new `busy = $13 == "waiting" || $13 == "agents" || ($13 == "working" && now - $15 <= 5)`.
  Fails P2.
- M7 `agents` shows the working marker: old
  `else if (ast[i] == "agents") mk = c(cyan, "\357\203\200")`, new
  `else if (ast[i] == "agents") mk = c(cyan, "\357\204\220")`. Fails P1.

Task gates (from `~/dotfiles`): Gate 1 for this file only
(`bash -n tmux/session-picker.sh && /bin/bash -n tmux/session-picker.sh`),
`test -x tmux/session-picker.sh`, Gate 3 for `tmux/session-picker.sh` and
`README.md`, Gate 6.

Definition of done: the three script edits and the README substring applied,
the test script saved, task gates green (paste the `FAILS=` line).

### Seams

| Producer | Consumer | Shared definition |
| --- | --- | --- |
| T1 (`@claude_state` = `agents` on Stop) | T2 (`busy` and the marker in `render`) | State literal `agents` |

### Edge cases

- macOS vs Linux: the hook is wired on macOS only and the picker runs only
  with fzf >= 0.73; both unchanged.
- `/bin/bash` 3.2 runs the hook: the new code uses only `[ ]`, `{ ...; }`,
  `${var:-default}`.
- Older Claude Code without `background_tasks`: the count is `0`, old
  behavior.
- Missing `jq`/`tmux`: the existing early exits still apply.
- First run: running sessions pick up the edited hook at once through the
  `~/.claude/hooks/pane-state.sh` symlink; the next `Stop` of each session
  sets the new state.
- Dirty worktree: the branch starts from a clean `main`.
- Two Claude panes in one window: the activity guard stays per window, as
  before.

### Known limitations (reported, not fixed)

- `StopFailure` while agents run clears the state (the payload has no
  `background_tasks`); the next hand-back turn restores it.
- `/clear` while agents run: unlisted until the next hand-back turn.
- A background agent's permission prompt while main is idle: `waiting`, then
  `working` after the answer until the next `Stop` recounts.
- Esc mid-turn still fires no event; the activity guard hides the stale row.

### Not doing

- No `SubagentStart`/`SubagentStop` wiring or per-agent bookkeeping.
- Background shells and monitors do not count.
- No agent count or agent names in the picker row.
- No change to `install.sh`, `~/.claude/settings.json`, `.tmux.conf`,
  `everything.md`, or the earlier plan files.
