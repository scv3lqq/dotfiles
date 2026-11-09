# agent-inbox

## Goal

See at a glance which agent panes (Claude Code, Codex) work, which wait for the
user and which finished with a result nobody opened. Two surfaces:

- `prefix + a`: fzf popup with sections "needs you", "working" and a folded
  seen list, a preview of the agent's final text, Enter jumps and marks seen.
- One dim tmux status segment `! N  ● N  ◌ N` (zero counts hidden) and a mark
  on the name of the window holding the result.

Design: https://claude.ai/artifact/5HMLxvwvAzVyLf1H7RgCgG (boards "Inbox popup"
and "tmux bar").

## Current behavior

`claude/hooks/pane-state.sh` mirrors turn state into pane options
(`@claude_state` working|waiting|agents|done). Nothing records whether a result
was opened or what it said. The status bar shows no agent information;
`tmux/session-picker.sh` lists agents only inside its session tree.

## Acceptance criteria

Run from the repo root on `feat/agent-inbox`.

| # | Command | Expected |
|---|---------|----------|
| A1 | `just check` | exit 0 |
| A2 | `python3 -m unittest discover -s codex -p 'test_agent_inbox.py'` | exit 0, at least 18 tests |
| A3 | `/bin/bash -n claude/hooks/pane-state.sh && /bin/bash -n tmux/agent-inbox.sh` | exit 0 |
| A4 | `test -x tmux/agent-inbox.sh` | exit 0 |
| A5 | `git diff --name-only main...feat/agent-inbox \| sort` | exactly the Files list below |
| A6 | `grep -cF 'agent-inbox.sh status' tmux/tmux.conf` | 1 |
| A7 | `grep -cF 'bind a display-popup' tmux/tmux.conf` | 1 |
| A8 | `awk '/^run .*tpm/{r=NR} /agent-inbox\|agent_mark\|status-interval/{l=NR} END{exit !(l<r)}' tmux/tmux.conf` | exit 0 (nothing follows `run tpm`) |
| A9 | Isolated popup drive from T2 definition of done, repeated by the validator | same observations |

Base results (5a7cc32): `just check` exit 0, `/bin/bash -n
claude/hooks/pane-state.sh` exit 0; A2, A3 second half, A4, A6, A7 fail because
the files or lines do not exist yet, A8 fails (no matching line).

Files (A5): `README.md`, `AGENTS.md`, `claude/hooks/pane-state.sh`,
`codex/test_agent_inbox.py`, `plans/agent-inbox.md`, `tmux/agent-inbox.sh`,
`tmux/tmux.conf`.

## Gates

```bash
/bin/bash -n claude/hooks/pane-state.sh
/bin/bash -n tmux/agent-inbox.sh
just check
```

Do not run `tmux source-file` against the live server inside a task: the
orchestrator applies it once after merge.

## Shared definitions

**D1 Pane options** (new, next to `@claude_*`, whose values stay unchanged):

- `@agent_unseen`: `1` when a finished result was not opened; unset otherwise.
- `@agent_failed`: `1` when the last turn ended in StopFailure; unset otherwise.
- `@agent_report`: absolute path of the report file; unset when there is none.

**D2 Window option** `@agent_mark`: a tmux format string, unset when no mark:
`' #[fg=#F07178]!'` (a blocked or failed pane in the window, wins) or
`' #[fg=#E6B450]●'` (a ready pane).

**D3 Report files**: directory
`${XDG_STATE_HOME:-$HOME/.local/state}/agent-inbox`, created with umask 077.
File name `<pane id without %>-<epoch>.txt`. At most 65536 bytes.

**D4 Classes**, first match wins, for a pane whose client is known. Client:
`#{pane_current_command}` equal to `codex` gives tag `cx`; matching
`^[0-9]+\.[0-9]+\.[0-9]+$` or equal to `claude` gives tag `cc`; any other pane
is ignored.

1. `@claude_state` = waiting: `blocked`
2. `@agent_unseen` = 1 and `@agent_failed` = 1: `failed`
3. `@agent_unseen` = 1: `ready`
4. `@claude_state` working or agents and `now - window_activity <= 5`: `working`
5. `@claude_state` = done: `seen`
6. otherwise: `idle`, never shown or counted

