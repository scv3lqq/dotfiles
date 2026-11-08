# Codex terminal origin isolation

## Goal and current behavior

Base: `61e21cc`. Shared Codex app-server workers inherit the daemon startup
TMUX_PANE and PWD rather than each TUI client environment. Live inspection found
many codex panes without @claude_state and only the daemon origin pane marked
working. The picker requires hook state, so these clients disappear from its
assistant section. Notification tmux location similarly points to the daemon pane.

Official evidence: https://github.com/openai/codex/blob/main/codex-rs/app-server-daemon/README.md
states that shared clients inherit the daemon environment without per-client
isolation. https://github.com/openai/codex/blob/main/codex-rs/tui/src/cli.rs
defines --no-daemon to force embedded execution even while a daemon exists.
startup_orchestration.rs rejects combining --no-daemon with --remote.
Disabling daemon_auto_start alone still permits attachment to an existing daemon.

## Constraints and shared definitions

Work on main as explicitly requested by the user, overriding the normal feature
branch cycle. The previous feature branch was merged into main. Preserve all
unrelated dirty files and the recovery stash. No agent may stage unrelated files.
Read .claude/rules/tmux.md and .claude/rules/shell-scripts.md explicitly.
Keep existing picker IDs, navigation, freshness thresholds and Claude behavior.
Do not interrupt or restart running clients, mutate private Codex configuration,
read transcript contents, install tools or stop the daemon.

## Acceptance criteria

1. New shell codex calls add --no-daemon while preserving each original argument,
including resume/fork, spaces and empty arguments. Explicit --remote and
--remote=ADDR calls pass through unchanged. Stop option scanning at --.
2. A live codex pane with empty hook state appears in the assistant section with
an explicit neutral open status, its actual session/pane target and Codex label.
It must not claim working/waiting/done. Plain shells remain excluded.
3. Existing Claude lifecycle, stale-state guards, completion ordering, search,
notification identity, visibility and click-focus regressions remain green.
4. Installed Codex accepts the wrapper flag for normal/resume/fork CLI parsing;
no network or API call is required. Linked zsh and picker source remain correct.
5. just check, Bash syntax checks, scoped ruff/mypy and git diff --check pass.

## Gates

- just check
- /bin/bash -n tmux/session-picker.sh claude/hooks/pane-state.sh claude/hooks/notify.sh
- uvx ruff check codex/test_launch.py codex/test_activity.py
- uvx mypy --strict codex/test_launch.py codex/test_activity.py
- git diff --check

Baseline: just check PASS: 67 tests and 4 plan-edit tests. Shell syntax is included
for zsh. Additional new regression cases must demonstrate RED before source edits.
Save command output and exit codes privately; full gates run serially.

## Tasks

### T0: Regression tests first

Ownership: codex/test_launch.py and codex/test_activity.py only.
Create unittest launch tests that source zsh/aliases.zsh using zsh -f and execute
codex with a fake executable recording JSON argv. Expected argv literals: normal
[--no-daemon,--yolo], resume [--no-daemon,resume,fixture-session], fork similarly;
spaces and empty strings must survive. Explicit remote forms unchanged, and --
ends flag detection. A fake binary needs no real credentials or network.
Add picker tests for codex with empty hook state: target %7, Codex label, visible
open status. Guard shell with empty state excluded, stale working codex excluded,
expired done codex excluded. Search retains neutral row without separator.
Gates: python3 -B -m unittest discover -s codex -p test_launch.py and equivalent
test_activity.py; uvx ruff check and uvx mypy --strict on the owned files.
Record RED against unchanged source, then stop. Do not commit red tests.
Named mutations on a scratch copy: remove wrapper --no-daemon; remove picker
empty-state fallback. Each must fail its corresponding regression suite.

### T1: Isolated interactive launches

Ownership: zsh/aliases.zsh only. Depends on T0 RED.
Add codex() shell function with one local argument variable. Iterate "$@" until
--. For exact --remote or --remote=* immediately call command codex "$@" and
return its exit code. Otherwise command codex --no-daemon "$@". Preserve all
aliases. Add a brief English comment explaining tmux hook environment isolation.
No wrapper installation or alias recursion. No shell global mutable state.
Gates: zsh -n zsh/aliases.zsh; launch unittest suite.

### T2: Open clients without hook state

