# agent-inbox-origin-guard

## Goal

A hook process speaks only for the tmux pane it really runs in. Codex sessions
served by the shared `codex app-server` daemon stop marking an unrelated old
pane as "needs you" in `tmux/agent-inbox.sh`.

## Current behavior

`claude/hooks/pane-state.sh:31` takes `pane=$TMUX_PANE` on trust. The shared
Codex daemon keeps the environment of the pane that first started it, so every
hook of every daemon session writes to that one pane: a Stop sets
`@claude_state=done`, `@agent_unseen=1` and a report file (`record_result`,
`:89-112`), and `tmux/agent-inbox.sh:44` lists the old pane under "needs you".
`claude/hooks/notify.sh:122-136` (`pane_is_origin`) already guards its own pane
use against this for Codex; `pane-state.sh` has no such guard.

Evidence (read-only, 2026-11-10, macOS):

- Daemon: `codex app-server --listen unix://` has parent `codex app-server
  daemon pid-update-loop`, whose parent is pid 1. No pane process is among the
  ancestors of its hooks.
- Claude Code CLI pane: `claude` is a direct child of the pane's `#{pane_pid}`
  (the login zsh). A Claude Code tool shell reports the `claude` process as its
  `$PPID`, so children are spawned without reparenting.
- `codex --no-daemon` panes (three checked): `codex` is a direct child of
  `#{pane_pid}`.
- Panes started as `exec ... codex`: `codex` is `#{pane_pid}` itself, so the
  hook's `$PPID` matches on the first comparison.
- Not caught live: a hook process itself (they exit within milliseconds). A6
  closes that hop after merge.

Both Claude Code and Codex call the same script (`claude/settings.json`,
`~/.codex/hooks.json` through a link), so one unconditional guard covers both
and Claude Code needs no separate scope.

## Acceptance criteria

Run from the repo root on `feat/agent-inbox-origin-guard`.

| # | Command | Expected |
|---|---------|----------|
| A1 | `just check` | exit 0 |
| A2 | `python3 -B -m unittest discover -s codex -p 'test_agent_inbox.py'` | exit 0, 32 tests (29 on base) |
| A3 | `python3 -B -m unittest discover -s codex -p 'test_activity.py'` | exit 0, 28 tests |
| A4 | `/bin/bash -n claude/hooks/pane-state.sh` | exit 0 |
| A5 | `git diff --name-only main...feat/agent-inbox-origin-guard \| sort` | exactly the Files list below |
| A6 | After merge, orchestrator: submit a prompt in a live Claude Code pane and in a `codex --no-daemon` pane, then `tmux show -pv -t <pane> @claude_state` | `working` during the turn, `done` after it |
| A7 | After merge, orchestrator: note `@claude_since` and `@agent_report` of the daemon's origin pane, finish a turn in a daemon Codex session of another pane, read them again | both unchanged |

Base results (393a57c): A1 not rerun here, A2 exit 0 with 29 tests, A3 exit 0
with 28 tests, A4 exit 0.

Files (A5): `claude/hooks/pane-state.sh`, `codex/test_agent_inbox.py`,
`codex/test_activity.py`, `plans/agent-inbox-origin-guard.md`.

## Gates

```bash
/bin/bash -n claude/hooks/pane-state.sh
python3 -B -m unittest discover -s codex -p 'test_agent_inbox.py'
just check
```

## Shared definitions

D1 to D7 of `plans/agent-inbox.md` stay as they are. One addition:

**G1, origin.** A hook process is of pane P when the pid chain that starts at
its `$PPID` and follows `ps -o ppid= -p <pid>` contains `#{pane_pid}` of P
within 64 steps. Any other outcome (chain reaches pid 1 or 0, 64 steps pass,
`tmux display` or `ps` fails, a non-numeric or empty answer, `pane_pid` not
above 1) is "not of P": the hook exits 0 before it reads stdin, sets or unsets
any pane option, or touches the report directory.

## Tasks

One wave, one task.

### T1: origin guard in the hook

Files: `claude/hooks/pane-state.sh`, `codex/test_agent_inbox.py`,
`codex/test_activity.py`. Bash 3.2, never writes stdout, always exits 0. Keep
every existing transition and `record_result` untouched.

1. `claude/hooks/pane-state.sh`: right after `pane=$TMUX_PANE` (:31) and before
   `now=$(date +%s)`, add the G1 guard (about 14 lines), modeled on
   `pane_is_origin` in `claude/hooks/notify.sh:122-136`:

   ```bash
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
   ```

   `ps` is called by bare name (as in `notify.sh`) so the fixtures can stub it.
   stderr is already closed by `exec >/dev/null 2>&1` (:29). No change to the
   header list of options; no other line of the script changes.

