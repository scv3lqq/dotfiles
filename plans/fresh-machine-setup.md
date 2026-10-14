# Fresh-machine setup: working install.sh and an accurate README

## Goal

A person who knows nothing about this repo follows `README.md` on a fresh
Apple Silicon Mac or a fresh Ubuntu 24.04+/Debian 13+/Fedora server and ends
up with a working shell, tmux and Neovim (plugins built, tree-sitter parsers
compiled, Mason servers installed) without reading any other file.

Non-goals: Intel Macs, RHEL/Rocky/Alma, Ubuntu 22.04/Debian 12 support;
changing keybindings, aliases, themes; fixing config bugs unrelated to setup
(`gcof`, `tmux-reload`, `clipboard` over SSH, Karabiner device ids, AeroSpace
Alt keys, `.stow-local-ignore`); creating the topgrade launchd agent from
`install.sh`; touching `everything.md`, `CLAUDE.md`, `AGENTS.md`.

## Current behavior

`install.sh` installs a subset of what the configs need. Evidence from
container runs (Ubuntu 24.04, Fedora 44, aarch64) and research:

- Linux: Neovim tarball is x86_64-only (`install.sh:36`), broken on arm64 and
  never replaced because only presence is checked (`:35`); root `tar` keeps
  the archive owner, so `/usr/local/{bin,lib,share}` become uid 1001;
  `chsh` (`:154`) fails with "PAM: Authentication failure" for a passwordless
  cloud user and exits 1 under `set -e`; on Fedora `command -v zsh` is
  `/usr/sbin/zsh`, not listed in `/etc/shells`; no fzf (tmux `prefix + s`
  popup breaks), no make/gcc (telescope-fzf-native, guihua builds fail and
  telescope errors on every start), no tree-sitter CLI (all 19 parsers fail),
  no go/npm/unzip/python3-venv (Mason gopls, yamlls, basedpyright fail),
  no zsh-autosuggestions. Neither apt nor dnf: nothing installs, then Stow is
  missing and the script dies.
