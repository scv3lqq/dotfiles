# Claude Code notifications and commit signing in dotfiles

## Goal

The whole notification stack built on 2026-10-12 lives in git and a fresh Mac
gets it from one `./install.sh` run: alert only when Claude Code fully finishes
a turn, nothing from other terminal programs or gopass.

The same run makes every commit in `~/dotfiles` SSH-signed and Verified on
GitHub, on macOS and Linux.

Non-goals: Linux desktop alerts (servers have no desktop; Ghostty drops OSC
9/777, so over SSH there is no path either), global (all-repo) signing, SSH key
generation, the other `~/.claude/hooks/*` scripts, the rest of
`~/.claude/settings.json`.

## Current behavior

- `~/.claude/hooks/notify.sh` is a regular file outside the repo. It
  self-installs `terminal-notifier` via brew on first alert.
- `~/.claude/settings.json` (outside the repo) wires it as the only `Stop` hook.
- `~/.claude.json` has `preferredNotifChannel: notifications_disabled`, set by
  hand with jq; `claude config set` no longer exists.
- `~/.config/gopass/config` has `core.notifications = false`, set by hand.
- `ghostty/ghostty/config` already has `desktop-notifications = false` (in git).
- `install.sh` knows nothing about Claude Code.
- Signing was configured by hand in `.git/config` (not in git): `user.email`
  (personal; global `~/.gitconfig` holds the work address), `gpg.format ssh`,
  `user.signingkey ~/.ssh/id_ed25519.pub`, `gpg.ssh.allowedSignersFile
  ~/.ssh/allowed_signers`, `commit.gpgsign true`, `tag.gpgsign true`. The key is
  registered on GitHub as both auth and signing key. A fresh clone gets none of it.

## Target behavior

- Script lives at `claude/hooks/notify.sh` in the repo; `~/.claude/hooks/notify.sh`
  is a symlink to it (`ln -sf`, same as `starship.toml`, not Stow: the target
  dir holds unmanaged hooks).
- `install.sh`, macOS branch only, after the Stow section:
  1. `terminal-notifier` added to the existing `brew install` line.
  2. `mkdir -p ~/.claude/hooks`, symlink the script.
  3. `~/.claude/settings.json`: created as `{}` if missing; a `Stop` hook with
     command `~/.claude/hooks/notify.sh` (timeout 10) appended only when no
     `Stop` hook command already mentions `notify.sh`. Idempotent; other keys
     and hooks untouched.
  4. `~/.claude.json`: `preferredNotifChannel` set to `notifications_disabled`
     (file created with only that key if missing).
  5. gopass: `gopass config core.notifications false` only when gopass is
     installed and `~/.config/gopass/config` exists (avoids an interactive
     first-run setup).
- `install.sh`, both OSes, new "Commit signing" block after the Stow section:
  1. Skip with a message when `~/.ssh/id_ed25519.pub` is missing or git is
     older than 2.34 (no SSH signing); never generate a key.
  2. Identity = author email of the last commit (`git -C "$DOTFILES" log -1
     --format=%ae`), so no address is hardcoded in the repo.
  3. Repo-local config (`git -C "$DOTFILES" config`): `user.email`, the five
     signing keys above. Global `~/.gitconfig` untouched.
  4. `~/.ssh/allowed_signers`: append `<email> <key type> <key>` only when the
     line is not there yet (`grep -qF`).
  5. GitHub: when `gh` is installed and `gh api user/ssh_signing_keys`
     succeeds (needs scope `admin:ssh_signing_key`), add the key with
     `gh ssh-key add --type signing` unless it is listed already; otherwise
     print the one-line hint (`gh auth refresh -h github.com -s
     admin:ssh_signing_key`, then re-run). Never fails the install.
- `notify.sh`: drop the brew self-install (provisioning belongs to
  `install.sh`); exit 0 early when `uname` is not Darwin. Everything else
  unchanged (focus check, pending-task check, headless skip, click-to-pane).

## Relevant files