2. `codex/test_agent_inbox.py`, how ancestry is faked: a `ps` stub on the
   closed fixture `PATH`, written with the existing `Fixture.stub` helper, same
   contract as the `ps` stub of `NotificationTests` in `codex/test_activity.py`
   (`sys.argv[1:4] == ["-o", "ppid=", "-p"]`, else exit 2). It prints the file
   `<FIXTURE_ROOT>/parent` and exits 1 when that file is absent. The test
   runner is never below the fixture pane, so the hook always asks the stub
   once for the parent of its `$PPID`.
   - `HookTests.setUp`: read the fixture pane's real `#{pane_pid}` from the
     isolated server, write it to `parent` (H1 to H10 then pass unchanged: the
     first answer equals `pane_pid`), install the stub. Add a helper
     `set_parent(text: str | None)` (None removes the file).
   - `HOOK_TMUX`: one more branch in the existing style: when `#{pane_pid}` is
     in the arguments and the file `pane_pid` exists under `FIXTURE_ROOT`,
     print its content when non-empty, exit 1 when it is empty. Otherwise the
     call reaches the real server as today.
   - `test_h11_daemon_origin_stop_ignored`: `set_parent("1")`, Stop with a
     `last_assistant_message`: `options()` has none of `@agent_unseen`,
     `@claude_state`, `@claude_since`, `@agent_report`; `stored() == []`.
   - `test_h12_daemon_origin_prompt_ignored`: a Stop of the pane itself first
     (unseen 1, state done, one report), then `set_parent("1")` and
     UserPromptSubmit: `options()` and `stored()` equal the snapshot taken
     before it (`@agent_unseen` still 1, `@claude_state` still `done`).
   - `test_h13_origin_lookup_failure_is_silent`: subTests, each on a Stop with
     text: `ps` exits 1 (`set_parent(None)`), `ps` prints `abc`, `pane_pid`
     lookup fails (empty `pane_pid` file), `pane_pid` answers `0`. Each: exit
     0 (asserted by `run_script`), empty stdout, `options()` without the four
     options above, `stored() == []`.

3. `codex/test_activity.py`,
   `test_synthetic_hook_lifecycle_renders_each_codex_state` (:210): it runs the
   hook against a real isolated pane with no `ps` stub and would now be
   ignored. After the pane is created, read its `#{pane_pid}` through
   `isolated_tmux` and `self.stub("ps", ...)` printing that pid. Nothing else
   in the file changes (the other classes never run `pane-state.sh`).

Definition of done: Gates pass; A2 to A5 hold; H11 fails on the base hook
and H12 fail and H1 to H10 pass with the guard lines removed (run once with
the guard commented out in the working copy, restore it, say so in the report).

## Seams

| Producer | Consumer | Definition |
|----------|----------|------------|
| T1 hook | `tmux/agent-inbox.sh`, `tmux/session-picker.sh` | D1 unchanged: fewer writers, same options |
| T1 hook | T1 tests | G1 |

## Edge cases

- macOS vs Linux `ps`: `ps -o ppid= -p <pid>` is POSIX and prints the same on
  BSD and procps, padded with spaces (stripped). Hooks are not installed on the
  Linux servers anyway.
- Missing tools: `jq` or `tmux` missing exits early as today (:28); `ps`
  missing or failing is "not of P": silent exit 0, no state. Sandboxes that
  hide the process table lose pane state rather than misplace it.
- `/bin/sh -c 'codex ...'` panes and `exec` launchers: the wrapper or the
  agent is `pane_pid`, the walk reaches it in one or two steps.
- Nested tmux or a pane id reused after the daemon's origin pane closed:
  `pane_pid` of the reused pane is not an ancestor of the daemon: ignored.
- Cost: one `tmux display` and one to three `ps` calls per hook event, a few
  milliseconds; PreToolUse and PostToolUse run it on every tool call.
- Dirty worktree: `.codex/config.toml`, `codex/check.py` and the untracked
  harness files belong to another session: never staged, edited or stashed.
  Commits use explicit pathspecs.
- First run: no state to migrate. A stale `@agent_unseen` already on the
  daemon's origin pane stays until that pane is opened from the inbox or its
  own session runs a turn.

## Not doing

- Any change to `tmux/agent-inbox.sh`, `tmux/session-picker.sh`,
  `claude/hooks/notify.sh`, `claude/settings.json` or Codex hook wiring.
- Mapping a daemon session to its real pane: daemon sessions stay out of the
  inbox and the picker until restarted with `--no-daemon`.
- Panes whose codex runs under `/bin/sh -c` (`pane_current_command` is `bash`)
  being skipped by `tmux/agent-inbox.sh:57-59`: a separate defect.
- Clearing state the daemon already wrote to its origin pane.
- README or `AGENTS.md` edits: no command, path or convention changes.
