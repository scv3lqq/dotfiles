---
name: setup-dotfiles
description: Set up or update these dotfiles on this machine. Checks the requirements, moves existing configs aside, runs install.sh (or install.sh --update) in a tmux window or the user's terminal, verifies the links and lists the first-run steps left. Invoke as /setup-dotfiles or /setup-dotfiles update.
argument-hint: "[update]"
disable-model-invocation: true
---

# Set up the dotfiles

Argument: $ARGUMENTS

Mode `update` when the argument is `update` (`install.sh --update`: git pull,
upgrades, plugin sync); otherwise mode `install` (plain `install.sh`, safe to
re-run). `README.md` and `install.sh` own the facts, this skill only orders
them; where they disagree, `install.sh` wins. Nothing on the machine changes
before the confirmation in step 3.

## 1. Preflight (read-only)

```sh
uname -sm
sw_vers -productVersion 2>/dev/null || grep -E '^(ID|VERSION_ID)=' /etc/os-release
git rev-parse --show-toplevel; git -C "$HOME/dotfiles" rev-parse --show-toplevel
git -C "$HOME/dotfiles" status --short
git -C "$HOME/dotfiles" rev-parse --abbrev-ref HEAD; git -C "$HOME/dotfiles" rev-parse --abbrev-ref '@{u}'
ls -l ~/.tmux.conf; echo "TMUX=${TMUX:-unset}"
```

Stop and report, changing nothing, when:

- the two `--show-toplevel` lines differ or the second fails: every link
  assumes the checkout is exactly `~/dotfiles`; tell the user to clone it
  there and start `/setup-dotfiles` from that checkout;
- macOS on anything but `arm64`: the Homebrew installer aborts on Intel;
- Linux with `ID` `rhel`, `rocky` or `almalinux`, or with neither `apt-get`
  nor `dnf`;
- the system is neither `Darwin` nor `Linux`;
- mode `update` and the `@{u}` line fails: `git pull --ff-only` needs an
  upstream branch.

Warn, then go on:

- HEAD is not `main`: the links will point at this branch's files and dangle
  after a switch to a branch without them;
- Linux older than Ubuntu 24.04, Debian 13 or Fedora 42: quote what breaks
  from README `## Requirements`;
- mode `update` with dirty tracked files other than `nvim/lazy-lock.json`
  (`install.sh` handles that one): `git pull --ff-only` stops if the pull
  touches them.

The machine is **set up** when `ls -l ~/.tmux.conf` shows a link into
`~/dotfiles/` (`~/dotfiles/tmux/tmux.conf`, or `~/dotfiles/.tmux.conf` on
checkouts older than that move), otherwise **fresh**.

## 2. What install.sh would replace (read-only)

- Fresh: read README from `## Before you start: existing configs` to
  `## Install` (`grep -n` both headings, `sed -n` the range). Run its
  `for p in ...` loop with `echo "would move $p"` in place of the `mv`
  line. On macOS also test
  `~/Library/Application Support/com.mitchellh.ghostty/config` and
  `config.ghostty` next to it.
- Set up: skip that loop (it would move the real `~/.config/nvim`,
  `~/.config/zsh` and `~/.config/yazi` directories that hold the Stow links).
  Check only the Claude Code files `install.sh` links over: every file of
  `~/dotfiles/claude/{agents,hooks,bin}/` plus `claude/statusline.sh` and
  `claude/themes/ayu.json`, at the same path under `~/.claude/`. Each one that
  is a regular file (not a link) and differs from its copy under
  `~/dotfiles/claude/` (`cmp -s`; a missing copy counts as different) goes on
  the move list. On macOS `install.sh` moves a regular `~/.claude/CLAUDE.md` or
  `~/.claude/settings.json` to `~/.claude/backups/` itself: list those as notes,
  not moves. A real directory `~/.claude/skills/<name>` for a name in
  `~/dotfiles/claude/skills/` that holds regular files is skipped by
  `install.sh`: put it in the warnings.

## 3. Confirm (one AskUserQuestion)

Show the mode and the exact command, the move list (when it is not empty,
with the backup directory `~/dotfiles-backup/<timestamp>`), the warnings
from step 1, what `install.sh` deletes or replaces (the
bullets of README `## Before you start: existing configs`) and that it asks
for passwords (README `## Requirements`, "The run is interactive"). Options:
run, cancel. On cancel, stop.

