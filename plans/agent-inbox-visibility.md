# agent-inbox-visibility

Draft. Target path in the repo: `plans/agent-inbox-visibility.md`. Base: `main`
after `feat/agent-inbox-origin-guard` (da03dc4) is merged; branch
`feat/agent-inbox-visibility`.

## Goal

`tmux/agent-inbox.sh` stops hiding running agents: a Codex or Claude Code
process started through a wrapper shell is recognized by the process tree, and
a Codex pane that has no hook state at all (served by the shared
`codex app-server`) shows as working while its window produces output.

## Current behavior

- `tmux/agent-inbox.sh:56-58` derives the client only from
  `#{pane_current_command}`: `codex` gives `cx`, a version string or `claude`
  gives `cc`, everything else hits `else next`. A Codex started as
  `/bin/sh -c "codex ..."` reports `bash` or `sh` and is dropped before
  `classify` runs, even with `@claude_state=done` and `@agent_unseen=1`: the
  unread result never reaches "needs you".
- `tmux/agent-inbox.sh:40-49` (`classify`): rule 4 (`:46`) needs
  `@claude_state` working or agents and `now - window_activity <= 5`
  (`window_activity` is column 12 of the D5 list, `:28`; the 5 is an inline
  literal). With an empty state every rule falls through to `return ""` (`:48`)
  and `:66` drops the row. Codex TUIs started without `--no-daemon` run their
  hooks inside the daemon, guard G1 ignores them, so these panes never get any
  `@claude_*` option.
- `tmux/agent-inbox.sh:180` (`status`) and `:91` (`render`) both read
  `panes()`, so both inherit the two gaps. `status` runs every 5 s
  (`tmux/tmux.conf:84,86`), `render` every 2 s while the popup is open
  (`tick`, `:258`).

Evidence (read-only, 2026-11-10, macOS, tmux 3.8):

- `pane_current_command` over all panes: 43 `codex`, 8 `zsh`, 5 `bash`, 1
  `nvim`, 1 `2.1.319`. All 5 `bash` panes (`cfo-central`, `cfo-f00`, `cfo-f02`,
  `cfo-f03`, `cfo-f04`) have `#{pane_pid}` = `sh` with `codex` as its direct
  child (depth 1). `%283` (`cfo-f04`) carries `done` and `@agent_unseen=1`.
- The Claude Code CLI pane: `pane_current_command` is `2.1.319`, while `ps`
  reports comm `claude` as a direct child of the pane's login zsh.
- `ps -A -o pid=,ppid=,comm=` on macOS prints comm as a full path that may
  contain spaces (`~/Library/Application Support/.../MacOS/claude`,
  `npm exec firecrawl-mcp`); look-alikes exist (`codex-code-mode-host`, 21
  processes). The daemon's own `codex` processes hang below pid 1, not below a
  pane. 1455 lines, 0.18 s wall for one call.
- State by activity at one instant: 23 `codex` panes stateless and quiet, 5
  stateless and active, 13 `done` and quiet, 2 `working` and active. Idle Codex
  TUIs do not refresh `window_activity`.
- `%5`: `@claude_state=working`, `@claude_since` 30 min old, window active.
  `%26`: no options, window active.

## Acceptance criteria

Run from the repo root on `feat/agent-inbox-visibility`.

| # | Command | Expected |
|---|---------|----------|
| A1 | `just check` | exit 0 |
| A2 | `python3 -B -m unittest discover -s codex -p 'test_agent_inbox.py'` | exit 0, 39 tests (32 on base) |
| A3 | `python3 -B -m unittest discover -s codex -p 'test_activity.py'` | exit 0, 28 tests |
| A4 | `/bin/bash -n tmux/agent-inbox.sh` | exit 0 |
| A5 | `git diff --name-only main...feat/agent-inbox-visibility \| sort` | exactly the Files list below |
| A6 | `grep -c 'ps -A' tmux/agent-inbox.sh` | `1`: a single `ps` call site, inside `panes()` |
| A7 | `git diff main...feat/agent-inbox-visibility -- claude/hooks tmux/tmux.conf tmux/session-picker.sh \| wc -l` | `0` |
| A8 | After merge, orchestrator: the Post-merge live checks below | each as stated there |