Rank for sorting: blocked 0, failed 1, ready 2, working 3, seen 4; inside one
rank `@claude_since` descending.

**D5 Pane list format** for `tmux list-panes -a -F`, tab-separated, in this
order (the test stub returns rows in it):

```
#{session_id} #{window_id} #{pane_id} #{pane_active} #{window_active}
#{session_attached} #{pane_current_command}
#{?#{==:#{pane_title},#{host}},,#{pane_title}} #{pane_current_path}
#{@claude_state} #{@claude_since} #{window_activity} #{@agent_unseen}
#{@agent_failed} #{@claude_agents}
```

Parse with `LC_ALL=C awk -F '\t'`. A pane is **front** when `pane_active` = 1,
`window_active` = 1 and `session_attached` > 0.

**D6 Status segment**, printed on one line by `agent-inbox.sh status`, parts
joined by two spaces, parts with zero count omitted, empty output when all are
zero. N1 = blocked + failed, N2 = ready, N3 = working:

```
#[fg=#F07178,bold]! N1#[nobold]  #[fg=#E6B450,bold]● N2#[nobold]  #[fg=#7A8290]◌ N3
```

**D7 Render row** (`agent-inbox.sh render`), tab-separated, 4 fields:
`session_id`, `pane_id`, `class`, `display`. Header and filler rows have empty
fields 1 and 2 and `up:down` (1-based rows of the nearest selectable row above
and below; when one side has none it repeats the other; when no row is
selectable both are the row's own number) in field 3.

Row order: header `needs you <n>`; blocked, failed, ready rows, or the filler
`nothing to open` when none; header `working <n>`; working rows; then, only
when some pane is `seen`, the filler `show seen <n>` or `hide seen <n>`, and
seen rows after `hide seen`. Seen rows show when the file
`$AGENT_INBOX_STATE/show-seen` exists; an unset `AGENT_INBOX_STATE` means hidden.

Display of an agent row, ANSI 24-bit, fields joined by one space, the title
last so fzf truncates it, not the columns (BWK awk counts bytes):
`<glyph> <age, right-aligned 3> <tag> <project, left-aligned 14> <title><subs>`.

- Glyph and color: blocked `!` and failed `✗` in 240;113;120, ready `●` in
  230;180;80, working `◌` in 122;130;144, seen a space.
- Text color: 191;189;182 for blocked, failed, ready; 122;130;144 for the rest.
- Age from `@claude_since`: `<1m` under 60 s, then `Nm`, `Nh`, `Nd`; `-` when
  not numeric.
- Project: basename of the path, cut to 14 bytes only when pure ASCII.
- Title: strip Claude's glyph prefix as `session-picker.sh:75-79`; empty title
  falls back to the project.
- Subs: ` +N` from `@claude_agents` when greater than 0, else empty.
- Headers and fillers: plain text in 122;130;144.

## Tasks

Wave 1 (parallel, disjoint files): T1, T2, T3, T5. Wave 2: T4.

### T1: record results in the hook

File: `claude/hooks/pane-state.sh`. Depends on nothing. Keep every existing
`@claude_*` transition. Still bash 3.2, never writes stdout, always exits 0.

Edits (quote the old text, line numbers are hints):

1. Header comment: after the `@claude_agents` line (:13) add three comment lines
   describing `@agent_unseen`, `@agent_failed`, `@agent_report` for
   `tmux/agent-inbox.sh`.
2. :32-33: the payload must be read once and reused. Before `fields=` add
   `payload=$(cat) || exit 0`, and feed jq with
   `fields=$(printf '%s' "$payload" | jq -r '...same filter...') || exit 0`.
3. `clear_state` (:45): after its tmux call, add `clear_result` and remove the
   report: read `old=$(tmux display -p -t "$pane" '#{@agent_report}')`, then
   `[ -z "$old" ] || rm -f "$old"`, then `tmux set -pu -t "$pane" @agent_report`.
4. Add before `case "$event" in`:

```bash
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
      jq -r '[(.error // empty | tostring), (.last_assistant_message // empty)] | join("\n\n")' |
      head -c 65536 >"$file"
    if [ -s "$file" ]; then
      tmux set -p -t "$pane" @agent_report "$file"
      [ -z "$old" ] || [ "$old" = "$file" ] || rm -f "$old"
    else
      rm -f "$file"
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
```

5. `UserPromptSubmit)`: after the existing tmux call add
   `[ -n "$agent" ] || clear_result`, keeping the `;;` on the last line.
6. `Stop)` (:108): becomes

```bash
    if [ "${bg:-0}" -gt 0 ]; then await_agents "$bg"
    else
      finish "$now"
      [ -n "$agent" ] || record_result
    fi ;;
```

7. `StopFailure)` (:114): the final branch becomes
   `else finish "$now"; record_result 1; fi ;;`.

Task gates: `/bin/bash -n claude/hooks/pane-state.sh`;
`python3 -m unittest discover -s codex -p 'test_activity.py'`.
Done: both pass, no other line changed.

### T2: popup and status script

File: `tmux/agent-inbox.sh` (new, mode 755, `#!/usr/bin/env bash`, bash 3.2
rules of `.claude/rules/shell-scripts.md`). Read `plans/claude-activity-picker.md`
spike findings first; never use a tracked reload. Self path as in
`session-picker.sh`. Subcommands, dispatched by `$1`:

- `--supported`: exec `session-picker.sh --supported` from the same directory.
- `render`: D7 to stdout. One shared internal function produces classified
  rows per D4 and D5; `render` and `status` both use it. `now` comes from
  `date +%s`.
- `status`: for each pane of class ready or failed that is front (D5):
  `tmux set -pu -t <pane> @agent_unseen \; set -pu -t <pane> @agent_failed`,
  and treat it as seen for the rest of this run. Then per window compute the
  D2 mark. Read current marks with
  `tmux list-windows -a -F '#{window_id}<tab>#{@agent_mark}'` and call
  `tmux set -w -t <id> @agent_mark <value>` or `tmux set -wu -t <id> @agent_mark`
  only when the value differs. Print D6.
- `seen <pane>`: only when `$2` matches `%*`:
  `tmux set -pu -t "$2" @agent_unseen \; set -pu -t "$2" @agent_failed`. Other
  input: no tmux call.
- `open <session_id> <pane>`: empty `$2`: return. Otherwise `seen "$2"`, then
  `tmux select-window -t "$2" \; select-pane -t "$2" \; switch-client -t "$1"`.
- `toggle-seen`: create or remove `$AGENT_INBOX_STATE/show-seen`.
- `skip <field1> <field3>`: same logic as `skip_row`, `session-picker.sh:233-242`.
- `tick`: render to `$AGENT_INBOX_STATE/next`; when it differs from
  `$AGENT_INBOX_STATE/shown`, move it over and print
  `reload-sync(cat "$AGENT_INBOX_STATE/shown")` with single quotes as
  `session-picker.sh:200-201`. Otherwise print nothing.
- `preview <pane> <class>`: empty pane: print nothing. Line 1: the class label
  in its D7 glyph color (blocked `needs your answer`, failed `failed`, ready
  `done`, working `working`, seen `seen`). Line 2 in 122;130;144:
  `#{session_name}:#{window_index}.#{pane_index}  #{pane_current_path}`. Blank
  line. Then for failed, ready, seen with `@agent_report` a readable file inside
  the D3 directory: its content; otherwise the last 40 lines of
  `tmux capture-pane -ep -t <pane>`.
- no argument: main. `export AGENT_INBOX_STATE=$(mktemp -d)` with `trap` cleanup,
  remove D3 files older than 7 days (`find ... -type f -name '*.txt' -mtime +7
  -delete`, skip when the directory is missing), render into `shown`, run fzf on
  it with:
  `--ansi --delimiter '\t' --with-nth 4.. --layout reverse --no-sort
  --info inline-right --prompt '> '`, colors copied from
  `session-picker.sh:309-312`, `--footer 'enter open   ctrl-x seen   tab seen list   esc close'`,
  `--preview "$self preview {2} {3}"`,
  `--preview-window 'right,55%,wrap,<55(down,45%,wrap)'`, and binds:
  `load:unbind(load)+pos(2)`, `every(2):transform($self tick)`,
  `resize:transform($self tick)`, `focus:transform($self skip {1} {3})`,
  `enter:become($self open {1} {2})`,
  `ctrl-x:execute-silent($self seen {2})+transform($self tick)`,
  `tab:execute-silent($self toggle-seen)+transform($self tick)`.
  fzf exit 130 (esc) exits 0.

Task gates: `/bin/bash -n tmux/agent-inbox.sh`; `test -x tmux/agent-inbox.sh`.

Definition of done includes this drive on an isolated server (`S` a scratch
dir, `cp /bin/sleep "$S/codex"`; report BLOCKED if that copy will not run):
`env -u TMUX tmux -L inbox -f /dev/null`, two windows each running
`"$S/codex" 300` in session `a`, plus a third window with a shell to host the
popup command. Set `@claude_state done`, `@claude_since`, `@agent_unseen 1` on
the first and `@claude_state waiting` on the second. Run the script in the third
window with a 100x30 size, `capture-pane -ep`, and observe: the `needs you 2`
header, the blocked row above the ready row, cursor on the blocked row. Down
then Enter: the client target window changes (with no client attached assert
`@agent_unseen` is gone from that pane) and the popup process exits. Kill the
server afterwards.

### T3: tmux config

File: `tmux/tmux.conf`. Keep everything else, every new line before
`run '~/.tmux/plugins/tpm/tpm'`.

1. After the `bind s` block (:53-55), add with a one-line comment:

```
if-shell '~/dotfiles/tmux/agent-inbox.sh --supported' \
  'bind a display-popup -B -E -s "bg=#0B0E14" -w 85% -h 80% "~/dotfiles/tmux/agent-inbox.sh"' \
  'bind a display-message "agent inbox needs fzf 0.73+"'
```

2. After `set -g @tmux-dotbar-bg "#0B0E14"` (:78) add:

```
set -g status-interval 5
set -g @tmux-dotbar-right true
set -g @tmux-dotbar-status-right '#(~/dotfiles/tmux/agent-inbox.sh status)'
set -g @tmux-dotbar-window-status-format ' #W#{E:@agent_mark} '
```

Task gates: the A6, A7, A8 commands. Done: they pass and the diff is only these
lines.

### T4: tests

File: `codex/test_agent_inbox.py` (new, Python 3.11 typed, unittest, auto
discovered). Depends on T1, T2. Fixture per test: temp `HOME`, `XDG_STATE_HOME`
under it, `bin` dir with a python `date` stub printing `2000000000` (NOW),
`PATH` of that dir then `/opt/homebrew/bin:/usr/bin:/bin`, run with `/bin/bash`,
as `codex/test_activity.py:73-85`.

Hook cases use a real server copied from `codex/test_activity.py:213-228`; the
`tmux` wrapper stub prints the value of class attribute-like file `front` for
argv containing `#{pane_active}#{window_active}#{?session_attached,1,0}`
(default `000`) and execs real tmux for the rest. `TMUX_PANE` set.

Inbox cases use a python `tmux` stub: `list-panes` prints the file `rows`,
`list-windows` the file `windows`, `display-message`/`display` a fixed line,
every call appends its argv as JSON to `calls.log`. Rows follow D5.

| Case | Input | Literal expected | Mutation it catches |
|------|-------|------------------|---------------------|
| H1 stop_unseen | Stop, message `final text`, front 000 | `@agent_unseen`=`1`, report file content `final text`, name `<pane digits>-2000000000.txt` | record_result: never set unseen |
| H2 stop_front | Stop, front 111 | `@agent_unseen` unset, `@agent_report` set | drop the 111 branch |
| H3 failure | StopFailure, `error` `rate_limit` | `@agent_failed`=`1`, unseen `1`, report `rate_limit` | StopFailure calls record_result without 1 |
| H4 prompt_clears | Stop then UserPromptSubmit | unseen unset, state `working` | UserPromptSubmit: remove clear_result |
| H5 background | Stop, one subagent in `background_tasks` | state `agents`, unseen unset, no file in D3 | move record_result before the bg check |
| H6 session_end | Stop then SessionEnd reason `other` | report option unset, D3 directory has 0 files | clear_state keeps the report |
| H7 replace | Stop at NOW, then date stub NOW+1, Stop | exactly 1 file in D3, the NOW+1 one | do not remove old |
| H8 empty_message | Stop, no message | unseen `1`, `@agent_report` unset, 0 files | keep empty file |
| R1 order | rows for waiting, failed+unseen, unseen, working activity NOW, working activity NOW-6, done, empty-state codex, command `zsh` with waiting | pane ids in output order: blocked, failed, ready, working; stale working, done, idle, zsh absent; last line starts `\t\t` and strips to `show seen 1` | D4: drop the 5 s check |
| R2 seen_shown | R1 rows, `show-seen` file present | last row is the done pane, previous line strips to `hide seen 1` | ignore show-seen |
| R3 empty_needs | only one working row | row 2 strips to `nothing to open`, field 3 of row 1 `4:4` | omit the filler |
| R4 display | ready row, since NOW-120, path `/x/dotfiles`, command `2.1.0`, title `Fix bar` | stripped display `●  2m cc dotfiles       Fix bar` | swap tag column |
| S1 segment | blocked, failed, ready, working | stdout `#[fg=#F07178,bold]! 2#[nobold]  #[fg=#E6B450,bold]● 1#[nobold]  #[fg=#7A8290]◌ 1` | count failed as ready |
| S2 zero | no agent rows | stdout empty | always print working part |
| S3 front | ready pane front | `set -pu` of `@agent_unseen` in calls, stdout empty | skip front clearing |
| S4 mark_priority | one window with a ready and a blocked pane, no mark | call sets `@agent_mark` to ` #[fg=#F07178]!` | ready wins |
| S5 mark_same | ready pane, window already has the accent mark | no `set -w` call | always set |
| S6 mark_clear | window has a mark, no panes | `set -wu` for it | never unset |
| O1 open | `open '$1' %3` | calls contain `set -pu -t %3 @agent_unseen`, then `select-window -t %3` | open does not mark seen |
| O2 seen_guard | `seen abc` | `calls.log` absent or empty | drop the `%*` guard |

Mutation command: `python3 -m unittest discover -s codex -p 'test_agent_inbox.py'`.
Task gates: that command and `uvx ruff check codex/test_agent_inbox.py`.

### T5: docs

Files: `README.md`, `AGENTS.md`. `AGENTS.md` names no product.

1. `README.md`, table row after `prefix` + `s` (:495), new row:
   ``| `prefix` + `a` | Agent inbox popup (fzf): agents that need you on top, working ones below, seen ones folded (`Tab`), preview of the final text, `Enter` jumps and marks seen, `Ctrl+x` marks seen; needs fzf 0.73+ |``
2. `AGENTS.md` after "(fzf popup; design in `plans/tmux-session-tree-picker.md`)."
   add the sentence in the same bullet, rewrapped under 80 columns:
   "`prefix + a` runs `tmux/agent-inbox.sh` (agent inbox and bar counters; design
   in `plans/agent-inbox.md`)."