## 4. Move aside

- Fresh: in ONE Bash call (shell state does not survive between calls) run
  the README snippet verbatim, then on macOS move each Ghostty config found
  in step 2 into the same directory:
  `mv "$HOME/Library/Application Support/com.mitchellh.ghostty/<file>" "$backup/ghostty-<file>"`.
- Set up with a non-empty move list:
  `backup=~/dotfiles-backup/$(date +%Y%m%d-%H%M%S); mkdir -p "$backup"`, then
  `mv` each listed file into it, in the same Bash call.

## 5. Run install.sh

The command is `~/dotfiles/install.sh` (install) or
`~/dotfiles/install.sh --update` (update). It asks for passwords, so it never
runs through the Bash tool.

- `TMUX` set: open it in a new window that stays open after the run. Write
  the command without `<flag>` for install, with `--update` in its place for
  update:
  ```sh
  S="$(mktemp -d)"
  W="$(tmux new-window -P -F '#{window_id}' -n dotfiles-setup -c "$HOME/dotfiles" \
    "$HOME/dotfiles/install.sh <flag>; echo \$? > $S/exit; echo; echo 'install.sh finished, press Enter to close this window'; read -r line")"
  echo "dir=$S window=$W"
  ```
  The new window comes to the front: tell the user to answer the prompts
  there and come back to this window when it says finished. Then start ONE
  background Bash (`run_in_background`) with the printed values in place of
  `<dir>` and `<window>`, and end the turn:
  ```sh
  for i in $(seq 360); do
    [ -f <dir>/exit ] && break
    tmux display -p -t <window> '#{window_id}' >/dev/null 2>&1 || break
    sleep 10
  done
  if [ -f <dir>/exit ]; then cat <dir>/exit
  elif tmux display -p -t <window> '#{window_id}' >/dev/null 2>&1; then echo running
  else echo "no exit code"; fi
  ```
  `running` (60 min passed, the window is still open, `install.sh` may wait
  for a password): start the same loop again, this is not a failure. On an
  exit code read the run: `tmux capture-pane -p -J -S -400 -t <window>`. If
  the window is gone, ask the user for the last lines of the output.
- `TMUX` unset: ask the user to run the command in another terminal window
  and to reply when it ends, with the last lines of the output if it failed.
  End the turn and wait.

Exit code not 0, or `no exit code`: name the failing step from the output and
propose a fix. Re-run only after the user agrees; step 4 is not repeated.

## 6. Verify (read-only, one Bash call)

```sh
ls -l ~/.tmux.conf ~/.config/starship.toml ~/.config/nvim/init.lua ~/.config/zsh/.zshrc \
  ~/.claude/skills/feature ~/.claude/agents/implementer.md ~/.claude/hooks/pane-state.sh
cat ~/.zshenv; ls -d ~/.tmux/plugins/tpm
dscl . -read "/Users/$USER" UserShell 2>/dev/null || getent passwd "$USER" | cut -d: -f7
git -C ~/dotfiles status --short
```

Expected: every link resolves into `~/dotfiles` (`~/.tmux.conf` to
`tmux/tmux.conf`, `~/.config/starship.toml` to `starship/starship.toml`),
`~/.zshenv` exports `ZDOTDIR`, TPM exists, the login shell is zsh, the
checkout is clean. On macOS also `readlink ~/.claude/settings.json` (and the
same for `~/.claude/CLAUDE.md`) prints a path under `~/dotfiles/claude/`.

## 7. Report

The backup directory and what moved there, the `install.sh` result (its
`Skipping ...` and `Warning:` lines included), each check from step 6 as ok
or failed. Then the steps left to the user, from README `## First run`:
mode `install` on a fresh machine, every step that applies to this OS (step
6, marked repo owner only, when the `install.sh` output has a
`Skipping commit signing` or `To get Verified commits` line); mode `update`
or a set-up machine, none of them. Always end with: restart Claude Code, since this
session does not see the skills, agents and hooks `install.sh` just linked,
and inside tmux press `prefix + r` to reload the config.
