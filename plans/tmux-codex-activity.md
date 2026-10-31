# Codex activity and notification identity

## Goal and current behavior

Show Codex beside Claude Code in the existing tmux session picker, including
recently completed turns, and attribute desktop alerts to the originating client.
Base: `0a638f8`. Codex already invokes the shared pane-state and notification
hooks through file symlinks under its own hooks directory. Both clients currently
write the existing `@claude_state` / `@claude_since` options. The picker excludes
`codex` processes and notification titles/groups always identify Claude Code.

Baseline: `just check` PASS (47 Codex tests, four feature tests). Both hook scripts
and the picker pass `/bin/bash -n`. New regression tests do not exist on base.
Official hook input/output evidence: <https://learn.chatgpt.com/docs/hooks#stop>.
No new hook configuration or event schema is needed for this fix.

## Constraints and shared definitions

- Preserve Bash 3.2 compatibility, existing tmux state options, 5-second activity
  freshness, 600-second completion retention, ordering, keys, row IDs, preview,
  fzf untracked reload, and all existing Claude behavior.
- Read `.claude/rules/shell-scripts.md` and `.claude/rules/tmux.md` explicitly.
- Client identities: command `codex` maps to `Codex`; command `claude` or the
  existing bare semantic-version regex maps to `Claude Code`. Other processes
  never gain an activity row merely from a leftover state option.
- Activity section heading becomes `  ── assistants ──`; prepend `Codex · ` or
  `Claude Code · ` to the activity/completion row's existing title/path field.
  Apply the existing assistant glyph to Codex window rows as well.
- Notification source is selected by invocation path BEFORE resolving symlinks:
  `*/.codex/hooks/*` identifies Codex, all other paths retain Claude Code default.
  Add optional `--agent codex` / `--agent claude` for canonical-path callers and
  fixtures; unknown values exit silently without a notification. Existing
  `--focus <pane>` must continue to work without an agent argument.
- Titles: `Codex: готово`, `Claude Code: готово`; group prefixes `codex-`,
  `claude-code-`, retaining the existing pane/nopane suffix. Bodies unchanged.
- Claude-specific entrypoint and transcript pending-task guards run only for
  Claude Code; Codex transcripts have a different format. Visibility suppression,
  Linux no-op, click focus, force/debug variables, stdout silence and exit 0 stay.
- Tests use synthetic payloads, fake desktop commands and temporary homes. No
  real notification, transcript, network or user UI manipulation in unit tests.

## Acceptance criteria

1. `python3 -B -m unittest discover -s codex -p 'test_activity.py'` proves Codex
   working/waiting/recent done rows and Claude rows render with exact identities;
   stale working (>5 seconds), expired done (>=600 seconds), and shell leftovers
   are excluded. Done rows remain newest first, row IDs remain target pane IDs,
   and search still includes activity rows without a separator.
2. The same suite proves explicit and symlink-selected notification identities,
   groups `codex-%7` and `claude-code-%7`, visible-pane suppression, Linux silence,
   stdout silence, fallback osascript title, Notification-event silence and click
   focus. Claude headless/pending-task suppression stays; Codex does not inherit
   those Claude-only guards. Unknown --agent is a silent successful no-op.
3. Synthetic lifecycle events through the existing pane-state hook produce
   working, waiting and done, and those states appear for Codex in the picker.
4. Isolated tmux server/PTY smoke opens picker with prefix+s, captures a synthetic
   Codex activity row with Codex label, then navigates to that target. Do not
   modify the live server or inspect real pane content.
5. Live hook commands still resolve to the shared tracked scripts through their
   existing symlinks. No installer or private configuration edits required.

## Tasks

### T0: Regression tests first