- macOS: brew line lacks ripgrep, tree-sitter-cli, go, node, yarn, gh.
  `brew install --cask` exits 1 when the app or font already exists outside
  brew (true on the owner's Mac for Karabiner and the font), aborting the
  script before Stow.
- Both: `zsh/.zshrc:27` prints "command not found: go" on every start when go
  is missing; `fzf --zsh` prints "unknown option: --zsh" on fzf < 0.48
  (Ubuntu 24.04 ships 0.44.1); `FZF_DEFAULT_COMMAND` uses `fd`, absent on
  Linux, so `nf`/Ctrl+T list nothing; compinit dump dir `~/.cache/zsh` is
  never created. The notify hook check in `install.sh:93` errors on a Stop
  hook without `command` and appends a duplicate hook.
- Lazy does not retry failed builds: deps must exist before the first `nvim`.
- `README.md` claims "lazy.nvim installs everything automatically", omits
  prerequisites, existing-config clobbering, macOS permissions, the
  owner-only nature of commit signing, Linux limitations; its brew block lacks
  `terminal-notifier` and its Linux block drifted from `install.sh`.

## Target behavior

- `install.sh` provisions every external tool the configs need on macOS and
  on apt/dnf Linux (x86_64 and arm64), is safe to re-run, never leaves
  `/usr/local` owned by a non-root uid, and switches the shell without a
  password prompt on Linux.
- `zsh/.zshrc` starts silently on a machine without go, fd, bat, eza, or with
  an old fzf.
- `README.md` is a complete newcomer guide (see T3).

## Relevant files

- `install.sh`: edit (T1).
- `zsh/.zshrc`: edit (T2).
- `README.md`: rewrite (T3).
- `plans/fresh-machine-setup.md`: this plan, read-only for implementers.
- Read-only context: `.tmux.conf`, `zsh/aliases.zsh`, `zsh/.zprofile`,
  `nvim/init.lua`, `nvim/lua/plugins/*.lua`, `aerospace/aerospace/aerospace.toml`,
  `karabiner/karabiner/karabiner.json`, `ghostty/ghostty/config`,
  `topgrade/topgrade/topgrade.toml`, `plans/topgrade-autoupdate.md`,
  `~/Library/LaunchAgents/local.topgrade.plist`.

## Constraints

- Keep `#!/usr/bin/env bash` + `set -e`; do not add `pipefail`.
- Keep the macOS/Linux branching; macOS-only steps never run on Linux.
- Keep `DOTFILES="$HOME/dotfiles"`, Stow package layout, link targets, the
  Claude notify block semantics, the commit-signing block (except nothing),
  TPM clone, `~/.zshenv` line.
- No keybinding, alias, prompt or theme change. `zsh/aliases.zsh` untouched.
- Never use the em dash character (U+2014) in any file.
- Comments: only "why", matching surrounding density.
- Do not run `./install.sh` on the host; do not `brew install` anything.

## Shared definitions

Supported targets (state exactly these in README):

- macOS: Apple Silicon only (the official Homebrew installer aborts on Intel
  since 2026-09-04), admin account.
- Linux: Ubuntu 24.04+, Debian 13+, Fedora 42+; x86_64 or arm64; a user with
  sudo. Older releases: tmux < 3.3 rejects `allow-passthrough`, glibc < 2.39
  cannot run the prebuilt tree-sitter CLI on arm64 (no highlighting), fzf <
  0.48 falls back to the packaged key bindings. RHEL/Rocky/Alma: not
  supported (stow, fzf, ripgrep live in EPEL).

## Implementation steps

### T1: install.sh (owner: implementer)

Scope: `install.sh` only. Gate: `bash -n install.sh`, `shellcheck install.sh`
if available (report, do not chase pre-existing warnings outside your edits).

1. macOS brew formula line: append `ripgrep tree-sitter-cli go node yarn gh`
   on a new continuation line after `lazygit lazydocker topgrade terminal-notifier`.
2. macOS casks: replace the two `brew install --cask` lines with a loop that
   installs each cask separately and does not abort on failure:

   ```bash
     # A copy installed outside brew (DMG app, hand-installed font) makes brew
     # exit 1: keep it and go on
     for cask in ghostty karabiner-elements font-jetbrains-mono-nerd-font nikitabobko/tap/aerospace; do
       brew install --cask "$cask" || echo "Skipping $cask: brew could not install it (already installed by hand?)"
     done
   ```

3. Linux branch, replace the whole body (from `echo "Installing packages (Linux)..."`
   to the end of the tmux block) with:

   ```bash
     echo "Installing packages (Linux)..."
     case "$(uname -m)" in
       x86_64) nvim_arch=x86_64 ts_arch=x64 ;;
       aarch64 | arm64) nvim_arch=arm64 ts_arch=arm64 ;;
       *) echo "Unsupported architecture: $(uname -m)"; exit 1 ;;
     esac

     # Neovim, tree-sitter CLI (nvim-treesitter), make/gcc (plugin builds),
     # go/npm/unzip/python venv (Mason servers) must exist before the first
     # nvim start: lazy.nvim does not retry a failed build
     if command -v apt-get &>/dev/null; then
       sudo apt-get update -q
       sudo apt-get install -y stow zsh curl git jq tmux fzf ripgrep make gcc unzip \
         python3-venv nodejs npm golang-go zsh-autosuggestions
     elif command -v dnf &>/dev/null; then
       sudo dnf install -y stow zsh curl git jq tmux fzf ripgrep make gcc unzip \
         python3 nodejs npm golang zsh-autosuggestions
     else
       echo "No apt-get or dnf: install the packages listed in README.md by hand"
       exit 1
     fi

     # The config needs Neovim 0.11.3+; distro packages are older
     nvim_version="$(nvim --version 2>/dev/null | sed -n '1s/^NVIM v\([0-9.]*\).*/\1/p')"
     if [[ -z "$nvim_version" || "$(printf '%s\n' 0.11.3 "$nvim_version" | sort -V | head -1)" != 0.11.3 ]]; then
       # --no-same-owner: as root tar would keep the archive's uid on /usr/local/{bin,lib,share}
       curl -fsSL "https://github.com/neovim/neovim/releases/latest/download/nvim-linux-$nvim_arch.tar.gz" |
         sudo tar -C /usr/local -xz --strip-components=1 --no-same-owner
     fi

     # Checks the version output, not the exit code: a failed or interrupted
     # download leaves an empty file that bash runs as an empty script (exit 0)
     if ! tree-sitter --version 2>/dev/null | grep -q '^tree-sitter '; then
       curl -fsSL "https://github.com/tree-sitter/tree-sitter/releases/latest/download/tree-sitter-linux-$ts_arch.gz" |
         gunzip | sudo tee /usr/local/bin/tree-sitter >/dev/null
       sudo chmod 755 /usr/local/bin/tree-sitter
       if ! /usr/local/bin/tree-sitter --version 2>/dev/null | grep -q '^tree-sitter '; then
         sudo rm -f /usr/local/bin/tree-sitter
         echo "Skipping tree-sitter CLI: download failed or the prebuilt binary needs glibc 2.39+, Neovim gets no tree-sitter highlighting"
       fi
     fi

     if ! command -v starship &>/dev/null; then
       curl -sS https://starship.rs/install.sh | sh -s -- -y
     fi
   ```

   The old `rm nvim-linux-x86_64.tar.gz` and the separate tmux block go away
   (tmux is now in the package lists).
4. Notify hook check (`install.sh:93`): change the jq filter to
   `'[.hooks.Stop[]?.hooks[]?.command // empty] | any(test("notify\\.sh"))'`
   so a hook without `command` (e.g. `type: "prompt"`) does not make jq exit 5.
5. Default shell block: replace with

   ```bash
   if [[ "${SHELL##*/}" != zsh ]]; then
     echo "Setting zsh as default shell..."
     if [[ "$OS" == "Darwin" ]]; then
       chsh -s "$(command -v zsh)"
     else
       # chsh asks for a password cloud users do not have; on Fedora
       # `command -v zsh` is /usr/sbin/zsh, which /etc/shells does not list
       zsh_path="$(grep -m1 '/zsh$' /etc/shells || command -v zsh)"
       sudo usermod -s "$zsh_path" "$(id -un)"
     fi
   fi
   ```

Definition of done: steps 1 to 5 applied verbatim (indentation two spaces as
in the file), nothing else changed, `bash -n install.sh` passes.

### T2: zsh/.zshrc (owner: implementer)

Scope: `zsh/.zshrc` only. Gate: `zsh -n zsh/.zshrc`, plus
`env -i HOME="$(mktemp -d)" PATH=/usr/bin:/bin ZDOTDIR="$PWD/zsh" TERM=xterm-256color zsh -i -c exit`
run from the repo root under a pty (`script -q /dev/null ...`; without a tty
fzf's script prints `can't change option: zle`) must print nothing on stderr
except a possible
`starship: command not found` (starship is not on that PATH; acceptable).

1. Line 27: `export PATH="$PATH:$(go env GOPATH)/bin"` becomes
   `command -v go &>/dev/null && export PATH="$PATH:$(go env GOPATH)/bin"`.
2. Before `compinit -u -d "$HOME/.cache/zsh/zcompdump"` add
   `[[ -d "$HOME/.cache/zsh" ]] || mkdir -p "$HOME/.cache/zsh"`
   (compinit silently skips the dump when the directory is missing).
3. Replace `command -v fzf &>/dev/null && eval "$(fzf --zsh)"` with:

   ```zsh
   if command -v fzf &>/dev/null; then
     if _fzf_init="$(fzf --zsh 2>/dev/null)"; then
       eval "$_fzf_init"
     else
       # fzf < 0.48 (Ubuntu 24.04, Debian 12) has no --zsh: use the packaged script
       for _p in /usr/share/doc/fzf/examples/key-bindings.zsh /usr/share/fzf/shell/key-bindings.zsh; do
         [[ -f "$_p" ]] && source "$_p" && break
       done
     fi
     unset _fzf_init _p
   fi
   ```

4. Replace the five `export FZF_*` lines with:

   ```zsh
   # fd, bat and eza come from Homebrew; the Linux install has none of them
   if command -v fd &>/dev/null; then
     export FZF_DEFAULT_COMMAND="fd --type f --hidden --exclude .git"
     export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
     export FZF_ALT_C_COMMAND="fd --type d --hidden --exclude .git"
   fi
   command -v bat &>/dev/null && export FZF_CTRL_T_OPTS="--preview 'bat --color=always --line-range :500 {}'"
   command -v eza &>/dev/null && export FZF_ALT_C_OPTS="--preview 'eza --tree --level=2 --color=always {}'"
   ```

Definition of done: on macOS with brew tools present, every exported value is
identical to before (verify with
`zsh -i -c 'print -l $FZF_DEFAULT_COMMAND $FZF_CTRL_T_COMMAND $FZF_ALT_C_COMMAND $FZF_CTRL_T_OPTS $FZF_ALT_C_OPTS'`
on the old file via `git show HEAD:zsh/.zshrc > <scratch>` with ZDOTDIR
pointing at a scratch copy, and on the new one), gate passes.

### T3: README.md rewrite (owner: implementer, model override opus)

Scope: `README.md` only. English. Keep it scannable: headings, short
paragraphs, tables, fenced shell blocks. No em dash. Every fact below was
verified; do not add claims you have not checked in the repo files. Read
`install.sh` and `zsh/.zshrc` AFTER T1/T2 land (the orchestrator tells you
when) and describe them as they are.

Required structure and content:

1. Title + one-paragraph description: macOS workstation (Ghostty, AeroSpace,
   Karabiner, Neovim, tmux, zsh, Starship, Yazi) and Linux servers (zsh,
   tmux, Neovim, Starship). Configs are symlinked into `$HOME`, edits in the
   repo are live.
2. `## Requirements`: the Supported targets from Shared definitions, the
   checkout path `~/dotfiles` (must be exactly there), internet access, and
   that the run is interactive: macOS asks for the sudo password (Homebrew,
   the Karabiner pkg), Homebrew waits for RETURN, `chsh` asks for the user
   password if the login shell is not zsh; Linux asks for the sudo password.
3. `## Before you start: existing configs`: what `install.sh` overwrites or
   deletes (`~/.config/karabiner` removed, `~/.zshenv` overwritten,
   `~/.tmux.conf` and `~/.config/starship.toml` replaced by links) and that
   Stow aborts the run if `~/.config/{nvim,zsh,yazi}` (and on macOS
   `ghostty,aerospace,topgrade`) contain regular files. Give a backup snippet
   (POSIX sh, works in bash and zsh) that moves every such non-symlink path
   into `~/dotfiles-backup/`. Mention that a Ghostty config in
   `~/Library/Application Support/com.mitchellh.ghostty/` overrides the repo's
   one, and that apps or fonts installed by hand before are kept (the cask
   install prints "Skipping ...").
4. `## Install` with `### macOS` (1. `xcode-select --install` because git is
   needed for the clone, 2. clone over HTTPS + `./install.sh`) and
   `### Linux` (1. `sudo apt-get install -y git` or `sudo dnf install -y git`,
   2. clone + `./install.sh`). One sentence each on what the script does
   (packages, links, TPM, ZDOTDIR, default shell, macOS Claude Code hook,
   commit signing when a key exists). Safe to re-run.
5. `## First run` numbered:
   1. Open a new terminal (macOS) or reconnect (Linux) so zsh is the login shell.
   2. tmux plugins: start `tmux`, press `Ctrl+a` then `Shift+i`.
   3. Neovim: start `nvim`; lazy.nvim installs plugins at the commits in
      `nvim/lazy-lock.json`, nvim-treesitter compiles parsers, Mason installs
      gopls, basedpyright, ruff, lua_ls, yamlls (interactive start only), and
      go.nvim installs its Go tools: the first start takes several minutes.
      If nvim stops at "Press ENTER or type command to continue", press
      Enter: the installs wait for it (seen in T4). The bootstrap clones
      lazy.nvim from its `stable` branch, so the first start rewrites the
      lazy.nvim line of `nvim/lazy-lock.json`; `:Lazy restore` alone does not
      undo it (T4). Recipe verified in T4:
      `git -C ~/dotfiles checkout nvim/lazy-lock.json` then
      `nvim --headless "+Lazy! restore" +qa`. If a build failed because a tool
      was missing, fix it and run `:Lazy build <plugin>` (lazy.nvim does not
      retry builds).
   4. macOS permissions: open AeroSpace once and grant Accessibility (System
      Settings > Privacy & Security > Accessibility), later logins start it
      via `start-at-login`; open Karabiner-Elements and follow its setup
      (allow its background items in General > Login Items & Extensions,
      Accessibility and Input Monitoring for Karabiner-Core-Service, the
      driver extension); allow `terminal-notifier` on the first Claude Code
      alert. Set Ghostty as your terminal.
   5. SSH from Ghostty to a server: copy Ghostty's terminfo once,
      `infocmp -x xterm-ghostty | ssh <host> -- tic -x -`, otherwise tmux on
      the server fails with "missing or unsuitable terminal: xterm-ghostty".
   6. Commit signing (repo owner only): before `install.sh`, have
      `~/.ssh/id_ed25519` (`ssh-keygen -t ed25519`), `gh auth login`, and
      `gh auth refresh -h github.com -s admin:ssh_signing_key`; re-run
      `./install.sh` to upload the key. Warn: the step sets this repo's
      `user.email` to the author of the last commit, so anyone else sets their
      own with `git -C ~/dotfiles config user.email <you>` or skips signing by
      not having `~/.ssh/id_ed25519.pub`. Owner: switch the remote to SSH to
      push (`git remote set-url origin git@github.com:scv3lqq/dotfiles.git`).
   7. Optional, macOS: Claude Code (not installed by the script) picks up the
      Stop hook; restart it after `install.sh` (it may rewrite
      `~/.claude.json` from memory).
6. `## What gets installed`: per OS, a bullet list of packages exactly as in
   the new `install.sh` (macOS formulae + casks, Linux apt and dnf names plus
   the Neovim tarball, tree-sitter CLI binary, Starship script), each group
   with what needs it. Then `### Not installed on Linux`: fd, bat, eza, yazi,
   lazygit, lazydocker, fast-syntax-highlighting, yarn: so `y`, `lzd`, the
   fzf previews and `:MarkdownPreview` are unavailable. Then
   `### Install by hand (macOS)`: the existing Zen/Obsidian/Telegram/Spotify
   table. Do not duplicate install commands from `install.sh`.
7. `## Layout`: keep the existing table, still accurate; add
   `~/.zshenv` (written, sets ZDOTDIR) if not already clear.
8. `## Updating`: `git -C ~/dotfiles pull`; re-run `./install.sh` when it
   changed (idempotent: packages skip, links are re-made, `~/.zshenv`
   rewritten); after a pull that changed `nvim/lazy-lock.json`, run
   `:Lazy restore` (not `:Lazy sync`, which rewrites the lock); macOS
   topgrade: keep the existing text but replace the pointer to the plan with a
   copy-paste block that writes `~/Library/LaunchAgents/local.topgrade.plist`
   (content identical to the owner's file: Label `local.topgrade`,
   ProgramArguments `/bin/zsh -lc topgrade`, StartCalendarInterval Hour 22
   Minute 0, StandardOutPath and StandardErrorPath
   `$HOME/Library/Logs/topgrade.log` expanded by the shell heredoc) and loads
   it with `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.topgrade.plist`.
9. `## tmux`: keep the table, add rows: `prefix + C-l` clear screen (C-l is
   taken by the navigator), copy mode `v` / `y` (vi keys), `prefix + C-s` /
   `prefix + C-r` save / restore (tmux-resurrect), and a line that
   tmux-continuum saves every 5 minutes and restores on tmux start. Note that
   tmux-assistant-resurrect writes SessionStart/SessionEnd hooks into
   `~/.claude/settings.json` (and `~/.cursor/hooks.json`) on every tmux start,
   on servers too. Config needs tmux 3.3+.
10. `## AeroSpace keybindings`: keep as is.
11. `## Karabiner` (new, short): Right Control + h/j/k/l send arrow keys (any
    other modifiers pass through); Caps Lock is remapped to Right Control only
    for two specific keyboards (the owner's MacBook Air internal keyboard,
    vendor 1452 product 641, and an external one, vendor 1241 product 661). On
    other keyboards add the Caps Lock remap in Karabiner-Elements >
    Simple Modifications with that keyboard as the target device.
12. `## Shell`: keep the alias table and the note.
13. `## Verifying config changes`: keep the commands; add
    `aerospace reload-config --dry-run`; note that `tmux source-file` must run
    inside a tmux session and `luac` comes from `brew install lua`;
    `./install.sh` is not a check.

Definition of done: every section above present, every package list matches
`install.sh` token for token, no em dash (`grep -c $'\u2014' README.md` is 0),
every path and key mentioned exists in the repo configs.

### T4: container e2e (owner: orchestrator via a general-purpose agent)

After T1 and T2: copy the working tree into fresh `ubuntu:24.04` and
`fedora:latest` containers (aarch64, plus `--platform linux/amd64` for
Ubuntu if emulation works), user `dev` without a password and with NOPASSWD
sudo, `SHELL=/bin/bash`; run `./install.sh`; then check the acceptance items
below that are Linux-observable. Re-run `./install.sh` to prove idempotency.

### T5: reviews (owner: orchestrator)

`plan-reviewer` per T1, T2, T3; then `acceptance-validator` with the T4
report. Fix loop until PASS. Then one commit with explicit pathspecs
(`install.sh zsh/.zshrc README.md plans/fresh-machine-setup.md`) and push.

## Tests / verification

- `bash -n install.sh`
- `zsh -n zsh/.zshrc zsh/.zprofile zsh/aliases.zsh`
- Clean-env zsh start (T2 gate) prints no `go` / `fzf` errors.
- T4 container runs (Linux end to end).
- `grep -c $'\u2014' README.md install.sh zsh/.zshrc` prints 0 for each.

## Edge cases

- Re-run on the owner's Mac: Karabiner and the font exist outside brew, the
  cask loop prints "Skipping" and the script continues.
- Linux machine where a previous run left a broken x86_64 nvim on arm64:
  `nvim --version` fails, version is empty, the tarball is reinstalled.
- Distro nvim 0.9 in /usr/bin: tarball goes to /usr/local/bin, which comes
  first in PATH.
- tree-sitter already installed (any version): left alone.
- glibc < 2.39 on arm64: tree-sitter binary removed, message printed, run
  continues.
- `$USER` empty (docker exec): `id -un` is used instead.

## Rollback / migration notes

Single commit; `git revert <sha>` restores the previous files. Machines that
ran the old Linux installer may have `/usr/local/{bin,lib,share}` owned by uid
1001: `sudo chown root:root /usr/local/bin /usr/local/lib /usr/local/share`
(mentioned to the user, not in README).

## Acceptance criteria

1. `bash -n install.sh` and `zsh -n zsh/.zshrc` pass.
2. Ubuntu 24.04 and Fedora containers: `./install.sh` exits 0 for a
   passwordless sudo user with `SHELL=/bin/bash`; login shell becomes zsh
   (`getent passwd dev` ends in a zsh path listed in `/etc/shells`).
3. Containers: `nvim --version` is 0.11.3+ on the native arch;
   `/usr/local/bin` is owned by root; `tree-sitter --version` works.
4. Containers: `zsh -i -c exit` prints nothing on stderr; PATH has no
   trailing `:/bin` from an empty GOPATH.
5. Containers: after the first nvim start, telescope loads without error,
   tree-sitter parsers in `~/.local/share/nvim/site/parser` include lua and go,
   `:MasonInstall gopls basedpyright yaml-language-server` succeeds.
6. Containers: tmux `prefix + s` popup command runs (fzf present).
7. Containers: second `./install.sh` run exits 0.
8. macOS: on this Mac, with the new `.zshrc`, the five `FZF_*` values are
   unchanged versus HEAD.
9. README contains every section and fact listed in T3; its package lists
   match `install.sh`; no em dash in the three edited files.

## Notes for reviewer

- Risky: the Linux block rewrite (pipes into `sudo tar` / `sudo tee` under
  `set -e` without pipefail), `usermod` vs `chsh`, the cask loop swallowing
  real failures (acceptable: it prints why).
- Expected diff: `install.sh` about +45/-20, `zsh/.zshrc` about +20/-6,
  `README.md` largely rewritten, new `plans/fresh-machine-setup.md`.