Task gates: `grep -cF 'tmux/agent-inbox.sh' AGENTS.md` prints 1;
`grep -cF 'Agent inbox popup' README.md` prints 1; `just check`.

## Seams

| Producer | Consumer | Definition |
|----------|----------|------------|
| T1 | T2 | D1, D3 |
| T2 | T3 | D2, D6, `status` subcommand |
| T1, T2 | T4 | D1 to D7 |

## Edge cases

- Linux: hooks are not installed there, so no state exists: the segment is
  empty and no marks appear. fzf older than 0.73: `prefix + a` shows the message.
- Missing `jq` or `tmux`: the hook exits early as today.
- First run: D3 is created by the first result; `render` needs no state file.
- tmux restart: pane options vanish with the panes, reports are removed after
  7 days; a reused pane id reads only its own `@agent_report`, never a guess.
- Esc or a denied prompt: stale working is dropped by the 5 s activity check.
- Worktree: `.DS_Store` stays untracked and out of every commit.

## Not doing

- Notification changes (`claude/hooks/notify.sh`, coalesced toasts).
- The always-on dock.
- The `partly unverified` label and structured report sections: the preview
  shows the raw final text.
- A "next unread" key: the cursor starts on the most urgent row.
- Changing `tmux/session-picker.sh`, `claude/settings.json`, Codex hook wiring.
- Codex blocked on `request_user_input` and Codex failures: no hook reports them.
- Persisting seen state across tmux restarts.
