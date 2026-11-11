# hook-codex-env-guard

## Goal

Codex hook events are never dropped because of Claude Code environment
variables. A Ghostty started from a Claude Desktop Bash call hands every pane
`CLAUDE_CODE_ENTRYPOINT=claude-desktop`; Codex in such a pane must still set
pane state, inbox rows and Stop notifications. Claude Code behavior stays as is:
SDK and Desktop Claude sessions are still skipped.

## Current behavior

`claude/hooks/pane-state.sh:25-26` exits on any `CLAUDE_CODE_ENTRYPOINT` other
than `cli`, before it knows which client called it. Codex runs the same file
through the link `~/.codex/hooks/pane-state.sh` (`~/.codex/hooks.json`), so in
a pane with the inherited Desktop env every Codex event exits there: no
`@claude_state`, no inbox row.

`claude/hooks/notify.sh` is not affected: `:32-35` takes the client from the
invocation path (`*/.codex/hooks/*` is Codex, `--agent` overrides) and the
guard at `:67-70` runs only for `agent=claude`. It gets a regression test, no
code change.

## Detection signal

Chosen: the invocation path, `${BASH_SOURCE[0]}` matching `*/.codex/hooks/*`,
the same rule `notify.sh:32-35` already uses. Why:

- Each client calls its own link, `~/.claude/hooks/...` from
  `claude/settings.json`, `~/.codex/hooks/...` from `~/.codex/hooks.json`. The
  caller's own config names the caller, so a nested client (Claude Code started
  in a Codex shell or the reverse) is identified by the one actually firing the
  hook: "nearest agent wins" holds by construction.
- No extra process, no `ps`, same on macOS and Linux, no new failure path
  before G1.
- Neither hook command string changes, so Codex `trusted_hash` entries in
  `~/.codex/config.toml` stay valid.

Rejected:

- Process ancestry (comm basename `codex` below `pane_pid`, reusing G1's walk).
  Claude Code installed through npm runs as `node`, so a Claude SDK session
  started from a Codex shell would find no `claude` ancestor, reach `codex`
  first and be taken for Codex: its headless guard would be skipped. It also
  needs `ps -o comm=` parsing (full paths with spaces on macOS, 15-char
  truncation on Linux).
- Payload fields only one client sends (Codex `turn_id`, `model`). Neither
  client documents them as identity, Claude Code may add fields with the same
  names, and the guard would have to move after the stdin read.

## Not doing

- No change to `~/.codex/hooks.json`, `claude/settings.json`, hook command
  strings, G1, any state transition or `record_result`.
- No change to `claude/hooks/notify.sh`.
- No ancestry or payload probing.

## Contract

**E1, client.** A hook process is Codex when `${BASH_SOURCE[0]}` matches
`*/.codex/hooks/*`, else Claude Code. The headless guard
(`CLAUDE_CODE_ENTRYPOINT` set and not `cli`: exit 0) applies to Claude Code
only; Codex ignores `CLAUDE_*` variables. E1 runs before G1 and before stdin is
read, so every silent-exit guarantee of G1 holds.

## Tasks

One wave, one task.

### T1: client-aware headless guard

Files: `claude/hooks/pane-state.sh`, `codex/test_agent_inbox.py`,
`codex/test_activity.py`. Bash 3.2, no stdout, always exit 0.

1. `claude/hooks/pane-state.sh:25-26`: wrap the guard in a `case` on
   `${BASH_SOURCE[0]}`; `*/.codex/hooks/*` skips it, anything else keeps it.
2. `codex/test_agent_inbox.py`, `HookTests`: a link
   `<root>/home/.codex/hooks/pane-state.sh` and `<root>/home/.claude/hooks/
   pane-state.sh` to `HOOK`, a `hook()` parameter for the script path, and
   - Codex link + `CLAUDE_CODE_ENTRYPOINT=claude-desktop`: UserPromptSubmit
     gives `working`, Stop gives `done` with `@agent_unseen=1`.
   - Claude link (and the plain `HOOK` path) + `claude-desktop`: ignored.
   - Claude link + `cli`: Stop gives `done`.
3. `codex/test_activity.py`, `NotificationTests`: through the two links with
   `claude-desktop`, Codex notifies, Claude does not.

## Edge cases

- macOS vs Linux `ps`: E1 calls no `ps`; G1 is unchanged.
- Missing `ps`: unchanged, G1 exits silently as before.
- Claude Code launched in a Codex shell, or Codex in a Claude Code shell: each
  hook is called through its own client's link, so the firing client decides.
- Claude Desktop env inherited by a Codex pane: Codex link, guard skipped,
  events recorded (the bug).
- A real Claude SDK or Desktop session: called through `~/.claude/hooks`,
  guard applies, skipped as today.
- Called by a path outside both link dirs (repo path, manual run): treated as
  Claude Code, the old behavior.

## Gates

```bash
/bin/bash -n claude/hooks/pane-state.sh
/bin/bash -n claude/hooks/notify.sh
python3 -B -m unittest discover -s codex -p 'test_agent_inbox.py'
python3 -B -m unittest discover -s codex -p 'test_activity.py'
just check
```

## Acceptance

| # | Check | Expected |
|---|-------|----------|
| A1 | Gates | all exit 0 |
| A2 | New pane-state Codex test against the base hook (scratch copy through `HOOK`) | fails |
| A3 | Isolated tmux server, a process named `codex` between pane and hook, hook run through a `.codex/hooks` link with `CLAUDE_CODE_ENTRYPOINT=claude-desktop` and UserPromptSubmit | `@claude_state=working` |
| A4 | `git diff --name-only main...HEAD` | the T1 files and this plan |