Base results to record before T1 starts: A2 exit 0 with 32 tests, A3 exit 0
with 28 tests, A4 exit 0.

Files (A5): `tmux/agent-inbox.sh`, `codex/test_agent_inbox.py`,
`plans/agent-inbox-visibility.md`.

## Gates

```bash
/bin/bash -n tmux/agent-inbox.sh
python3 -B -m unittest discover -s codex -p 'test_agent_inbox.py'
just check
```

## Shared definitions

D1 to D3, D6, D7 of `plans/agent-inbox.md` and G1 of
`plans/agent-inbox-origin-guard.md` stay as they are. D4 and D5 are amended
here; `plans/agent-inbox.md` itself is not edited.

**V1, client by process tree (amends the client part of D4).** The client of a
pane is, first match wins:

1. `pane_current_command` equal to `codex`: `cx`; matching
   `^[0-9]+\.[0-9]+\.[0-9]+$` or equal to `claude`: `cc` (today's rule,
   unchanged and still first).
2. Otherwise the tag of the nearest agent process at or below `#{pane_pid}`,
   at most 4 parent hops away. An agent process is a line of the snapshot whose
   comm, after everything up to the last `/` is removed, is exactly `codex`
   (`cx`) or exactly `claude` (`cc`). On equal distance `cc` wins (only so the
   result does not depend on awk's `for in` order).
3. Otherwise the pane is ignored, as today.

The snapshot is one `ps -A -o pid=,ppid=,comm= 2>/dev/null` per `panes()` call.
Each line is `<pid> <ppid> <comm...>` with leading blanks and blanks inside
comm allowed; a line whose first two fields are not numeric is skipped. When
`ps` is missing, fails or prints nothing, no pane matches step 2 and the result
is exactly today's command filter.

**V2, stateless fallback (amends rule 4 of D4).** Rule 4 becomes: `working`
when `now - window_activity <= 5` (same column, same literal 5, same numeric
check on `window_activity`) and either `@claude_state` is working or agents,
or `@claude_state` is empty and the client is `cx`. Rules 1 to 3, 5 and 6 and
their order are unchanged, so a stateless pane can never become blocked,
failed, ready or seen through V2, and a stateless quiet pane stays idle
(hidden, not counted). Such a row has no `@claude_since`: the age column shows
`-` through the existing `age()` (`:107`) and it sorts last among working rows
(`sec` = 0). `status` counts it in N3 with no extra code: it reads the class
column of `panes()`.

V2 is `cx` only. Reason: every stateless Codex pane seen live is quiet when
idle, while `claude/skills/tmux-cleanup/SKILL.md:3` records that
`window_activity` is always fresh for Claude panes; Claude Code panes always
run their own hooks, so an empty state there really is idle and a fallback
would pin every fresh Claude session to working.

**V3, D5 column 16.** `#{pane_pid}` is appended as the last column of the
`tmux list-panes -a -F` format. Columns 1 to 15 keep their positions.

## Tasks

One wave, one task (about 25 changed lines of shell, about 75 of tests).

### T1: process tree detection and stateless fallback

Files: `tmux/agent-inbox.sh`, `codex/test_agent_inbox.py`. Bash 3.2, BWK awk
under `LC_ALL=C`, no gawk extensions. Only `panes()` and the header comment
change in the script: `render`, `status`, `seen`, `open_target`, `tick`,
`preview`, `main` and the output format of `panes()` stay byte for byte.

1. `tmux/agent-inbox.sh`, `panes()` (`:24-83`):
   - Feed awk from one group, the snapshot first, then a marker line, then the
     pane rows (the `echo windows` pattern of `status`, `:179-183`):

     ```bash
     {
       # One snapshot per call: `status` runs every 5 s. A failed ps leaves
       # the tree empty, which is the plain command filter
       ps -A -o pid=,ppid=,comm= 2>/dev/null
       echo panes
       tmux list-panes -a -F "$(printf '%s\t' ... '#{@claude_agents}' '#{pane_pid}')"
     } | LC_ALL=C awk -F '\t' ...
     ```

     `ps` by bare name so the fixture can stub it. A snapshot line never equals
     `panes` (it starts with a pid) and never contains a tab-split layout that
     matters: it is parsed from `$0`.
   - awk, before the row block:

     ```awk
     !rows && $0 == "panes" { rows = 1; resolve(); next }
     !rows {
       if (split($0, f, " ") < 3 || f[1] !~ /^[0-9]+$/ || f[2] !~ /^[0-9]+$/) next
       c = $0
       sub(/^[ \t]*[0-9]+[ \t]+[0-9]+[ \t]+/, "", c)
       sub(/.*\//, "", c)
       par[f[1]] = f[2]
       if (c == "codex") kind[f[1]] = "cx"
       else if (c == "claude") kind[f[1]] = "cc"
       next
     }
     ```

     and the function (names must not collide with the existing arrays `pid`,
     `sid`, `wid`, `kls`, `cl`, `tg` or the counter `n`):

     ```awk
     # Every process up to 4 hops above an agent learns the nearest agent's tag
     function resolve(   p, q, d) {
       for (p in kind) {
         q = p
         for (d = 0; d <= 4 && q + 0 > 1; d++) {
           if (!(q in near) || d < near[q] || (d == near[q] && kind[p] == "cc")) { near[q] = d; via[q] = kind[p] }
           if (!(q in par)) break
           q = par[q]
         }
       }
     }
     ```

     The walk goes up from each agent process (about 75 live), not down from
     each pane: no child index, no recursion, a few hundred steps in total.
   - Row block (`:56-58`): insert one branch before `else next`:
     `else if ($16 in via) client = via[$16]`.
   - `classify` rule 4 (`:46`): extend the state test to
     `(state == "working" || state == "agents" || (state == "" && client == "cx"))`
     and extend the comment above it with one line on why: daemon-served Codex
     panes have no hook state, output is their only signal. `client` is
     already a global set before `classify` is called (`:56-60`).
   - Header comment (`:19-23`) and the file header: mention the process
     snapshot and that a stateless Codex pane is working while its window is
     active. No em dash.

2. `codex/test_agent_inbox.py`, fixtures:
   - `COLUMNS` (`:32-38`): append `"#{pane_pid}"`. `Pane`: new field
     `pid: int = 0`, appended by `line()` as the 16th field (0 is never in the
     tree: the walk stops at pids not above 1).
   - New stub `INBOX_PS`, written with `Fixture.stub("ps", ...)` in
     `InboxTests.setUp` (the closed `PATH` otherwise reaches the real
     `/bin/ps` and the live process table). Contract, in the style of
     `HOOK_PS`: append `json.dumps(sys.argv[1:])` to `<FIXTURE_ROOT>/ps.log`
     (not `calls.log`: `test_o2_seen_guard` asserts that one empty); exit 2
     unless `sys.argv[1:] == ["-A", "-o", "pid=,ppid=,comm="]`; exit 1 when
     the file `<FIXTURE_ROOT>/procs` is absent; else print its content.
     `setUp` writes an empty `procs`, so every existing case runs with an
     empty tree.
   - Helper `procs(*rows: tuple[int, int, str] | None)`: writes
     `f"{pid:>5} {ppid:>5} {comm}\n"` per row (BSD padding); a single `None`
     removes the file (`ps` fails).
   - `mixed()` (`:121-132`): `%7` becomes `Pane("%7", state="")` (quiet). Its
     old form, stateless and active, is exactly V2 now and would turn
     `test_r1_order` and `test_r2_seen_shown` red for the right reason; the
     active case moves to `test_v2`.
   - `test_r1_order`: no edit beyond what `COLUMNS` brings.

3. `codex/test_agent_inbox.py`, new cases in `InboxTests`:
   - `test_v1_wrapped_codex_with_state_listed`: pane `%1`, `command="bash"`,
     `state="done"`, `unseen="1"`, `pid=500`; procs `(500, 1, "sh")`,
     `(501, 500, "/opt/homebrew/bin/codex")`. `render`: one agent row, pane
     `%1`, class `ready`, display contains ` cx `. Second subTest: comm
     `/Users/x/Library/Application Support/Claude/claude` (blanks in the path)
     gives ` cc `.
   - `test_v2_stateless_active_is_working`: `Pane("%1", state="",
     activity=NOW)` (command `codex`): class `working`, display starts with
     `◌   - cx`. SubTest for the edge `activity=NOW - 5` (still working).
   - `test_v3_stateless_quiet_is_hidden`: subTests, each with no agent row in
     `render` and empty `status`: `codex` pane with `activity=NOW - 6`;
     `command="claude"` pane with `state=""`, `activity=NOW` (V2 is `cx`
     only); wrapped `bash` pane with a `codex` child, stateless, quiet.
   - `test_v4_shell_without_agent_not_listed`: `Pane("%1", command="zsh",
     state="waiting", activity=NOW, pid=500)` next to `Pane("%2",
     state="working", activity=NOW, pid=600)` in the same window; procs
     `(500, 1, "-zsh")`, `(501, 500, "nvim")`,
     `(502, 500, "/x/bin/codex-code-mode-host")`, `(600, 1, "codex")`. Only
     `%2` is listed. SubTest: a `codex` 5 hops below pane 500 (chain of 5
     `sh`) does not list `%1` either; at 4 hops it does.
   - `test_v5_status_counts_fallback`: a stateless active `codex` pane, a
     stateless active wrapped pane (`bash`, `codex` child) and a
     `state="working"`, `activity=NOW` pane: `status` prints
     `#[fg=#7A8290]◌ 3`, `mark_calls()` is empty, and `ps.log` holds exactly
     one line (the single snapshot per `status`).
   - `test_v6_ps_failure_falls_back`: `procs(None)`; panes: `%1` `codex`
     `state="working"` `activity=NOW`, `%2` `bash` `state="done"`
     `unseen="1"` `pid=500`. `render` exits 0 (asserted by `run_script`) and
     lists only `%1` as `working`. SubTest with `procs()` empty but present:
     same result.

4. `codex/test_agent_inbox.py`, origin guard hardening (review of `da03dc4`;
   the hook file itself does not change, A7). The `ps` stub of the hook cases
   gave every pid the same unpadded answer, so neither a walk of more than one
   step nor the whitespace strip `pid=${pid//[[:space:]]/}` of
   `claude/hooks/pane-state.sh` was exercised:
   - `HOOK_PS` is strictly pid-keyed: it reads the JSON object
     `<FIXTURE_ROOT>/chain` (pid to parent pid, both strings), prints the
     answer right-aligned with `.rjust(8)` like BSD `ps`, and exits 1 for a pid
     the chain does not name or while the file is absent. The argv contract
     stays (exit 2 unless `-o ppid= -p <pid>`). The file `parent` goes away.
   - `HookTests.set_chain(*answers: str)`: the runner's own pid
     (`os.getpid()`, which is the hook's `$PPID` because the test process
     starts the hook) maps to `answers[0]`, that one to `answers[1]` and so
     on. `set_parent(text)` keeps its meaning for the first step (it is
     `set_chain(text)`; `None` removes the file, so every lookup fails).
     `setUp` keeps the pane's own pid as `self.origin`, and `test_h13` takes
     `own` from there instead of the `parent` file.
   - New `test_h14_origin_walk_three_hops`: `set_chain("41001", "41002",
     self.origin)`, then a `Stop` is recorded (`@agent_unseen` is `1`).

Definition of done: Gates pass; A2 to A7 hold; `test_v1`, `test_v2` and
`test_v5` fail against the base `tmux/agent-inbox.sh` with the new fixtures
(no stash in the shared checkout: write the base script to the scratch dir
with `git show main:tmux/agent-inbox.sh`, point `INBOX` at it for that one
run, restore, and say so in the report); each of two mutants of the hook
makes a hook test fail: the line `pid=${pid//[[:space:]]/}` removed, and
`ps -o ppid= -p "$pid"` replaced by `ps -o ppid= -p "$PPID"`. Run them on
scratch copies of the hook with `HOOK` pointed at them, never on the working
tree file.

## Seams

| Producer | Consumer | Definition |
|----------|----------|------------|
| `panes()` | `render`, `status` | 10-field row unchanged; more rows, class `working` with empty `since` now possible |
| `tmux list-panes` format | T1 tests (`COLUMNS`) | D5 + V3 |
| `ps` snapshot | T1 tests (`INBOX_PS`) | V1 |
| `claude/hooks/pane-state.sh` | `panes()` | D1, G1 unchanged; V2 reads only the absence of `@claude_state` |

## Stale foreign state (pane `%5`)

Decision: no new rule; a one-time manual cleanup in the post-merge steps.

Reasoning. Rule 4 of D4 already gates `working` on `window_activity`
(`:46`): a stale `working` on a quiet window is idle and hidden, which
`mixed()` row `%5` (`state="working"`, `activity=NOW - 6`) has been pinning
since the first plan. While the window is active, `%5` shows as working, and
that is the same answer V2 gives for any stateless Codex pane, so the stale
value cannot produce a wrong class: `working` never turns into blocked, ready
or failed without a hook event, and G1 now stops foreign events. What stays
wrong is cosmetic: the age column and `tmux/session-picker.sh` read a
`@claude_since` that no longer means anything. A rule that tells "state whose
own hooks never fire" from live state needs the pane-to-daemon-session mapping
that is out of scope; an age cutoff would also hide real long turns. The
cleanup is safe both ways: if the pane's hooks are alive after all, the next
event rewrites the state.

## Edge cases

- macOS vs Linux `ps`: `-A` with `-o pid=,ppid=,comm=` is POSIX and accepted
  by BSD `ps` and procps alike (`-ax` is BSD syntax that procps only tolerates).
  macOS prints comm as a full path, procps as a bare name cut to 15 bytes:
  `codex` and `claude` survive both, the basename strip is a no-op on Linux.
  BusyBox `ps` rejects the options: fallback. Zombie lines (`(codex)`) do not
  match.
- Linux servers: hooks are not installed there, so until now the segment was
  always empty. With V2 an active Codex pane there shows `◌ N`. Intended.
- Missing tools: no `ps`, or a sandbox that hides the process table: empty
  tree, today's command filter, no error text (`2>/dev/null`), exit status of
  the pipeline unchanged (awk is the last command).
- awk variants: BWK awk with `LC_ALL=C` is the target; the added code uses
  only `split`, `sub`, `in` and POSIX bracket-free regexes, no `gensub`, no
  `length(array)`, no `\s`. `split($0, f, " ")` trims leading blanks in every
  awk even though `FS` is a tab.
- Locale: with no UTF-8 locale in the caller's environment tmux 3.8 prints
  the tabs of the list format as `_`, so no row parses (seen while checking the
  sketch from a bare shell; with `LC_ALL=en_US.UTF-8` the sketch resolved all
  5 `bash` panes to `cx`, the `2.1.319` pane to `cc`, 8 `zsh` and 1 `nvim` to
  none). Existing behavior, unchanged here; run the live checks from a pane.
- Agent inside an agent: a Claude Code pane whose tool shell runs `codex exec`
  keeps `cc` (step 1 of V1 wins); a shell pane where both sit at different
  depths takes the nearer one.
- nvim or another TUI hosting an agent in a terminal buffer, at most 4 hops
  down: treated as an agent pane. It shows only with state or, for Codex,
  while the window is active.
- Two agent panes in one window share `window_activity` (tmux has no per-pane
  activity time in D5): output of either makes every stateless Codex pane and
  every `working` pane of that window show as working. Same imprecision rule 4
  already has; a plain shell pane in that window still never shows (V1).
- Typing in a stateless Codex pane echoes into the window: it shows as working
  while the user types and for 5 s after. Accepted: the user is looking at it.
- A daemon-served pane that still carries old state (`done` from an earlier
  `--no-daemon` run in the same pane) is not stateless: V2 does not apply and
  it stays `seen`. Only restarting that session or unsetting the options
  changes it; not solved here.
- Performance: one `ps` (0.18 s wall, 1455 lines on the live machine) per
  `status` (every 5 s) and per `render` (every 2 s with the popup open). No
  `ps` per pane, none in `seen`, `open`, `skip`, `preview`. The awk walk is
  bounded by agent processes times 5.
- Dirty worktree: `.codex/config.toml`, `README.md`, `codex/check.py`,
  `codex/setup.py` and the untracked harness files belong to another session:
  never staged, edited or stashed. Commits use explicit pathspecs.
- First run: nothing to migrate. Right after merge up to 5 more `◌` rows and a
  larger N3 appear at once (5 stateless active Codex panes at survey time).

## Not doing

- Resolving the real pane of a daemon session from the hook payload.
- Any change to `claude/hooks/pane-state.sh`, `claude/hooks/notify.sh`,
  notifications, key bindings, `tmux/tmux.conf`, `tmux/session-picker.sh`
  (it keeps its own `pane_current_command` filter, `:62`).
- ready, blocked, failed or a report preview for stateless panes: without
  hooks there is no end-of-turn signal.
- A fallback for stateless Claude Code panes (see V2).
- An automatic rule for stale foreign state; restarting user sessions.
- Edits to `plans/agent-inbox.md`, `README.md`, `AGENTS.md`: no command, path
  or convention changes.

## Post-merge live checks

Orchestrator, on the live server, after `main` holds the change. Helper:

```bash
~/dotfiles/tmux/agent-inbox.sh render | perl -pe 's/\e\[[0-9;]*m//g' | cut -f2-4
```

1. `%26`: while that Codex is producing output, the helper shows
   a row `%26  working  ◌   - cx ...`; 6 s after it goes quiet the row is gone.
2. `cfo-*` panes with `cmd=bash`
   (`tmux list-panes -a -F '#{pane_id} #{pane_current_command} #{session_name}' | grep ' bash '`):
   each one that is active or has state appears in the helper output with tag
   `cx`.
3. `%283`: the helper shows `%283  ready  ● ...` under `needs you`, the status
   bar shows `● N` one higher than before, window mark `●` on its window.
4. A plain `zsh` pane in a window with an active agent (for example `%267` in
   `finance`) is not in the helper output.
5. `time ~/dotfiles/tmux/agent-inbox.sh status`: under 0.5 s wall.
6. One-time cleanup of `%5`. First confirm it is foreign state, not a live
   turn: `tmux display -p -t %5 '#{pane_pid} #{@claude_state} #{@claude_since}'`,
   then `ps -o args= -p <pid of codex below that pane_pid>` has no
   `--no-daemon`. Then:

   ```bash
   tmux set -pu -t %5 @claude_state \; set -pu -t %5 @claude_since \; \
     set -pu -t %5 @claude_wait_agent \; set -pu -t %5 @claude_wait_from \; \
     set -pu -t %5 @claude_agents
   ```

   `tmux show -p -t %5` then lists no `@claude_*`; `%5` shows through V2 only
   while active, with age `-`. Leave `@agent_unseen` and `@agent_report`
   alone unless `tmux show -pv -t %5 @agent_unseen` prints `1` for a result
   that is not its own: then `~/dotfiles/tmux/agent-inbox.sh seen %5`.
