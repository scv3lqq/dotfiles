# claude-activity-picker

## Goal

`prefix + s` keeps the session tree at the top exactly as now and adds a
section pinned to the bottom edge of the list area: one selectable row per
Claude Code pane that is mid-turn (working, or waiting on the user), refreshed
live. `Enter` on a row jumps to that pane. The state comes from a new Claude
Code hook that writes tmux pane options.

## Current behavior

`tmux/session-picker.sh` (139 lines) shows a collapsible session tree in fzf
(>= 0.71, else `choose-tree`); nothing tells working Claude panes from idle
ones, and the pane title is `✳ <title>` in both cases (re-checked: 394 frames,
every state). Claude hooks in `~/.claude/settings.json`: `notify.sh` (Stop,
ours), `bash-guard.py`/`git-commit-guard.py`/`no-em-dash.sh`/
`skill-note-sync.sh` (local), SessionStart/SessionEnd entries owned by the
tmux-assistant-resurrect plugin (it re-adds them when missing, never removes
others).

## Spike findings (evidence in the session scratchpad, not committed)

Hooks (Claude Code 2.1.303, docs https://code.claude.com/docs/en/hooks, logs in
`$S/spike-hooks/events.log`, `$S/spike-hooks/activity/samples.csv`):

- Events used: UserPromptSubmit, PreToolUse, PermissionRequest (fires as the
  dialog shows, 75 ms after PreToolUse; no `tool_use_id`), PostToolUse,
  PostToolUseFailure, Notification (`matcher` matches `notification_type`:
  `permission_prompt` 6 s after the dialog, `idle_prompt` 60 s after Stop
  only, `elicitation_dialog`), Stop, StopFailure (API error instead of Stop),
  SessionStart, SessionEnd. Subagent events carry `agent_id`.
- AskUserQuestion: PreToolUse(AskUserQuestion), then PermissionRequest, then
  PostToolUse when answered.
- No event at all for Esc mid-turn, a denied permission, or Esc on a question:
  the state stays until the next prompt. A working Claude redraws its spinner
  at least every 1.9 s (thinking, streaming, a long Bash, text typed in the
  input box); after the turn ends the window prints nothing (idle, dialogs).
  So the picker hides a `working` pane whose window printed nothing for 5 s
  (`#{window_activity}`, window granularity). Pane title and screen text were
  rejected: the title never changes, and the footer differs by permission mode
  (bypass shows no `? for shortcuts`) and hides `esc to interrupt` while text
  is typed.
- `TMUX_PANE` and `CLAUDE_CODE_ENTRYPOINT=cli` are in the hook environment.
  Hooks of one event run in parallel; a synchronous 20 ms hook is fine.
  Empty stdout with exit 0 on UserPromptSubmit injects nothing.