Ownership: tmux/session-picker.sh only. Depends on T0 RED, independent of T1.
In render, collect codex rows whose state field is empty alongside busy rows;
set their internal state to open. Render open rows with the existing foreground
grey color and a plain neutral circle, and display open in the age column.
Actual state-bearing working/waiting/agents/done behavior stays unchanged.
Do not use window activity to infer work for empty state. Preserve Bash 3.2,
row targets, sort, reload and navigation. The row title remains Codex plus its
existing title/path fallback. No new icons in private Unicode ranges.
Gates: /bin/bash -n tmux/session-picker.sh; activity unittest suite.

## Seams

| Producer | Consumer | Contract |
| --- | --- | --- |
| T0 launch fixtures | T1 shell | Exact argv and exit status preservation |
| Existing hooks and T0 pane fixtures | T2 picker | Existing 15 TSV fields; empty Codex state means open only |

## Edge cases

macOS/Linux: zsh wrapper is portable; no desktop notification behavior change.
Missing Codex: shell preserves command-not-found failure. Explicit remote clients
keep their endpoint. Dirty worktree remains out of task commits. First-run Codex
without hook state is visible as open. Existing daemon clients cannot be migrated
without reconnecting; tell the user to resume after their current work completes.
This is a documented runtime limitation, not evidence that old hooks are repaired.

## Not doing

No daemon protocol changes, heuristic session mapping, DB/transcript scanning,
private hook/config edits, active-session restarts, new notification titles or
notification suppression policy, resurrect plugin edits, documentation rewrites.

## Notification origin hardening amendment

A no-daemon launch fixes future hook environments, but existing daemon hooks
continue supplying the daemon TMUX_PANE. Protect current notification attribution
without guessing a pane from cwd. Preserve project from payload cwd; tmux location,
click target, visibility suppression and pane group require proven origin.

Additional acceptance criterion 6: a Codex hook process whose parent ancestry does
not reach the supplied pane shell PID emits subtitle demo (no tmux location),
group codex-nopane and Ghostty activation rather than an execute command; it is
not suppressed merely because the inherited wrong pane is visible. Embedded Codex
with proven ancestry preserves subtitle demo plus its actual tmux location, pane
group, visibility and click-focus behavior. Claude behavior is unchanged.

### T3: Notification regression tests first

Ownership: codex/test_activity.py only; depends on T0-T2 green commit.
Extend fake tmux display-message for #{pane_pid} to return literal 123. Stub ps so
its -o ppid= output returns 123 normally and 1 when FIXTURE_DAEMON_ORIGIN=1.
Existing notification cases then represent proven embedded ancestry. Add explicit
daemon tests: absent ancestry yields subtitle demo, group codex-nopane, -activate
com.mitchellh.ghostty, no -execute. With FIXTURE_VISIBLE=1 the alert still fires
because wrong daemon origin must not suppress another client. Preserve existing
Claude cases and assert exact embedded subtitle demo plus fixture:2. Add a failing
ps case that safely produces the same unbound alert (no proof, no pane trust).
Gates: activity unittest suite (new daemon cases RED before T4), scoped ruff check
and mypy --strict. Save RED privately, do not commit red tests.
Named mutation: remove Codex ancestry rejection; daemon tests must fail.

### T4: Prove notification pane ownership

Ownership: claude/hooks/notify.sh only; depends on T3 RED.
Add function pane_is_origin: read pane shell PID with tmux display-message -p -t
"$pane" '#{pane_pid}'. Reject empty/nonnumeric PID and PID <=1. Starting at $PPID,
walk parent PIDs with ps -o ppid= -p "$pid", strip whitespace via Bash parameter
replacement, reject empty/nonnumeric results. Compare to shell PID before each
parent query. Return success only upon exact ancestor match. Stop at PID <=1 or
64 iterations, returning failure; missing tools/failed commands also fail closed.
Within existing tmux detection, Codex uses tmux context only if pane_is_origin;
on failed proof clear pane so group uses nopane and existing -activate fallback.
Claude skips this additional proof and retains behavior. Keep --focus handling,
stdout silence, always-zero exit, Linux no-op and Bash 3.2 compatibility.
Gates: /bin/bash -n claude/hooks/notify.sh and activity unittest suite.

Additional seam: T3 fake ancestry models pane shell PID 123; T4 consumes only
standard tmux pane_pid and ps parent PID, never session database heuristics.
The existing full Gates already cover these files. Existing running sessions
still require resume for accurate working/waiting hooks; neutral open visibility
and notification-origin protection apply through source symlinks immediately.
