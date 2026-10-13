# tmux-assistant-resurrect

Source of truth: plugin README and source at commit `4d74092` (2026-09-11),
https://github.com/timvw/tmux-assistant-resurrect. Continuum behavior verified
against the local checkout in `~/.tmux/plugins/tmux-continuum`.

## Goal

AI assistant sessions (primarily Claude Code, also Codex) survive
`tmux kill-server` and reboots: tmux-resurrect restores the layout, the plugin's
post-restore hook types `claude <saved flags> --resume <id>` into each pane.

Non-goals:

- No `@assistant-resurrect-capture-env` (captured values land on disk in plain
  text).
- No session-less relaunch vouchers (`claude agents` etc.).
- No pinning/forking of the plugin, no changes to `~/.claude/settings.json` by
  hand: the plugin's installer owns its two hook entries.
- `everything.md` (cheatsheet that lags the configs by design, still says
  "continuum (restore off)" at lines 263 and 419) is not updated here.

## Current behavior

`.tmux.conf` loads tpm, vim-tmux-navigator, tmux-sessionist, tmux-dotbar,
tmux-resurrect, tmux-continuum. `@resurrect-capture-pane-contents` is already
`on`, `@continuum-restore` is `off`, `@continuum-save-interval` is unset
(continuum default 15 min). Restore is manual (`prefix + Ctrl-r`) and assistant
panes come back as bare shells.

Pre-check results (2026-09-21):

| Check | Result |
|---|---|
| tmux | 3.7c (plugin tested on 3.4 to 3.7) |
| jq / python3 | `/opt/homebrew/bin/jq`, `/opt/homebrew/bin/python3` present |
| jq in `install.sh` | absent from both the brew and the apt/dnf lists |
| `@resurrect-hook-post-save-all` / `-post-restore-all` | unset in config and in the live server: no conflict |
| `@resurrect-processes` | unset: no assistant double-launch |
| `@resurrect-dir` | unset; save dir resolves to `~/.local/share/tmux/resurrect` (`~/.tmux/resurrect` does not exist) |
| `~/.claude/settings.json` | regular file (0600), not a symlink, not managed by this repo or `install.sh` |
| Existing Claude hooks | `PreToolUse` (commit-subject-length), `PostToolUse` (no-em-dash), `Stop` (notify); no `SessionStart` / `SessionEnd` |
| `~/.cursor/hooks.json`, `~/.config/opencode/plugins/` | do not exist |
| Plugin vs `status-right` | no reference to `status-right`/`status-left` anywhere in plugin source |
| `status-right` continuum_save count | 1 (baseline) |
| Running inside tmux | yes: no `kill-server` from the agent |

## Target behavior

- Plugin loaded last in the plugin list, after tmux-continuum.
- Autosave every 5 min, auto-restore on tmux server start.
- Plugin sets `@resurrect-hook-post-save-all`, `@resurrect-hook-post-restore-all`
  and `@assistant-resurrect-relaunch 'on'` (inert without a voucher file) at
  load time; these are runtime options, not config lines.
- Plugin installer adds one `SessionStart` and one `SessionEnd` entry to
  `~/.claude/settings.json` (command form `bash "$HOME"'/.tmux/plugins/...'`,
  no absolute machine path). Existing hook events stay untouched. The installer
  is self-healing: it re-adds missing entries on every tmux start.
- Side effects outside the repo, unconditional even though neither tool is
  installed: creates `~/.cursor/hooks.json` (`{"version":1}` plus two hooks) and
  symlinks `~/.config/opencode/plugins/session-tracker.js` into the plugin dir.

## Relevant files

- `.tmux.conf`: edit. Plugin list and resurrect/continuum options.
- `install.sh`: edit. Add `jq` to package lists (plugin silently skips Claude
  hook install when jq is missing, which matters on a fresh machine or server).
- `~/.claude/settings.json`: not in repo; modified by the plugin installer only.
  Back up first.