- Running sessions pick up hook changes without a restart: proven live on a
  project settings file (the next prompt fired a hook added mid-session, plus
  a `ConfigChange` event); the docs (settings#when-edits-take-effect) say the
  same for `~/.claude/settings.json`. T5 proves it on this very session.

fzf (prototype `$S/spike-fzf/picker.sh`, harness `$S/spike-fzf/harness.sh`,
66/66 on fzf 0.74.5, 0.74.4, 0.73.0):

- Bottom pinning: blank filler rows plus a dim `── claude ──` rule between the
  tree and the active rows, sized from the list height, which fzf does not
  export: `FZF_LINES - 8` (preview right) or `FZF_PREVIEW_TOP - 9` (preview
  below) for the current `--style full:rounded` + footer layout. The initial
  list uses `stty size </dev/tty`; the first tick corrects a miss. Fillers
  never hold the cursor (a `focus` transform jumps over them by `FZF_ACTION`).
- Refresh: the `every(2)` event (fzf 0.73+, 0.72 rejects it) runs a
  synchronous `transform(tick)` that re-renders and reloads only on change.
- No tracked reload anywhere: a tracked reload blocks input and drops keys
  (the current picker loses a Down typed 30 ms after Right, 6 of 6 runs). An
  untracked reload keeps the cursor index; `←`/`Ctrl-d` on a window line do
  `pos(<session row>)+reload-sync(...)`; a tick that moves the focused line
  re-arms `load` to `pos()` it.
- Rows get a 4th field (aux) and `--id-nth 1,2`; `--info-command` subtracts
  the filler rows from the counter.

## Workflow sections

### Shared definitions

- `S=/private/tmp/claude-501/-Users-me-dotfiles/6ded08f5-1df3-4ac5-9aa2-50dbded974e9/scratchpad`
  (session scratchpad: spikes, harness, hook test).
- Pane options (written by the hook, read by the picker):
  - `@claude_state`: `working` (mid-turn) or `waiting` (mid-turn, blocked on
    the user); unset when idle.
  - `@claude_since`: epoch seconds when the turn started.
  - `@claude_wait_agent`: hook-internal, the agent whose prompt is pending
    (`main` or a subagent id).
- Active pane (picker): `@claude_state` is `waiting`, or `working` with
  `now - #{window_activity} <= 5`; AND `#{pane_current_command}` matches
  `^[0-9]+\.[0-9]+\.[0-9]+$` or is `claude`.
- Minimum fzf for the popup: 0.73 (`every(N)` event). `--supported` exits 0
  for >= 0.73, else 1.
- Hook command string: `~/.claude/hooks/pane-state.sh` (symlink to
  `~/dotfiles/claude/hooks/pane-state.sh`).
- Settings filter (jq, used verbatim by T4 and T5):

  ```jq
  reduce ("UserPromptSubmit", "PreToolUse", "PermissionRequest", "PostToolUse",
      "PostToolUseFailure", "Notification", "Stop", "StopFailure",
      "SessionStart", "SessionEnd") as $e (.;
    if any(.hooks[$e][]?.hooks[]?.command; . == "~/.claude/hooks/pane-state.sh") then .
    else .hooks[$e] += [(if $e == "Notification"
        then {matcher: "permission_prompt|elicitation_dialog|idle_prompt"} else {} end)
      + {hooks: [{type: "command", command: "~/.claude/hooks/pane-state.sh", timeout: 5}]}]
    end)
  ```

- Hook test (T1 saves it verbatim as `$S/hook-test.sh`; isolated server
  `-L hooktest` only, the hook reaches it through `TMUX`):

  ```bash
  #!/usr/bin/env bash
  # pane-state.sh test on an isolated tmux server; prints PASS/FAIL and FAILS=<n>
  set -u
  HOOK=${HOOK:-$HOME/dotfiles/claude/hooks/pane-state.sh}
  t() { env -u TMUX tmux -L hooktest -f /dev/null "$@"; }
  t kill-server 2>/dev/null
  t new-session -d -s h -x 80 -y 20 'sleep 600'
  P=$(t display -p -t h '#{pane_id}')
  SOCK=$(t display -p -t h '#{socket_path}')
  [ -n "$P" ] && [ -n "$SOCK" ] || { echo "FAIL no test server"; exit 1; }
  fails=0
  ok() { echo "PASS $1"; }
  bad() { echo "FAIL $1"; fails=$((fails + 1)); }
  state() { t show -pqv -t "$P" "@claude_${1:-state}"; }
  ev() { printf '{"hook_event_name":"%s"%s}' "$1" "${2:+,$2}"; }
  # $1 payload, $2 expected @claude_state ('' = unset), $3 CLAUDE_CODE_ENTRYPOINT
  step() {
    local out rc
    out=$(printf '%s' "$1" | env TMUX="$SOCK,0,0" TMUX_PANE="$P" CLAUDE_CODE_ENTRYPOINT="${3:-cli}" "$HOOK"); rc=$?
    if [ "$rc" = 0 ] && [ -z "$out" ] && [ "$(state)" = "$2" ]; then ok "$1 -> '$2'"
    else bad "$1 -> want '$2', got '$(state)' rc=$rc stdout='$out'"; fi
  }

  step "$(ev UserPromptSubmit '"prompt":"hi"')" working
  since=$(state since); now=$(date +%s)
  if [ -n "$since" ] && [ $((now - since)) -le 2 ]; then ok "prompt sets since"; else bad "prompt sets since ($since)"; fi
  step "$(ev PreToolUse '"tool_name":"Bash"')" working
  step "$(ev PermissionRequest '"tool_name":"Bash"')" waiting
  if [ "$(state since)" = "$since" ] && [ "$(state wait_agent)" = main ]; then ok "waiting keeps since, wait_agent main"; else bad "waiting keeps since, wait_agent main"; fi
  step "$(ev PostToolUse '"tool_name":"Read","agent_id":"sub1"')" waiting
  step "$(ev PostToolUse '"tool_name":"Bash"')" working
  step "$(ev PreToolUse '"tool_name":"AskUserQuestion"')" waiting
  step "$(ev Notification '"notification_type":"permission_prompt"')" waiting
  step "$(ev PostToolUse '"tool_name":"AskUserQuestion"')" working
  step "$(ev Notification '"notification_type":"permission_prompt"')" waiting
  step "$(ev PostToolUseFailure '"tool_name":"Bash"')" working
  step "$(ev PermissionRequest '"tool_name":"Bash","agent_id":"sub2"')" waiting
  step "$(ev PostToolUse '"tool_name":"Bash"')" waiting
  step "$(ev PostToolUse '"tool_name":"Bash","agent_id":"sub2"')" working
  step "$(ev Stop)" ''
  if [ -z "$(state since)" ] && [ -z "$(state wait_agent)" ]; then ok "stop clears all options"; else bad "stop clears all options"; fi
  step "$(ev Notification '"notification_type":"permission_prompt"')" ''
  step "$(ev PreToolUse '"tool_name":"Bash","agent_id":"bg1"')" ''
  step "$(ev PreToolUse '"tool_name":"Bash"')" working
  step "$(ev StopFailure '"error":"rate_limit"')" ''
  step "$(ev UserPromptSubmit '"prompt":"x"')" '' sdk-cli
  step "$(ev UserPromptSubmit '"prompt":"x"')" working
  step "$(ev Notification '"notification_type":"idle_prompt"')" ''
  step "$(ev UserPromptSubmit '"prompt":"x"')" working
  step "$(ev SessionEnd '"reason":"other"')" ''
  step "$(ev UserPromptSubmit '"prompt":"x"')" working
  t set -p -t "$P" @claude_since 1
  step "$(ev UserPromptSubmit '"prompt":"again"')" working
  if [ "$(state since)" -gt 1 ]; then ok "new prompt restarts since"; else bad "new prompt restarts since"; fi
  step "$(ev SessionStart '"source":"startup"')" ''
  t set -p -t "$P" @claude_state working
  out=$(ev Stop | env -u TMUX_PANE TMUX="$SOCK,0,0" "$HOOK"); rc=$?
  if [ "$rc" = 0 ] && [ -z "$out" ] && [ "$(state)" = working ]; then ok "no TMUX_PANE: no-op"; else bad "no TMUX_PANE: no-op"; fi
  out=$(ev Stop | env PATH=/usr/bin:/bin TMUX="$SOCK,0,0" TMUX_PANE="$P" "$HOOK"); rc=$?
  if [ "$rc" = 0 ] && [ -z "$out" ] && [ "$(state)" = working ]; then ok "no tmux on PATH: no-op"; else bad "no tmux on PATH: no-op"; fi
  start=$(python3 -c 'import time; print(time.time())')
  for i in 1 2 3 4 5 6 7 8 9 10; do
    ev UserPromptSubmit '"prompt":"x"' | env TMUX="$SOCK,0,0" TMUX_PANE="$P" "$HOOK"
    ev PostToolUse '"tool_name":"Bash"' | env TMUX="$SOCK,0,0" TMUX_PANE="$P" "$HOOK"
  done
  ms=$(python3 -c "import time; print(int((time.time() - $start) * 1000 / 20))")
  if [ "$ms" -lt 100 ]; then ok "avg $ms ms per call"; else bad "avg $ms ms per call"; fi
  t kill-server
  echo "FAILS=$fails"
  exit "$fails"
  ```

### Gates

Run from `~/dotfiles`.

1. `for f in tmux/session-picker.sh claude/hooks/pane-state.sh; do bash -n "$f" && /bin/bash -n "$f" || echo "BAD $f"; done; bash -n install.sh`
   prints nothing and exits 0.
2. `test -x tmux/session-picker.sh && test -x claude/hooks/pane-state.sh && git ls-files -s claude/hooks/pane-state.sh | grep -q '^100755'`
   exits 0.
3. `LC_ALL=C grep -c "$(printf '\342\200\224')" tmux/session-picker.sh claude/hooks/pane-state.sh install.sh .tmux.conf README.md plans/claude-activity-picker.md`
   prints `:0` for every file.
4. fzf gate, each prints the given exit code:
   `tmux/session-picker.sh --supported; echo $?` -> `0`;
   `env PATH=/usr/bin:/bin tmux/session-picker.sh --supported; echo $?` -> `1`;
   `PATH=$S/spike-fzf/dl/0.72.0:$PATH tmux/session-picker.sh --supported; echo $?` -> `1`;
   `PATH=$S/spike-fzf/dl/0.73.0:$PATH tmux/session-picker.sh --supported; echo $?` -> `0`.
5. `grep -c PICKER_LOG tmux/session-picker.sh` prints `0`.
6. `tmux source-file ~/.tmux.conf && tmux list-keys -T prefix s` exits 0 and
   prints a line containing `display-popup -BE -h "80%" -w "85%"` (tmux 3.8
   normalizes the flags).
7. `jq empty ~/.claude/settings.json` exits 0.
8. `bash $S/hook-test.sh` ends with `FAILS=0`.
9. `PICKER=$HOME/dotfiles/tmux/session-picker.sh bash $S/spike-fzf/harness.sh`
   ends with `FAILS=0` (SKIP lines allowed only for the checks T0 marks as
   log-only).

### Acceptance criteria

- AC1 (hook): Gate 8; the run includes every event of the Shared definitions
  filter, empty stdout, exit 0, `TMUX_PANE` unset is a no-op, avg < 100 ms.
- AC2 (section): harness A checks: two active rows with the working/waiting
  markers and colors, idle pane absent, fillers, last list row on the bottom
  edge, info counter without fillers.
- AC3 (jump): harness B checks: `Enter` on an active row selects that pane and
  window (`display -p`), `→`/`←`/`Ctrl-d` no-ops there.
- AC4 (live): harness C checks: section gone within 3 s after both states are
  unset, cursor kept on the session line, window line, or active row.
- AC5 (tree unchanged): harness D checks (Gate 7 a-f of
  `plans/tmux-session-tree-picker.md`) plus D2b (`→` on a window line lands on
  the session line, as before), E (cursor never on a filler), F (search mode
  filters active rows), G (no leftover processes), I (resize).
- AC6 (stale): harness K checks: a `working` pane whose window printed nothing
  for 5 s is not listed; output in it brings it back; silence hides it again.
- AC7 (gates): Gates 1-7.
- AC8 (live wiring): `readlink ~/.claude/hooks/pane-state.sh` prints
  `$HOME/dotfiles/claude/hooks/pane-state.sh`;
  `jq '[.hooks[][] | select(any(.hooks[]?; .command == "~/.claude/hooks/pane-state.sh"))] | length' ~/.claude/settings.json`
  prints `10`; the plugin's SessionStart/SessionEnd entries
  (`claude-session-track.sh`, `claude-session-cleanup.sh`) and the
  `notify.sh` Stop entry are still present.

### Tasks

Waves: wave 1 = T0, T1, T3, T4 (parallel, disjoint files); wave 2 = T2 (needs
T0) and T5 (needs T1 committed). T0 and T5 change no repo file.

#### T0: harness update (`$S/spike-fzf/harness.sh`, scratchpad, not committed)

Scope: adapt the spike harness so it tests the production script. Edit only
`$S/spike-fzf/harness.sh` (and create `$S/spike-fzf/bin/busy/`).

1. `PICKER=$D/picker.sh` -> `PICKER=${PICKER:-$D/picker.sh}`.
2. Busy fake: `BUSY=$D/bin/busy/2.1.999`, created in `setup()` when missing
   (`mkdir -p "$D/bin/busy" && cp /bin/bash "$BUSY"`). The beta:1 window runs
   `"echo CLAUDE-BETA-PANE; exec $BUSY -c 'while :; do printf .; read -t 1 x; done'"`
   instead of the sleep fake (it prints every second, like a working Claude).
   Add check `S0 busy fake reports 2.1.999` right after setup:
   `t display -p -t beta:1.0 '#{pane_current_command}'` is `2.1.999` on three
   reads 1 s apart.
3. Checks that read `$LOG` (A9, the tick-kinds check near line 193, the state
   dir lookup near line 215): when `grep -q PICKER_LOG "$PICKER"` fails, print
   `SKIP <check name>` instead and do not count it. If the state-dir check can
   be done without the log (diff of `ls -d "${TMPDIR:-/tmp}"/tmp.*` before
   start and after close), do that instead of skipping.
4. Every `@claude_state working` the harness sets on a pane other than
   beta:1.0 (e.g. the alpha row added above in C11) becomes `waiting`: those
   panes run the silent sleep fake, which the stale rule hides.
5. New check `D2b right on a window line -> its session line`, between Gate 7
   b and c: from step b's state (beta expanded, cursor on beta) `keys Down`
   (cursor on `├─ 0`), then `keys Right`, expect the cursor on `▾ beta`; step c
   continues from there unchanged.
6. New checks K, run with the picker open and both states set (any point after
   the C checks restore the section): set `@claude_state working` and
   `@claude_since $(date +%s)` on alpha:1.0 (silent sleep fake; its window has
   printed nothing since setup, wait until it has been silent 6 s).
   - `K1 silent working pane hidden`: polled once a second for 4 s,
     `listrows` never contains `alpha › 1.0`.
   - `K2 output brings it back`: `t send-keys -t alpha:1.0 x` (tty echo is
     window output), then `within 3` the row `alpha › 1.0` is listed.
   - `K3 silence hides it again`: `within 9` the row is gone.
   - Cleanup: `t set -pu -t alpha:1.0 @claude_state`, `@claude_since`.
7. End with `echo "FAILS=$fails"` before the exit.

Task gates: `bash -n $S/spike-fzf/harness.sh`; then
`bash $S/spike-fzf/harness.sh` (against the prototype) prints FAIL lines for
exactly `D2b`, `K1`, `K3` and passes everything else (the prototype lacks the
`→` rule and the stale rule). No em dash in the file.

DoD: harness gates as above; report the FAIL/SKIP list.

#### T1: `claude/hooks/pane-state.sh` (new, mode 755)

Write exactly this file, then `chmod +x`, then save the Hook test block from
Shared definitions to `$S/hook-test.sh`.

```bash
#!/bin/bash
# Claude Code hook: mirrors the turn state of the session in this tmux pane into
# pane options for the `prefix + s` picker (tmux/session-picker.sh):
#   @claude_state       working (mid-turn) or waiting (mid-turn, blocked on the
#                       user: permission prompt or question); unset when idle
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
fields=$(jq -r '.hook_event_name // "", .notification_type // .tool_name // "", .agent_id // ""') || exit 0
{ read -r event; read -r kind; read -r agent; } <<EOF
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
    # A main-agent tool call while idle: a turn that began without a prompt
    elif [ -z "$cur" ] && [ -z "$agent" ]; then
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
  Stop | StopFailure | SessionStart | SessionEnd) clear_state ;;
esac
exit 0
```

Must not: write to stdout, touch any tmux server other than the one in `TMUX`,
read or write files.

Task gates: Gates 1-3 scoped to `claude/hooks/pane-state.sh`
(`bash -n`, `/bin/bash -n`, `test -x`, em dash count `0`); `bash $S/hook-test.sh`
ends with `FAILS=0` (run it twice; the second run proves it cleans up).
Mode check after the commit: `git ls-files -s claude/hooks/pane-state.sh`
starts with `100755`.

DoD: file as above, gates green.

#### T2: `tmux/session-picker.sh` (port the prototype)

Model: sonnet. Start from the spike prototype, which already passes the tree,
section, refresh and search checks; apply exactly these changes.

1. `cp $S/spike-fzf/picker.sh tmux/session-picker.sh` (keeps mode 755).
2. Remove the spike instrumentation: every line containing `PICKER_LOG`
   (in `tick`, `loaded`, `skip_row`, `main`) and the
   `# spike-only instrumentation for harness.sh` comment line above each.
3. Stale rule. In `render()` append `'#{window_activity}'` to the
   `list-panes -F` field list right after `'#{@claude_since}'` (it becomes
   `$15`). In the awk main block replace

   ```awk
        if (($13 == "working" || $13 == "waiting") && claude) {
   ```

   with

   ```awk
        # Esc or a denied prompt ends a turn without a hook event; a working
        # Claude redraws its spinner every second, so a silent window is idle
        busy = $13 == "waiting" || ($13 == "working" && now - $15 <= 5)
        if (busy && claude) {
   ```

4. `→` on a window line keeps its current effect (the tracked reload in the
   old script landed the cursor on the session line). In `toggle()`, right
   after `case "$3" in %*) return 0 ;; esac`, add:

   ```bash
  # right on a window line keeps its old effect: the cursor goes to the session line
  if [ "$1" = right ] && [ -n "$4" ]; then echo "pos($4)"; return; fi
   ```

5. Header comment: the line
   `# collapse and kill on a window line move to the session row (aux) first.`
   becomes
   `# collapse, kill and right on a window line move to the session row (aux).`
   Also add, after the sentence that ends `refreshed every 2 s.`, the line
   `# State: pane options from claude/hooks/pane-state.sh.`

Must not change: colors, glyphs, key hints, popup options, preview, the
`change` binding, the 0.73 gate, anything else in the prototype.

Task gates: Gates 1, 3, 4, 5 scoped to `tmux/session-picker.sh`; Gate 9.

DoD: gates green; `git diff --stat` shows only `tmux/session-picker.sh`.

#### T3: `.tmux.conf` comment and `README.md` rows

- `.tmux.conf:50`: `# tmux's own tree where fzf is missing or older than 0.71`
  -> `# tmux's own tree where fzf is missing or older than 0.73`. Nothing else.
- `README.md:379` (row `prefix` + `s`) becomes exactly:

  ```
  | `prefix` + `s` | Session tree popup (fzf): `→` expand, `←` collapse, `Enter` opens the session's first window or the focused window, `Ctrl+d` kills the session or window; Claude panes mid-turn (working, or waiting on you) are listed live at the bottom, `Enter` jumps to the pane; tmux `choose-tree` when fzf < 0.73 |
  ```

- `README.md`: after the row starting `| \`claude/hooks/notify.sh\``
  (line 263) insert:

  ```
  | `claude/hooks/pane-state.sh` | `~/.claude/hooks/pane-state.sh` | macOS only; Claude Code hook that marks mid-turn panes for the `prefix + s` picker, `install.sh` also wires it into `~/.claude/settings.json` |
  ```

Task gates: Gate 3 for both files; Gate 6. DoD: `git diff --stat` shows 2
files, 3 lines changed in README, 1 in `.tmux.conf`.

#### T4: `install.sh` (macOS Claude block)

In the `if [[ "$OS" == "Darwin" ]]` block that starts with
`echo "Setting up Claude Code notifications..."` (lines 375-399):

1. After line 379 (`ln -sf "$DOTFILES/claude/hooks/notify.sh" ...`) add
   `  ln -sf "$DOTFILES/claude/hooks/pane-state.sh" ~/.claude/hooks/pane-state.sh`.
2. After the `fi` that closes the notify.sh `jq` block (line 387), add a blank
   line and:

   ```bash
  # Turn state for the `prefix + s` picker: one entry per event, added where missing
  pane_state_filter='<the Settings filter from Shared definitions, verbatim>'
  if [[ "$(jq "$pane_state_filter" "$settings")" != "$(jq . "$settings")" ]]; then
    tmp="$(mktemp)"
    jq "$pane_state_filter" "$settings" > "$tmp" && mv "$tmp" "$settings"
  fi
   ```

   The filter keeps its line breaks inside the single quotes.
3. Do not touch the section header, the `preferredNotifChannel` and gopass
   parts, or anything outside this block. Do not run `install.sh`.

Task gates: `bash -n install.sh`; Gate 3 for `install.sh`; the filter is
idempotent and keeps foreign entries:
`f=$(sed -n "/pane_state_filter='/,/end)'/p" install.sh | sed "1s/.*pane_state_filter='//; \$s/'\$//"); jq "$f" ~/.claude/settings.json > $S/s1.json && jq "$f" $S/s1.json > $S/s2.json && cmp $S/s1.json $S/s2.json && jq '[.hooks[][] | select(any(.hooks[]?; .command == "~/.claude/hooks/pane-state.sh"))] | length' $S/s1.json`
prints `10` (reads the live settings, writes only to `$S`).

DoD: gates green; diff limited to the two insertions.

#### T5: live wiring (no repo change; after T1 is committed)

1. `ln -sf ~/dotfiles/claude/hooks/pane-state.sh ~/.claude/hooks/pane-state.sh`.
2. Read `~/.claude/skills/cc-settings/SKILL.md` and follow its procedure:
   `cat ~/.claude/settings.json`, then
   `~/.claude/bin/settings-edit.sh ~/.claude/settings.json '<Settings filter>'`.
   Read the printed diff: only the 10 pane-state entries are added.
3. Verify AC8 and Gate 7.

Must not: edit `~/.claude/settings.json` any other way, touch the plugin's
SessionStart/SessionEnd entries or `~/.claude.json`.

DoD: AC8 and Gate 7 output in the report, plus the settings-edit diff.

### Edge cases

- macOS vs Linux: the hook is wired only on macOS (same block as notify.sh);
  the script itself is portable. Linux servers keep `choose-tree` (distro fzf
  < 0.73).
- Missing tools: no `jq` or `tmux` -> the hook exits 0 silently; `stty`
  failing -> the initial list has no fillers and the first tick adds them.
- Headless `claude -p` inside a pane and background subagents: skipped by
  `CLAUDE_CODE_ENTRYPOINT` and `agent_id`.
- Claude killed or exited without SessionEnd: the command filter drops the
  pane; a pane that is closed takes its options with it.
- Two Claude panes in one window: activity is per window, so a stale
  `working` pane stays listed while its neighbour prints (fail-safe).
- First run: settings without `hooks` or without some event key: the filter
  creates them.
- Dirty worktree: clean at the start (`git status --short` empty).

### Known limitations (reported, not fixed)

- `waiting` after a denied or escaped dialog stays until the next prompt (no
  event, and a dialog is as silent as idle).
- An approved long tool shows `waiting` until it finishes (no event on approval).
- The list height constants follow the current `--style`, footer and
  `--preview-window` options; changing them needs new constants.

### Not doing

- `everything.md`, `plans/tmux-session-tree-picker.md` (historical design).
- Committing the harness or the hook test (session scratchpad only).
- Pane-title or screen-text heuristics (rejected above).
- Linux wiring of the hook; changes to the tmux-assistant-resurrect entries.
- Any other picker behavior, color, key or popup change.