| Path | Why | Action |
|---|---|---|
| `claude/hooks/notify.sh` | new home of the hook | create (move from `~/.claude/hooks/`) |
| `~/.claude/hooks/notify.sh` | live hook path used by settings.json | replace with symlink |
| `install.sh` | provisioning | edit: brew line, new "Claude Code notifications" and "Commit signing" blocks |
| `README.md` | Layout table, after-install steps | edit: one table row, two steps (allow terminal-notifier in System Settings; gh scope for the signing key) |
| `.git/config`, `~/.ssh/allowed_signers` | written by the signing block | runtime only, not tracked |
| `CLAUDE.md` | repo map | edit: one line for `claude/` |
| `ghostty/ghostty/config` | already done | read-only |

## Constraints

- macOS-only steps stay inside `[[ "$OS" == "Darwin" ]]`; Linux path unchanged.
- No Stow package change; `claude/` is linked by `ln -sf` only.
- Hook command string stays `~/.claude/hooks/notify.sh`, so the existing
  settings.json entry is recognized and not duplicated.
- `SessionStart`/`SessionEnd` hooks (owned by tmux-assistant-resurrect) and all
  other settings.json content untouched.
- `set -e` in install.sh: every new command must not fail on a re-run.

## Implementation steps

- T0 (orchestrator): back up `~/.claude/hooks/notify.sh` to
  `~/.claude/backups/`, copy it to `claude/hooks/notify.sh`, apply the two
  script edits, then `ln -sf ~/dotfiles/claude/hooks/notify.sh ~/.claude/hooks/notify.sh`.
- T1 (orchestrator): `install.sh` brew line + Claude block + signing block;
  README and CLAUDE.md lines.
- T2 (orchestrator): verification below, then two signed commits, pushed:
  `feat(claude): manage notify hook and its setup in dotfiles` and
  `feat(install): configure SSH commit signing for the dotfiles repo`.

## Tests / verification

- `bash -n install.sh && bash -n claude/hooks/notify.sh`
- Claude block extracted and run twice against a scratch `HOME`:
  - empty HOME: settings.json gets exactly one Stop hook, `.claude.json` gets
    the key, symlink resolves into the repo;
  - copy of the real settings.json: Stop hook count stays 1, `jq -S` diff of
    everything except `.hooks.Stop` is empty;
  - second run: no change (idempotent).
- Hook replay with stub `terminal-notifier` (same test as 2026-10-12): finished
  transcript alerts, pending transcript and `CLAUDE_CODE_ENTRYPOINT=sdk-cli` stay silent.
- `readlink ~/.claude/hooks/notify.sh` points into `~/dotfiles`.
- Signing block run twice against a scratch `git clone` of the repo and a
  scratch `HOME` holding a copy of the public key: repo-local config has the
  six keys, `allowed_signers` has exactly one line, `git commit-tree -S` in the
  clone succeeds and `git verify-commit` passes; with the key file removed the
  block prints the skip message and exits 0. gh step checked against the real
  account (key already present: no add).

## Edge cases

- Claude Code running during install may rewrite `~/.claude.json` from memory:
  README step says to restart Claude after install.
- `terminal-notifier` needs notification permission once (System Settings);
  until then the script falls back to `osascript` (no click-to-pane).
- No jq: impossible on macOS here, jq is on the same brew line.
- Existing regular file at the symlink path: `ln -sf` replaces it.
- Signing with a passphrase-protected key and no agent: git prompts at commit
  time, not during install.
- Linux server whose key is not on GitHub: commits are signed but show
  Unverified; the gh hint covers it.
- Old distro git (< 2.34): block skips, commits stay unsigned rather than failing.

## Rollback

`git revert` the commit; restore the script from `~/.claude/backups/` over the
symlink. settings.json / .claude.json changes are the same values as today.

## Acceptance criteria

- [ ] `~/.claude/hooks/notify.sh` is a symlink into the repo and alerts work.
- [ ] Fresh scratch HOME after the install block: hook wired once, channel disabled.
- [ ] Re-running the block changes nothing.
- [ ] Linux branch of install.sh unchanged.
- [ ] No brew call left in notify.sh.
- [ ] Fresh clone after the signing block: commits signed, `verify-commit` passes,
      no email literal in tracked files.
- [ ] Missing key or old git: install continues with a message.

## Notes for reviewer

Risks: the jq merge on settings.json (must keep every other key); the signing
block under `set -e` (every probe wrapped in `if`). Expected diff: new
`claude/hooks/notify.sh` (~170 lines), ~55 lines in install.sh, 3-4 doc lines.