- `~/.tmux/plugins/tpm/bin/install_plugins`: read-only, verified to exist.
- `README.md`, `everything.md`, `AGENTS.md`: read-only.

## Constraints

- Plugin order: tpm, vim-tmux-navigator, tmux-sessionist, tmux-dotbar,
  tmux-resurrect, tmux-continuum, tmux-assistant-resurrect. Continuum stays
  after dotbar (dotbar overwrites `status-right`, continuum appends to it).
- `run '~/.tmux/plugins/tpm/tpm'` stays the last line.
- Do not add `@resurrect-processes`, `@resurrect-dir`,
  `@assistant-resurrect-capture-env`.
- Keep macOS/Linux branching in `install.sh`; only extend existing package lists.
- No `tmux kill-server`, no `./install.sh`, no `brew install` by agents.
- Backups go to `~/.claude/backups/`, never into the repo.
- Target files `.tmux.conf` and `install.sh` were clean before T1/T2; the
  unrelated dirty `CLAUDE.md` and this plan file stay out of the commit, so the
  revert touches config only.

## Implementation steps

- **T0 (orchestrator)**: snapshot pre-state.
  `cp -p ~/.claude/settings.json ~/.claude/backups/settings.json.bak.<ts>`;
  record that `~/.cursor/hooks.json` and `~/.config/opencode/plugins/` are
  absent. Gate: backup exists and `jq empty` passes on it.
- **T1 (implementer)**: `.tmux.conf`.
  - After `set -g @plugin 'tmux-plugins/tmux-continuum'` add
    `set -g @plugin 'timvw/tmux-assistant-resurrect'`, preceded by a one-line
    why-comment: it hooks resurrect's post-save/post-restore, so it loads after
    resurrect and continuum.
  - `set -g @continuum-restore 'off'` becomes `'on'`.
  - Add `set -g @continuum-save-interval '5'` next to it.
  - Leave `@resurrect-capture-pane-contents 'on'` as is.
  Gate: diff touches only those lines.
- **T2 (implementer)**: `install.sh`. Append `jq` to the `brew install` list and
  to both the `apt-get install` and `dnf install` base lists. python3 is not
  added: Claude detection does not need it (only Codex/OpenCode/Pi lookups do),
  and it ships with the OS on the target platforms. Gate: `bash -n install.sh`.
- **T3 (orchestrator, needs user OK: mutates `$HOME`)**:
  `~/.tmux/plugins/tpm/bin/install_plugins`, then
  `tmux source-file ~/.tmux.conf`. `install_plugins` only clones; the
  `source-file` runs TPM, which executes the plugin entry point and thereby the
  hook installer. Auto-restore does not fire on reload: continuum restores only
  when the server is younger than 10 s (`@continuum-restore-max-delay`).
- **T4 (orchestrator)**: verification block below plus the installer diff
  report.
- **T5 (plan-reviewer, then orchestrator)**: review the diff against this plan,
  then one commit with explicit pathspec `.tmux.conf install.sh`:
  `feat(tmux): restore AI assistant sessions across tmux restarts`.
  Unsigned (no `gpg.format` configured).

## Tests / verification

```sh
bash -n install.sh
tmux source-file ~/.tmux.conf
tmux show -g status-right | grep -c continuum_save          # must print 1
tmux show -gqv @continuum-restore                           # on
tmux show -gqv @continuum-save-interval                     # 5
tmux show -gqv @resurrect-hook-post-save-all                # save-assistant-sessions.sh
tmux show -gqv @resurrect-hook-post-restore-all             # restore-assistant-sessions.sh
tmux show -gqv @resurrect-processes                         # empty
jq '.hooks.SessionStart, .hooks.SessionEnd' ~/.claude/settings.json
diff <(jq -S . ~/.claude/backups/settings.json.bak.<ts>) <(jq -S . ~/.claude/settings.json)
jq . ~/.cursor/hooks.json
ls -la ~/.config/opencode/plugins/
```