Ownership: `codex/test_activity.py` only. No dependencies. Build standard-library
unittest fixtures following the existing test suite conventions. Invoke scripts
with `/bin/bash`. Fake tmux list-panes returns the existing 15 tab-separated
fields, matching the renderer. Use a fixed fake date and synthetic fixture rows.
Test hook state transitions with an isolated tmux server, killed by exact socket
name in cleanup; test picker rendering with fake command names for determinism.
Notification stubs capture argv as JSON and must support both terminal-notifier
and osascript fallback, visibility checks and focus calls. Put a symlink under
both temporary `.codex/hooks/` and `.claude/hooks/` directories to exercise actual
source detection. List literal expected titles/group values from shared definitions.
Complete acceptance criteria 1-3 with meaningful behavioral assertions. Demonstrate
RED against unchanged source, then report failures and hand source work to main.
Do not commit red tests; the first green source wave commits tests and source
atomically. This TDD ordering overrides canonical source-before-test ordering.
Task gate: the acceptance-criterion-1 unittest command (RED expected initially),
`uvx ruff check codex/test_activity.py`, `uvx mypy --strict codex/test_activity.py`.
Named mutations for reviewer, on scratch copies only: remove codex from the
picker recognition condition; replace the Codex notification title with Claude
Code's title. Each must make that unittest command fail. Guards may pass on base.

### T1: Source-aware notifications

Ownership: `claude/hooks/notify.sh` only. Depends on T0 RED evidence. Implement
notification shared definitions, retaining all other behavior. Use the current
SELF invocation path without realpath; parse optional --agent after the existing
--focus branch. No new helper dependency or settings changes. Keep source names
and group prefix controlled by the closed enum, never arbitrary payload text.
Task gates: `/bin/bash -n claude/hooks/notify.sh` and
`python3 -B -m unittest discover -s codex -p 'test_activity.py' -k Notification`.
Done: notification regression tests green, source-aware terminal-notifier and
osascript fallback, no user notification emitted while testing.

### T2: Mixed assistant activity

Ownership: `tmux/session-picker.sh` only. Depends on T0 RED evidence; independent
of T1. Extend current recognition to codex, retain the existing Claude/version
recognition, store client identity for both active and done arrays and prefix
only their final title/path display. Use shared definitions for heading and icon.
No changes to state producer, tmux config, sorting, freshness or retention.
Task gates: `/bin/bash -n tmux/session-picker.sh` and
`python3 -B -m unittest discover -s codex -p 'test_activity.py' -k Picker`.
Done: activity regressions green and no fzf behavior changes beyond displayed text.

## Seams

| Producer | Consumer | Shared definitions |
| --- | --- | --- |
| T0 fixtures | T1 notification script | Client titles, path/flag selection, groups and suppression |
| T0 fixtures | T2 picker | Existing pane-state format and client display identities |
| Existing pane-state hook | T2 picker | Unchanged state options, freshness and retention |

## Gates

- `just check` (before each commit, evidence saved privately).
- `/bin/bash -n claude/hooks/notify.sh claude/hooks/pane-state.sh tmux/session-picker.sh`
- `uvx ruff check codex/test_activity.py`
- `uvx mypy --strict codex/test_activity.py`
- `git diff --check 0a638f8`
- Acceptance criteria 4-5 verified by main and final validator from private evidence.

Plan commit is followed by T0 RED tests, parallel T1/T2 source work, one green
implementation commit, independent scoped review (including named mutations),
and final acceptance validation. Run full Gates serially. Follow repository
fast-forward-to-main and push instructions after PASS. No CI is configured.

## Edge cases

- macOS vs Linux: notification no-op on Linux, renderer stays portable.
- Missing desktop tools: existing osascript fallback retained; tests stub tools.
- Dirty checkout: only pre-existing untracked `.DS_Store`; leave it untouched.
- First run: no hook state produces no activity row; tree works unchanged.
- Canonical hook path: explicit --agent supports callers without runtime symlinks.
- Current terminal clients pick up script changes immediately through symlinks.

## Not doing

No Codex App session listing outside tmux, transcript reconstruction for old
sessions without hook state, new event wiring, state-namespace migration,
resurrect changes, notification body redesign, dependency installation, theme,
README, skill, agent instruction or installer edits.