The settings diff must show exactly two added keys under `.hooks` and nothing
else. `jq -S` on both sides hides the reformatting the installer's `jq` rewrite
causes.

## Edge cases

- **Already-running Claude sessions** (including the orchestrator's own) have no
  `SessionStart` state file. They are resolved through the transcript fallback
  (newest transcript for the pane cwd), which is ambiguous for two sessions in
  one cwd. Only sessions started after install are tracked exactly, hence the
  manual test uses a new session.
- **Flag replay**: CLI flags are read from `ps` and replayed, so a session
  started with `--dangerously-skip-permissions` comes back in that mode,
  unattended, after a reboot. Opt out with
  `@assistant-resurrect-claude-drop-flags` if unwanted.
- **Auto-restore on every server start**: to skip once,
  `touch ~/tmux_no_auto_restore` (continuum halt file), remove it afterwards.
- **Linux servers** share this `.tmux.conf`: the plugin installs there on
  `prefix + I` and needs jq (T2).
- **Deleted cwd**: pane returns as a shell, assistant not launched.
- **Save cost**: the hook runs on every save (every 5 min) under a 60 s
  watchdog. The sidecar is written atomically, a killed save never corrupts it.

## Rollback / migration notes

Order matters: the uninstall recipes live inside the plugin dir.

1. `cd ~/.tmux/plugins/tmux-assistant-resurrect && just uninstall-claude-hook uninstall-cursor-hook uninstall-opencode-plugin`.
   Do not run plain `just uninstall`: it includes `unconfigure-tmux`, which
   rewrites `~/.tmux.conf` through `mv` and would replace the repo symlink with
   a regular file if it ever matched.
   Without `just`: restore the backup, or apply the same jq filter by hand (drop
   entries whose command contains `claude-session-track` /
   `claude-session-cleanup`).
2. `git revert <sha>`.
3. `tmux set -gu @resurrect-hook-post-save-all; tmux set -gu @resurrect-hook-post-restore-all; tmux set -gu @assistant-resurrect-relaunch`,
   then `tmux source-file ~/.tmux.conf`.
4. `~/.tmux/plugins/tpm/bin/clean_plugins` (or `prefix + alt + u`).
5. Leftovers: `~/.cursor/hooks.json` (only if it holds nothing else),
   `~/.config/opencode/plugins/session-tracker.js`,
   `~/.local/state/tmux-assistant-resurrect/`,
   `~/.local/share/tmux/resurrect/assistant-*`.

If step 1 is skipped and the plugin dir is removed, every `claude` start logs a
failing `SessionStart` hook until the entries are removed.

## Acceptance criteria

- [ ] Plugin line is the last `@plugin`, directly after tmux-continuum.
- [ ] `@continuum-restore 'on'`, `@continuum-save-interval '5'`,
      `@resurrect-capture-pane-contents 'on'` in `.tmux.conf`.
- [ ] No `@assistant-resurrect-capture-env`, no `@resurrect-processes`.
- [ ] `continuum_save` count in `status-right` is 1 after reload.
- [ ] `~/.claude/settings.json`: `PreToolUse`, `PostToolUse`, `Stop` and all
      non-hook keys byte-equal after `jq -S`; `SessionStart` and `SessionEnd`
      added.
- [ ] `install.sh` passes `bash -n`, jq in all three package lists.
- [ ] One commit, two files, revertable on its own.

## Notes for reviewer

- Expected diff: about 4 lines in `.tmux.conf`, 3 words in `install.sh`.
- The plugin README carries a "vibecoded, limited real-world usage" disclaimer.
  TPM tracks the default branch unpinned and the repo publishes no tags, so
  `prefix + U` pulls new code that edits `~/.claude/settings.json` on the next
  tmux start. Reviewed revision: `4d74092`.
- `hook_command` keeps `$HOME` unexpanded in the persisted hook command, so the
  settings entry carries no machine-specific path.
