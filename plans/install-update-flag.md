# install.sh --update: pull, top up, upgrade

Design for one command that brings a machine set up with these dotfiles to the
current repo state and upgrades the tools the repo installs. Written for the
`/feature` workflow: this file is the reviewed design, the orchestrator appends
the Workflow sections (Gates, Shared definitions, Tasks, Not doing) below it.

## Goal

`~/dotfiles/install.sh --update`, on macOS and on Linux (apt or dnf):

1. pulls the repo (`--ff-only`) and continues with the NEW `install.sh`;
2. does everything a plain run does (installs what is missing, re-links
   configs, TPM, `~/.zshenv`, notify hook, signing, default shell);
3. upgrades the tools this repo installs, and only those;
4. brings tmux plugins and Neovim plugins/parsers to the repo state;
5. prints a short summary.

`./install.sh` without arguments keeps its current behavior and output.

Non-goals: system-wide upgrades (`apt upgrade`, `dnf upgrade` without a
package list, `brew upgrade` of formulae outside the list, macOS updates; on
servers they can restart services, on macOS topgrade already runs daily);
`:Lazy sync` / `:Lazy update` (changing `nvim/lazy-lock.json` is a deliberate,
committed act); git hooks; a separate update script; a shell alias; go.nvim
binaries (`:GoUpdateBinaries`); Intel macOS, RHEL family (see
`plans/fresh-machine-setup.md`).

## Current behavior (commit 64109b4, verify anchors before planning)

`install.sh` (bash, `set -e`, no `pipefail`), top to bottom:

- `:4` `DOTFILES="$HOME/dotfiles"`, `:6` `OS="$(uname -s)"`. No argument parsing.
- `:11-28` macOS: Homebrew bootstrap, one `brew install` of 23 formulae
  (`:19-22`), then a loop that installs each of 4 casks and only warns on
  failure (casks installed by hand outside brew make brew exit 1).
- `:30-76` Linux: arch case (`nvim_arch`, `ts_arch`), apt or dnf package
  line (`:43-44`, `:46-47`), else exit 1; Neovim tarball into `/usr/local`
  when `nvim` is missing or older than 0.11.3 (`:53-59`); tree-sitter CLI
  from GitHub releases when no working one (`:61-71`, checks the version
  output, removes a broken download); Starship install script when missing
  (`:73-75`).
- Stow / `ln -sf` links, TPM clone, `~/.zshenv`, macOS Claude Code notify
  hook, commit signing for this repo, default shell (`chsh` on macOS,
  `sudo usermod` on Linux), `echo "Done."`.

Facts established in `plans/fresh-machine-setup.md` (container runs):
lazy.nvim does not retry failed builds; the first nvim start rewrites the
lazy.nvim line of `nvim/lazy-lock.json` because `nvim/init.lua` bootstraps
lazy.nvim from its `stable` branch, and `:Lazy restore` alone does not undo
it, while `git checkout nvim/lazy-lock.json` + `nvim --headless "+Lazy!
restore" +qa` does; mason-lspconfig skips `ensure_installed` in headless mode;
a nvim first start can stop at "Press ENTER" (interactive only).

## Design

### Interface

- `./install.sh`: install mode (unchanged).
- `./install.sh --update`: update mode.
- `./install.sh -h` / `--help`: usage on stdout, exit 0.
- Any other argument, or more than one: usage on stderr, exit 2.

Usage text (exact):

```
Usage: install.sh [--update]

  (no flag)  install packages, link configs, set up the shell; safe to re-run
  --update   git pull --ff-only, then the same as above, plus upgrade the
             tools this repo installs and sync tmux and Neovim plugins
```

### Pull and re-exec

Placed right after `OS=...` and the argument parsing, before package
installation. `git pull` can rewrite `install.sh` while bash is executing it,
and bash reads a script incrementally: the pull and the `exec` must sit in ONE
compound command (an `if` block), which bash parses completely before running
it. Behavior:

- Only when the mode is update and `DOTFILES_PULLED` is unset.
- Record `old_head="$(git -C "$DOTFILES" rev-parse HEAD)"`, print
  `Pulling $DOTFILES...`, run `git -C "$DOTFILES" pull --ff-only`.
- On failure (diverged branch, local changes the pull would overwrite, no
  upstream, no network): print
  `git pull failed: fix it in $DOTFILES, then re-run install.sh --update`
  and exit 1 before anything else runs.
- On success: `DOTFILES_PULLED="$old_head" exec "$DOTFILES/install.sh" --update`.
  The re-executed run sees `DOTFILES_PULLED` set, skips the pull and uses the
  value for the summary.

### Package lists, single source of truth

Move the four lists into bash arrays declared once near the top (same tokens,
same order as today): `brew_formulae`, `brew_casks`, `apt_packages`,
`dnf_packages`. Both modes use them. `README.md` keeps listing the same tokens.

### Upgrades in update mode

macOS (brew):

- `brew update` before installing.
- The existing install of `brew_formulae` and the cask loop run as today.
- Then `brew upgrade` for `brew_formulae`. For casks, upgrade only those brew
  manages (`brew list --cask <name>` succeeds; the name is the last path
  segment of `nikitabobko/tap/aerospace`); a cask installed by hand is skipped
  silently. A failed upgrade prints a warning and the run goes on (same style
  as the cask install loop). Verify how `brew upgrade <up-to-date formula>`
  exits; keep the run green when nothing is outdated. Casks with
  `auto_updates` (Ghostty) are skipped by brew without `--greedy`: correct,
  they update themselves.

Linux apt: no extra command. `apt-get install` on an installed package
upgrades it when a newer candidate exists and leaves everything else alone
(apt-get(8): "This is also the target to use if you want to upgrade one or
more already-installed packages without upgrading every other package on the
system"). The existing `apt-get update` + install line already does it.

Linux dnf: after the existing install line, `sudo dnf upgrade -y` with
`dnf_packages` (upgrades only those packages and what they need).

Linux tools outside the package manager, shared helpers (defined once):

- `latest_release <owner/repo>`: latest release version without a leading
  `v`, from the redirect of `https://github.com/<owner/repo>/releases/latest`
  (`curl -fsSLI -o /dev/null -w '%{url_effective}'`, take what follows
  `/tag/v` or `/tag/`); no API token, no rate limit; prints nothing on
  failure. Verify the redirect for neovim/neovim, tree-sitter/tree-sitter,
  starship/starship.
- `version_lt <a> <b>`: true when a < b by `sort -V`, false when equal. The
  existing 0.11.3 check is rewritten with it (same result).
- Neovim: install mode keeps "missing or older than 0.11.3". Update mode
  reinstalls when the installed version is older than `latest_release
  neovim/neovim`. Whenever the tarball is extracted over an existing
  `/usr/local/bin/nvim`, first remove `/usr/local/share/nvim/runtime` and
  `/usr/local/lib/nvim` (sudo): files dropped by the new release must not
  linger in the runtime path. Keep `--no-same-owner`.
- tree-sitter CLI: the current download block becomes one function used by
  both modes. Update mode re-downloads when `command -v tree-sitter` is
  `/usr/local/bin/tree-sitter` (ours) and its version (second field of
  `tree-sitter --version`) is older than `latest_release
  tree-sitter/tree-sitter`. A tree-sitter elsewhere (distro, cargo) is left
  alone.
- Starship: update mode re-runs `curl -sS https://starship.rs/install.sh | sh
  -s -- -y` when `command -v starship` is `/usr/local/bin/starship` and its
  version (`starship --version`, first line, second field) is older than
  `latest_release starship/starship`.
- When `latest_release` returns nothing: print
  `Could not check the latest <tool> release, keeping <version>` and go on.

On macOS Neovim, tree-sitter-cli and Starship come from brew and are covered
by the brew upgrade.

### Plugins in update mode

Run after the default-shell block, before `Done.`. A failure in this section
prints a warning and does not abort the run.

- tmux: `~/.tmux/plugins/tpm/bin/install_plugins` (new plugins in
  `.tmux.conf`), then `~/.tmux/plugins/tpm/bin/update_plugins all`. Verify in
  a container whether they need a running tmux server; if they do, decide how
  to provide one (and stop it afterwards) in the plan.
- Neovim plugins, only when `nvim` exists:
  - If `git -C "$DOTFILES" diff --quiet -- nvim/lazy-lock.json` fails (local
    changes): print
    `Skipping Neovim plugins: nvim/lazy-lock.json has local changes (commit or discard them, then re-run)`
    and skip the Neovim steps. Never discard a user's lock edits.
  - Else run `nvim --headless "+Lazy! restore" +qa`. If the lock is dirty
    afterwards (the lazy.nvim self entry), `git -C "$DOTFILES" checkout --
    nvim/lazy-lock.json` and run the restore once more. The lock must end
    clean. Verify that missing plugins get installed and changed plugins get
    their `build` run in headless mode.
  - Tree-sitter parsers: update them headless with nvim-treesitter's `main`
    branch API (`require("nvim-treesitter").update()` and `:wait(...)`, the
    same pattern the T4 runs used for `install`); verify the API at the
    pinned commit.
  - Mason packages: upgrade them only if mason.nvim at the commit pinned in
    `nvim/lazy-lock.json` offers a reliable headless way to upgrade installed
    packages and wait for it (check with context7 and in a container). If
    not, leave Mason out, list it under Not doing, and README tells the user:
    `:Mason`, then `U`.

### Summary (update mode, before `Done.`)

- `Dotfiles: <old_short>..<new_short> (<n> commits)` when HEAD moved, else
  `Dotfiles already up to date (<short>)`. Use `git rev-list --count`.
- `Open a new shell (or run tmux-reload) to load zsh changes.`

### README.md

- `## Updating`: replace the `git -C ~/dotfiles pull` block and its bullets
  with `~/dotfiles/install.sh --update` and what it does / does not do per OS
  (exactly as implemented, including the Mason decision). Keep the topgrade
  text and plist block. Keep `:Lazy restore` advice only where it is still
  needed.
- `## First run` step 3: mention that `install.sh --update` also performs the
  lazy-lock fix after the first start.
- Package lists stay identical to the arrays, token for token.

## Workspace

`~/dotfiles` is the live checkout: configs are symlinked into it, and other
sessions commit to `main` there. Do all work in a git worktree outside it:
`git worktree add ~/dotfiles-worktrees/install-update-flag -b feat/install-update-flag`.
No push, no merge into `main`: the user merges. Remove nothing in
`~/dotfiles`.

## Constraints

- Keep `#!/usr/bin/env bash`, `set -e`, no `pipefail`; keep macOS/Linux
  branching; macOS-only steps never run on Linux.
- Install mode must behave as before. Allowed refactors: the arrays, the two
  helpers, the tree-sitter function, the stale-runtime removal before
  re-extracting Neovim over an existing install.
- Files in scope: `install.sh`, `README.md`, and the plan itself. Do not touch
  `zsh/`, `nvim/`, `.tmux.conf`, `CLAUDE.md`, `AGENTS.md`, `everything.md`.
- Never run `install.sh` on the host (it mutates `$HOME`), never `brew
  install` on the host. Linux behavior is proven in Docker containers
  (colima: start it, stop it when done); the macOS branch is proven with
  `bash -n`, shellcheck and a stubbed run (fake `brew` on `PATH` logging its
  arguments, scratch `HOME`, real repo copy at `$HOME/dotfiles`).
- No em dash character anywhere. Comments only for "why".

## Acceptance criteria

Container recipe: as in `plans/fresh-machine-setup.md` T4 (user `dev`
without password, NOPASSWD sudo, `SHELL=/bin/bash`, repo copied from a
read-only mount; for pull tests make `origin` a local bare clone inside the
container and push test commits to it).

1. `bash -n install.sh`; shellcheck (`koalaman/shellcheck:stable` in Docker)
   reports nothing new compared with `main`.
2. `./install.sh --help` exits 0 and prints the usage; `./install.sh --bogus`
   exits 2 with the usage on stderr.
3. Plain `./install.sh` on fresh ubuntu:24.04 and fedora:latest still exits 0
   and leaves nvim, tree-sitter, Starship, links and login shell as before.
4. A test commit pushed to the bare origin that adds a marker line to
   `install.sh`: `--update` prints `Pulling`, then the marker (proves the new
   script ran), exits 0, and HEAD equals the origin HEAD.
5. A local commit diverging from origin: `--update` exits 1 with the pull
   failure message and prints nothing from the package section.
6. Older Neovim (e.g. v0.11.5 tarball in `/usr/local`): `--update` installs
   the latest release; `nvim --version` matches `latest_release`; no file
   under `/usr/local/share/nvim/runtime` is absent from the new tarball.
7. Older tree-sitter in `/usr/local/bin` (e.g. v0.26.1) and older Starship:
   `--update` brings both to their latest release.
8. Lock handling: after a first nvim start (lazy.nvim line rewritten),
   `--update` leaves `nvim/lazy-lock.json` clean and lazy.nvim at the locked
   commit; with a deliberate local edit in the lock, `--update` prints the
   skip message and the edit is still there.
9. A test commit adding a tmux plugin to `.tmux.conf`: after `--update` the
   plugin directory exists under `~/.tmux/plugins/`.
10. fedora: the `--update` log shows the `dnf upgrade -y` of `dnf_packages`.
11. A second `--update` with nothing new exits 0 and prints
    `Dotfiles already up to date`.
12. macOS stubbed run: `--update` calls `brew update`, the install, `brew
    upgrade` with exactly `brew_formulae`, and `brew upgrade --cask` only for
    brew-managed casks; plain mode never calls `brew update` or `brew
    upgrade`.
13. `README.md` documents `--update` as implemented; its package lists match
    the arrays; no em dash in changed files.

---

# Workflow sections

Appended by the orchestrator after the review. The design sections above are
unchanged and win over anything below; where research contradicted a design
premise, the decision and its evidence are in "Research findings".

Worktree: `$HOME/dotfiles-worktrees/install-update-flag`, branch
`feat/install-update-flag`, base `46b8cb1` (main). Below, `W` is that path and
`SP` is the session scratchpad
`/private/tmp/claude-501/-Users-me-dotfiles/6aa84775-dce8-4ab8-b5eb-9967371c6e00/scratchpad`.
Colima mounts only `$HOME` into Docker: mount paths under `W`, pass
scratchpad files with `docker cp` or stdin.

## Research findings

- R1. `curl -fsSLI -o /dev/null -w '%{url_effective}' https://github.com/<repo>/releases/latest`
  ends at `.../releases/tag/v0.12.6` (neovim), `v0.27.1` (tree-sitter),
  `v1.26.0` (starship) on 2026-10-14. On failure curl still prints the
  requested URL and exits non-zero, so `latest_release` checks the exit code
  and the `/tag/` part.
- R2. `brew upgrade --dry-run jq stow` (both current) prints
  `Warning: jq 1.8.2 already installed` and exits 0: an up-to-date formula
  keeps the run green.
- R3. Design premise wrong: a cask NAMED on the command line is upgraded even
  with `auto_updates`. `brew upgrade --cask --dry-run ghostty` reports
  `ghostty 1.2.3 -> 1.3.1` although the app already is 1.3.1 (it updated
  itself). `brew outdated --cask --quiet` without `--greedy` leaves Ghostty
  out and prints short tokens (`aerospace` for `nikitabobko/tap/aerospace`).
  Decision: upgrade a listed cask only when `${cask##*/}` is a line of
  `brew outdated --cask --quiet`. Such a cask is brew-managed by definition,
  so this keeps the design's "only casks brew manages" and its "auto_updates
  casks are left to themselves".
- R4. TPM (`scripts/helpers/plugin_functions.sh`) reads its path with
  `tmux start-server\; show-environment -g TMUX_PLUGIN_MANAGER_PATH`. Container:
  with no server running `bin/install_plugins` works (rc 0) because that call
  starts a temporary server from `~/.tmux.conf`, which sources every plugin;
  tmux-continuum (`@continuum-restore 'on'`) then restores the saved sessions
  in the background when the server has just started. Inside tmux TPM talks to
  the live server. Decision: run both TPM scripts against a private server
  (`tmux -S <tmpdir>/tmux -f /dev/null new-session -d`, TPM path set with
  `set-environment`, `TMUX=<socket>,0,0` for the two scripts), then kill it.
  Container: install rc 0, update rc 0, a plugin added to `.tmux.conf` gets
  installed, a running user server keeps its session. `pgrep -x tmux` never
  matches a server (its name is `tmux: server`): check with `pgrep -f '^tmux'`.
- R5. Container, fresh `ubuntu:24.04`: `nvim --headless "+Lazy! restore" +qa`
  as the first start installs all 35 plugins, runs their builds
  (`telescope-fzf-native.nvim/build/libfzf.so`), takes about 4 minutes, rc 0,
  no "Press ENTER" hang, and leaves the lock dirty in the `lazy.nvim` line only.
  `git checkout -- nvim/lazy-lock.json` plus a second restore: lock clean,
  lazy.nvim at the locked commit. A plugin moved off its locked commit with
  its `build/` deleted: restore puts it back and rebuilds it.
- R6. Design inconsistency: "skip on any local change of the lock" would skip
  exactly the case AC8 and the README First-run item need (after the first
  interactive start the lock differs in the `lazy.nvim` line only). Decision:
  a diff whose changed lines all contain `"lazy.nvim":` is the bootstrap's
  rewrite and is reset with `git checkout`; any other changed line is the
  user's, and the Neovim steps are skipped with the design's message.
- R7. nvim-treesitter at the locked `5cb05e1`: `update(languages?, options?)`
  is `a.async`, so it returns a task with `:wait(timeout)`; it resolves to
  `true` when every parser installed (`install` returns `done == #tasks`);
  `:wait` raises on timeout. Container: a parser whose install was cut short
  by `+qa` (the config starts async installs on every start) has a `.so`
  without `site/parser-info/<lang>.revision`; `update()` then dies on an
  assert in `util.read_file`. Decision: force-reinstall installed parsers
  that lack a revision file, then `update()`. A Lua error in
  `nvim --headless -c 'lua error("x")' -c qa` exits 0, so the Lua runs in
  `pcall` and ends with `cquit 1` on failure.
- R8. mason.nvim at the locked `2a6940a`: headless `:MasonUpdate` and
  `:MasonInstall` block until done (`doc/mason.txt`: "Runs in blocking fashion
  if there are no UIs attached"); `:MasonInstall` exits nvim with `1cq` when a
  package fails or is unknown (container: rc 1). `mason-registry`
  `get_installed_packages()`, `Package:get_installed_version()` (string or nil)
  and `get_latest_version()` are synchronous. Container: `stylua@v0.20.0`
  upgraded to 2.6.0 by the outdated-then-`MasonInstall` snippet, rc 0; a run
  with nothing outdated is rc 0. Decision: Mason is upgraded by `--update`.
- R9. Container `fedora:latest`: `dnf upgrade -y <dnf_packages>` exits 0 and
  upgrades only those packages and their dependencies.
- R10. shellcheck 0.11.0 on `46b8cb1:install.sh` reports exactly one finding:
  SC2016 (info) at `echo 'export ZDOTDIR="$HOME/.config/zsh"' > ~/.zshenv`
  (intended).

## Gates

Run from any directory; every path is absolute. Never run `install.sh` on the
host except through G6 (scratch HOME, stubs).

- G1 syntax: `bash -n $HOME/dotfiles-worktrees/install-update-flag/install.sh`
  exits 0.
- G2 shellcheck parity with main (R10): prints exactly `SC2016 `.

```sh
docker run --rm -i koalaman/shellcheck:stable -f gcc - < $HOME/dotfiles-worktrees/install-update-flag/install.sh | grep -o 'SC[0-9]*' | tr '\n' ' '
```

- G3 interface, in a container (the script exits before touching anything):
  prints `--help rc=0 match=yes`, `-h rc=0 match=yes`, `--bogus rc=2 match=yes`,
  `two-args rc=2 match=yes`.

```sh
bash -s <<'EOF'
W=$HOME/dotfiles-worktrees/install-update-flag
want="$(awk '/^Usage: install.sh/{f=1} f{print} f&&/sync tmux and Neovim plugins$/{exit}' "$W/plans/install-update-flag.md")"
run() { docker run --rm -i ubuntu:24.04 bash -s -- "$@" <"$W/install.sh"; }
m() { [[ "$1" == "$want" ]] && echo yes || echo no; }
out="$(run --help 2>/dev/null)"; echo "--help rc=$? match=$(m "$out")"
out="$(run -h 2>/dev/null)"; echo "-h rc=$? match=$(m "$out")"
err="$(run --bogus 2>&1 >/dev/null)"; echo "--bogus rc=$? match=$(m "$err")"
err="$(run --update extra 2>&1 >/dev/null)"; echo "two-args rc=$? match=$(m "$err")"
EOF
```

- G4 package lists: the four arrays hold the tokens of `46b8cb1:install.sh`
  in the same order, and README.md names every token in inline code. Prints
  `arrays differing from 46b8cb1: none; tokens missing from README: none`,
  exits 0.

```sh
python3 - $HOME/dotfiles-worktrees/install-update-flag <<'EOF'
import pathlib
import re
import subprocess
import sys

root = pathlib.Path(sys.argv[1])
script = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else root / "install.sh"
new = script.read_text()
old = subprocess.run(
    ["git", "-C", str(root), "show", "46b8cb1:install.sh"],
    capture_output=True, text=True, check=True,
).stdout


def array(name: str) -> list[str]:
    m = re.search(rf"^{name}=\(([^)]*)\)", new, re.M)
    return m.group(1).split() if m else []


def old_tokens(pattern: str) -> list[str]:
    m = re.search(pattern, old, re.S)
    assert m, pattern
    return m.group(1).replace("\\\n", " ").split()


want = {
    "brew_formulae": old_tokens(r"brew install (stow.*?gh)\n"),
    "brew_casks": old_tokens(r"for cask in (.*?); do"),
    "apt_packages": old_tokens(r"apt-get install -y (stow.*?zsh-autosuggestions)\n"),
    "dnf_packages": old_tokens(r"dnf install -y (stow.*?zsh-autosuggestions)\n"),
}
bad = [name for name, tokens in want.items() if array(name) != tokens]
prose = re.sub(r"^[ \t]*```.*?^[ \t]*```", "", (root / "README.md").read_text(), flags=re.S | re.M)
readme = set(re.findall(r"`([^`\n]+)`", prose))
missing = sorted({t for tokens in want.values() for t in tokens} - readme)
print(f"arrays differing from 46b8cb1: {bad or 'none'}; tokens missing from README: {missing or 'none'}")
sys.exit(1 if bad or missing else 0)
EOF
```

- G5 no em dash: `grep -c $'\u2014' install.sh README.md plans/install-update-flag.md`
  (absolute paths under `W`) prints `0` for each file.
- G6 macOS stubbed run (AC12, written by T3): `bash $SP/e2e/mac-stub.sh`
  prints `PASS` for every check and exits 0.
- G7 Linux containers (AC3 to AC11, written by T3): `bash $SP/e2e/linux-e2e.sh`
  exits 0; logs in `$SP/e2e/logs/`. Takes 20 to 40 minutes.

Full Gates after the T1/T2 wave: G1 to G5. G6 and G7 run in T3 and again
(G6 fully, G7 from its logs) in validation.

## Shared definitions

- Mode variable: `mode` is `install` or `update`; set once by the argument
  `case`, never changed.
- `DOTFILES_PULLED`: environment variable set only on the re-exec, holding the
  full HEAD sha from before the pull; the update run uses it for the summary.
- Exact output lines added by this feature (T1 prints them, T3 greps them;
  `<...>` is filled at run time, everything else is literal):
  - M1 `Pulling <DOTFILES>...`
  - M2 `git pull failed: fix it in <DOTFILES>, then re-run install.sh --update`
  - M3 `Updating Homebrew...`
  - M4 `Warning: brew update failed, upgrading from the current package index`
  - M5 `Upgrading packages (macOS)...`
  - M6 `Warning: brew could not upgrade every formula, see the errors above`
  - M7 `Skipping <cask>: brew could not upgrade it`
  - M8 `Could not check the latest <Tool> release, keeping <version>` with
    `<Tool>` one of `Neovim`, `tree-sitter`, `Starship`
  - M9 `Updating Neovim <old> to <new>...`, `Updating tree-sitter CLI <old> to <new>...`,
    `Updating Starship <old> to <new>...`
  - M10 `Could not update tree-sitter CLI: download failed or the new binary does not run, keeping <version>`
  - M11 `Updating tmux plugins...`
  - M12 `Warning: tmux plugins were not fully updated, see the output above`
  - M13 `Skipping Neovim plugins: nvim/lazy-lock.json has local changes (commit or discard them, then re-run)`
  - M14 `Restoring Neovim plugins to nvim/lazy-lock.json...`
  - M15 `Warning: nvim/lazy-lock.json still differs from the repo after the restore`
  - M16 `Updating tree-sitter parsers...`
  - M17 `Updating Mason packages...`
  - M18 `Warning: Neovim plugins were not fully updated, see the output above`
  - M19 `Dotfiles: <old_short>..<new_short> (<n> commits)` or
    `Dotfiles already up to date (<short>)`
  - M20 `Open a new shell (or run tmux-reload) to load zsh changes.`
- Install-mode output stays as on main: none of M1 to M20 appear without
  `--update`.

## Tasks

### T1: install.sh (owner: implementer)

Scope: `install.sh` only. Depends on nothing.

Anchors verified at `46b8cb1`: lines 1-76 are the header and the
"Package installation" block (ends with the Linux `fi` on line 76); lines
78-190 are Stow, TPM, `~/.zshenv`, Claude Code notifications, commit signing
and default shell; line 192 is `echo "Done."`.

Edits:

1. Replace lines 1-76 with Snippet A, byte for byte (two-space indent, the
   heredoc bodies and their `EOF` lines start in column 0).
2. Replace line 192 (`echo "Done."`) with Snippet B, byte for byte. Line 191
   (the blank line before it) stays.
3. Lines 77-191 do not change.

Snippet A:

```bash
#!/usr/bin/env bash
set -e

DOTFILES="$HOME/dotfiles"

OS="$(uname -s)"

# README.md lists the same packages: change both together
brew_formulae=(
  stow neovim tmux starship fzf fd bat eza yazi jq
  zsh-fast-syntax-highlighting zsh-autosuggestions zsh-completions
  lazygit lazydocker topgrade terminal-notifier
  ripgrep tree-sitter-cli go node yarn gh
)
brew_casks=(ghostty karabiner-elements font-jetbrains-mono-nerd-font nikitabobko/tap/aerospace)
apt_packages=(
  stow zsh curl git jq tmux fzf ripgrep make gcc unzip
  python3-venv nodejs npm golang-go zsh-autosuggestions
)
dnf_packages=(
  stow zsh curl git jq tmux fzf ripgrep make gcc unzip
  python3 nodejs npm golang zsh-autosuggestions
)

# =============================================================================
# Helpers
# =============================================================================
usage() {
  cat <<'EOF'
Usage: install.sh [--update]

  (no flag)  install packages, link configs, set up the shell; safe to re-run
  --update   git pull --ff-only, then the same as above, plus upgrade the
             tools this repo installs and sync tmux and Neovim plugins
EOF
}

version_lt() {
  [[ "$1" != "$2" && "$(printf '%s\n' "$1" "$2" | sort -V | head -1)" == "$1" ]]
}

# The redirect of /releases/latest names the tag: no API token, no rate limit
latest_release() {
  local url
  url="$(curl -fsSLI -o /dev/null -w '%{url_effective}' "https://github.com/$1/releases/latest" 2>/dev/null)" || return 0
  [[ "$url" == */tag/* ]] || return 0
  url="${url##*/tag/}"
  echo "${url#v}"
}

# Downloads before touching the install, so a failed download leaves the old
# Neovim working. The old runtime goes before extracting: files a release
# dropped must not linger in the runtime path.
install_nvim() {
  local tarball
  tarball="$(mktemp)"
  curl -fsSL -o "$tarball" "https://github.com/neovim/neovim/releases/latest/download/nvim-linux-$1.tar.gz"
  if [[ -e /usr/local/bin/nvim ]]; then
    sudo rm -rf /usr/local/share/nvim/runtime /usr/local/lib/nvim
  fi
  # --no-same-owner: as root tar would keep the archive's uid on /usr/local/{bin,lib,share}
  sudo tar -C /usr/local -xzf "$tarball" --strip-components=1 --no-same-owner
  rm -f "$tarball"
}

# Checks the version output, not the exit code: a failed or interrupted
# download leaves an empty file that bash runs as an empty script (exit 0).
# The temporary name keeps a working binary in place when the new one fails.
install_tree_sitter() {
  local new=/usr/local/bin/tree-sitter.new
  curl -fsSL "https://github.com/tree-sitter/tree-sitter/releases/latest/download/tree-sitter-linux-$1.gz" |
    gunzip | sudo tee "$new" >/dev/null
  sudo chmod 755 "$new"
  if ! "$new" --version 2>/dev/null | grep -q '^tree-sitter '; then
    sudo rm -f "$new"
    return 1
  fi
  sudo mv -f "$new" /usr/local/bin/tree-sitter
}

# TPM asks a tmux server for its plugin path. With no server running it starts
# one from ~/.tmux.conf, which loads every plugin (tmux-continuum then
# restores the saved sessions); inside tmux it uses the live server. A private
# server without a config avoids both.
sync_tmux_plugins() {
  local dir rc=1
  dir="$(mktemp -d)"
  if tmux -S "$dir/tmux" -f /dev/null new-session -d &&
    tmux -S "$dir/tmux" set-environment -g TMUX_PLUGIN_MANAGER_PATH "$HOME/.tmux/plugins/"; then
    rc=0
    TMUX="$dir/tmux,0,0" ~/.tmux/plugins/tpm/bin/install_plugins || rc=1
    TMUX="$dir/tmux,0,0" ~/.tmux/plugins/tpm/bin/update_plugins all || rc=1
  fi
  tmux -S "$dir/tmux" kill-server 2>/dev/null
  rm -rf "$dir"
  return "$rc"
}

# lazy.nvim bootstraps itself from its stable branch, so the first start
# rewrites the "lazy.nvim" line of the lock. That line is reset; any other
# change is the user's and is kept.
sync_nvim_plugins() {
  local lock=nvim/lazy-lock.json rc=0 lua

  if git -C "$DOTFILES" diff --no-color -U0 -- "$lock" | grep -E '^[-+]' | grep -Ev '^(---|\+\+\+) ' |
    grep -vq '"lazy.nvim":'; then
    echo "Skipping Neovim plugins: nvim/lazy-lock.json has local changes (commit or discard them, then re-run)"
    return 0
  fi

  echo "Restoring Neovim plugins to nvim/lazy-lock.json..."
  git -C "$DOTFILES" checkout -- "$lock"
  nvim --headless "+Lazy! restore" +qa || rc=1
  if ! git -C "$DOTFILES" diff --quiet -- "$lock"; then
    git -C "$DOTFILES" checkout -- "$lock"
    nvim --headless "+Lazy! restore" +qa || rc=1
  fi
  if ! git -C "$DOTFILES" diff --quiet -- "$lock"; then
    echo "Warning: nvim/lazy-lock.json still differs from the repo after the restore"
    rc=1
  fi

  # Headless nvim exits 0 after a Lua error, hence pcall and cquit. A parser
  # whose install was cut short (nvim quit while the config's async install
  # ran) has no revision file and makes update() fail: reinstall those first.
  lua="$(mktemp)"
  cat >"$lua" <<'EOF'
local ok, res = pcall(function()
  local ts, config = require("nvim-treesitter"), require("nvim-treesitter.config")
  local info_dir = config.get_install_dir("parser-info")
  local broken = vim.tbl_filter(function(lang)
    return not vim.uv.fs_stat(info_dir .. "/" .. lang .. ".revision")
  end, config.get_installed("parsers"))
  if #broken > 0 and not ts.install(broken, { force = true }):wait(1800000) then
    return false
  end
  return ts.update(nil, { summary = true }):wait(1800000)
end)
if not ok then
  io.stderr:write(tostring(res), "\n")
end
if not (ok and res) then
  vim.cmd("cquit 1")
end
EOF
  echo "Updating tree-sitter parsers..."
  nvim --headless -c "luafile $lua" +qa || rc=1

  cat >"$lua" <<'EOF'
local ok, err = pcall(function()
  local registry = require("mason-registry")
  registry.refresh()
  local outdated = {}
  for _, pkg in ipairs(registry.get_installed_packages()) do
    if pkg:get_installed_version() ~= pkg:get_latest_version() then
      outdated[#outdated + 1] = pkg.name
    end
  end
  if #outdated > 0 then
    vim.cmd("MasonInstall " .. table.concat(outdated, " "))
  end
end)
if not ok then
  io.stderr:write(tostring(err), "\n")
  vim.cmd("cquit 1")
end
EOF
  echo "Updating Mason packages..."
  nvim --headless -c MasonUpdate -c "luafile $lua" +qa || rc=1
  rm -f "$lua"
  return "$rc"
}

# =============================================================================
# Arguments
# =============================================================================
case "$#:${1-}" in
  0:) mode=install ;;
  1:--update) mode=update ;;
  1:-h | 1:--help)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

# git pull may rewrite this file while bash is still reading it: bash parses
# the whole if block before running it, so the exec comes from the old text
if [[ "$mode" == update && -z "${DOTFILES_PULLED-}" ]]; then
  old_head="$(git -C "$DOTFILES" rev-parse HEAD)"
  echo "Pulling $DOTFILES..."
  if ! git -C "$DOTFILES" pull --ff-only; then
    echo "git pull failed: fix it in $DOTFILES, then re-run install.sh --update"
    exit 1
  fi
  DOTFILES_PULLED="$old_head" exec "$DOTFILES/install.sh" --update
fi

# =============================================================================
# Package installation
# =============================================================================
if [[ "$OS" == "Darwin" ]]; then
  if ! command -v brew &>/dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
  fi

  if [[ "$mode" == update ]]; then
    echo "Updating Homebrew..."
    brew update || echo "Warning: brew update failed, upgrading from the current package index"
  fi

  echo "Installing packages (macOS)..."
  brew install "${brew_formulae[@]}"

  # A copy installed outside brew (DMG app, hand-installed font) makes brew
  # exit 1: keep it and go on
  for cask in "${brew_casks[@]}"; do
    brew install --cask "$cask" || echo "Skipping $cask: brew could not install it (already installed by hand?)"
  done

  if [[ "$mode" == update ]]; then
    echo "Upgrading packages (macOS)..."
    brew upgrade "${brew_formulae[@]}" || echo "Warning: brew could not upgrade every formula, see the errors above"
    # A named cask is upgraded even when it updates itself (Ghostty); brew
    # outdated leaves those out, and casks installed by hand too
    outdated_casks="$(brew outdated --cask --quiet)" || outdated_casks=""
    for cask in "${brew_casks[@]}"; do
      if grep -qxF "${cask##*/}" <<<"$outdated_casks"; then
        brew upgrade --cask "$cask" || echo "Skipping $cask: brew could not upgrade it"
      fi
    done
  fi

elif [[ "$OS" == "Linux" ]]; then
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
    # On an installed package apt-get install takes the newest candidate, so
    # --update needs no extra apt command
    sudo apt-get install -y "${apt_packages[@]}"
  elif command -v dnf &>/dev/null; then
    sudo dnf install -y "${dnf_packages[@]}"
    if [[ "$mode" == update ]]; then
      sudo dnf upgrade -y "${dnf_packages[@]}"
    fi
  else
    echo "No apt-get or dnf: install the packages listed in README.md by hand"
    exit 1
  fi

  # The config needs Neovim 0.11.3+; distro packages are older
  nvim_version="$(nvim --version 2>/dev/null | sed -n '1s/^NVIM v\([0-9.]*\).*/\1/p')"
  if [[ -z "$nvim_version" ]] || version_lt "$nvim_version" 0.11.3; then
    install_nvim "$nvim_arch"
  elif [[ "$mode" == update ]]; then
    nvim_latest="$(latest_release neovim/neovim)"
    if [[ -z "$nvim_latest" ]]; then
      echo "Could not check the latest Neovim release, keeping $nvim_version"
    elif version_lt "$nvim_version" "$nvim_latest"; then
      echo "Updating Neovim $nvim_version to $nvim_latest..."
      install_nvim "$nvim_arch"
    fi
  fi

  if ! tree-sitter --version 2>/dev/null | grep -q '^tree-sitter '; then
    install_tree_sitter "$ts_arch" ||
      echo "Skipping tree-sitter CLI: download failed or the prebuilt binary needs glibc 2.39+, Neovim gets no tree-sitter highlighting"
  elif [[ "$mode" == update && "$(command -v tree-sitter)" == /usr/local/bin/tree-sitter ]]; then
    ts_version="$(tree-sitter --version | awk '{print $2}')"
    ts_latest="$(latest_release tree-sitter/tree-sitter)"
    if [[ -z "$ts_latest" ]]; then
      echo "Could not check the latest tree-sitter release, keeping $ts_version"
    elif version_lt "$ts_version" "$ts_latest"; then
      echo "Updating tree-sitter CLI $ts_version to $ts_latest..."
      install_tree_sitter "$ts_arch" ||
        echo "Could not update tree-sitter CLI: download failed or the new binary does not run, keeping $ts_version"
    fi
  fi

  if ! command -v starship &>/dev/null; then
    curl -sS https://starship.rs/install.sh | sh -s -- -y
  elif [[ "$mode" == update && "$(command -v starship)" == /usr/local/bin/starship ]]; then
    starship_version="$(starship --version | awk 'NR == 1 {print $2}')"
    starship_latest="$(latest_release starship/starship)"
    if [[ -z "$starship_latest" ]]; then
      echo "Could not check the latest Starship release, keeping $starship_version"
    elif version_lt "$starship_version" "$starship_latest"; then
      echo "Updating Starship $starship_version to $starship_latest..."
      curl -sS https://starship.rs/install.sh | sh -s -- -y
    fi
  fi
fi
```

Snippet B:

```bash
# =============================================================================
# Plugins and summary (--update)
# =============================================================================
if [[ "$mode" == update ]]; then
  echo "Updating tmux plugins..."
  sync_tmux_plugins || echo "Warning: tmux plugins were not fully updated, see the output above"

  if command -v nvim &>/dev/null; then
    sync_nvim_plugins || echo "Warning: Neovim plugins were not fully updated, see the output above"
  fi

  if [[ "$(git -C "$DOTFILES" rev-parse HEAD)" == "$DOTFILES_PULLED" ]]; then
    echo "Dotfiles already up to date ($(git -C "$DOTFILES" rev-parse --short HEAD))"
  else
    echo "Dotfiles: $(git -C "$DOTFILES" rev-parse --short "$DOTFILES_PULLED")..$(git -C "$DOTFILES" rev-parse --short HEAD) ($(git -C "$DOTFILES" rev-list --count "$DOTFILES_PULLED..HEAD") commits)"
  fi
  echo "Open a new shell (or run tmux-reload) to load zsh changes."
fi

echo "Done."
```

Must not change: the shebang, `set -e` without `pipefail`, the macOS/Linux
branching, every line from 77 to 191, the install-mode output.

Task gates: G1, G2, G3, G4 (its README half already passes on the base), and
`grep -c $'\u2014' $HOME/dotfiles-worktrees/install-update-flag/install.sh`
prints `0`. Never run `install.sh` on the host.

Definition of done: the four edits are in place; `git -C <W> diff --stat`
lists `install.sh` only; every task gate passes with the output stated in
Gates.

### T2: README.md (owner: implementer)

Scope: `README.md` only. Depends on nothing (the text below describes T1's
behavior exactly).

Edit 1, `## First run`, step 3: after the closing fence of the code block
that ends with `nvim --headless "+Lazy! restore" +qa` (line 135 at `46b8cb1`,
5-space indented ```` ``` ````), insert a blank line and then this paragraph,
each line indented 5 spaces like the fence:

```markdown
     `~/dotfiles/install.sh --update` performs the same fix, so running it
     once after the first start is enough.
```

The blank line between this paragraph and the next bullet
(`   - If a build failed ...`) stays.

Edit 2, `## Updating`: replace the block from the line ```` ```sh ```` right
under the heading through the end of the bullet that ends with
`first start.` (lines 267-276 at `46b8cb1`, i.e. the
`git -C ~/dotfiles pull` code block and both bullets) with exactly:

````markdown
```sh
~/dotfiles/install.sh --update
```

It runs `git pull --ff-only` in `~/dotfiles` and, when the pull fails
(diverged branch, local changes in the way, no network), stops with an error
before changing anything else. Then it runs the pulled `install.sh`, which
does everything a plain run does (installs what is missing, re-links the
configs, rewrites `~/.zshenv`) and also:

- macOS: `brew update`, `brew upgrade` of the formulae listed in
  [What gets installed](#what-gets-installed), and `brew upgrade --cask` of
  the listed casks that `brew outdated --cask` reports. Casks installed by
  hand and casks that update themselves (Ghostty) are left alone.
- Linux, apt: the `apt-get install` of the listed packages already upgrades
  them; nothing else on the system is upgraded.
- Linux, dnf: `dnf upgrade` of the listed packages only.
- Linux, outside the package manager: Neovim, the tree-sitter CLI and
  Starship are replaced by their latest GitHub release when it is newer.
  tree-sitter and Starship are touched only when they live in
  `/usr/local/bin`, where `install.sh` puts them.
- tmux: installs the plugins newly listed in `.tmux.conf` and updates all of
  them. TPM runs against a private tmux server, so your sessions are not
  touched.
- Neovim: restores the plugins to the commits in `nvim/lazy-lock.json`
  (headless `:Lazy restore`, including the lock fix from
  [First run](#first-run)), updates the tree-sitter parsers and upgrades
  outdated Mason packages. Skipped when the lock has local changes other
  than the lazy.nvim line the first start rewrites. Plugins never move past
  the lock: `:Lazy update` and committing the new lock stay a manual step.
- Prints the pulled commit range and reminds you to open a new shell (or run
  `tmux-reload`).

It does not upgrade the rest of the system (`apt upgrade`, a full
`dnf upgrade`, other brew formulae, macOS updates) or go.nvim's tools
(`:GoUpdateBinaries`).
````

Keep the blank line that follows, then the unchanged paragraph starting
that starts with On macOS `topgrade` upgrades, the plist block and the rest
of the file.

Must not change: every other section, the package lists under
`## What gets installed`, the topgrade text and plist block.

Task gates:

- `grep -c $'\u2014' $HOME/dotfiles-worktrees/install-update-flag/README.md` prints `0`.
- `grep -c 'install.sh --update' $HOME/dotfiles-worktrees/install-update-flag/README.md` prints `2`.
- `grep -c 'git -C ~/dotfiles pull' $HOME/dotfiles-worktrees/install-update-flag/README.md` prints `0`.
- `git -C $HOME/dotfiles-worktrees/install-update-flag diff -U0 -- README.md | grep '^@@'`
  shows exactly two hunks: one inserting after old line 135, one replacing
  old lines 267-276.

Definition of done: both edits in place; `git -C <W> diff --stat` lists
`README.md` only; every task gate passes.

### T3: Linux containers and macOS stub run (owner: orchestrator via a general-purpose agent)

Depends on T1 and T2 committed. Writes only under `$SP/e2e/`; touches no file
in `W` or `~/dotfiles`; never runs `install.sh` on the host outside
`mac-stub.sh`; leaves colima running.

Repo transfer: `git -C <W> bundle create $SP/e2e/repo.bundle HEAD feat/install-update-flag`;
`docker cp` it into each container; as user `dev`:
`git clone -q --bare /tmp/repo.bundle ~/origin.git`,
`git clone -q ~/origin.git ~/dotfiles`, `git clone -q ~/origin.git /tmp/pusher`
(test commits are made in `/tmp/pusher` and pushed to `~/origin.git`);
`git config --global user.name e2e`, `user.email e2e@example.invalid`.

Container recipe (both distros, native arch): user `dev` with home
`/home/dev`, login shell `/bin/bash`, NOPASSWD sudo, no password; run every
step as `docker exec -u dev -e HOME=/home/dev -e SHELL=/bin/bash -w /home/dev/dotfiles`.
Ubuntu needs `sudo git` installed as root first; Fedora `sudo git`.

`$SP/e2e/linux-e2e.sh` runs these steps, logs each to
`$SP/e2e/logs/<distro>-<step>.log`, records rc, prints `PASS`/`FAIL` per
check and exits non-zero on any FAIL:

ubuntu:24.04:

1. AC3: `./install.sh` rc 0; `command -v nvim` is `/usr/local/bin/nvim` and
   its version is 0.11.3+; `tree-sitter --version` starts with `tree-sitter `;
   `command -v starship` is `/usr/local/bin/starship`; `~/.tmux.conf` and
   `~/.config/starship.toml` are symlinks into `~/dotfiles`;
   `~/.config/nvim/init.lua` resolves into `~/dotfiles/nvim`;
   `getent passwd dev` ends in a zsh path listed in `/etc/shells`; the log
   holds none of M1 to M20.
2. Simulated first interactive start: `timeout 1800 nvim --headless "+Lazy! restore" +qa`;
   record `git -C ~/dotfiles diff --stat` (expect the lazy.nvim line).
3. AC8 part 1: `./install.sh --update` rc 0; log has M1, M14, M16, M17,
   `Dotfiles already up to date`, M20, `Done.`, and no `Warning:` line; lock
   clean (`git diff --quiet -- nvim/lazy-lock.json`); `git -C
   ~/.local/share/nvim/lazy/lazy.nvim rev-parse HEAD` equals the lazy.nvim
   commit in the lock.
4. Parser and Mason repair: delete the `.revision` file of one installed
   parser (`css` if present, else any), write `0000000` into `lua.revision`
   (both under `~/.local/share/nvim/site/parser-info/`), run
   `timeout 900 nvim --headless -c "MasonInstall stylua@v0.20.0" -c qall`;
   then `./install.sh --update` rc 0, no `Warning:` line, both revision files
   hold a real revision again, `~/.local/share/nvim/mason/bin/stylua --version`
   is newer than 0.20.0.
5. AC8 part 2: change the `mason.nvim` line of `~/dotfiles/nvim/lazy-lock.json`
   (e.g. its branch `main` to `dev`, with python3, not `sed -i`);
   `./install.sh --update` rc 0, log has M13 and not M14; the edit is still in
   `git diff`. Then `git -C ~/dotfiles checkout -- nvim/lazy-lock.json`.
6. AC4 and AC9: in `/tmp/pusher` insert `echo "E2E-MARKER: pulled install.sh runs"`
   as line 3 of `install.sh` and insert `set -g @plugin 'tmux-plugins/tmux-yank'`
   right before the `run '~/.tmux/plugins/tpm/tpm'` line of `.tmux.conf`;
   commit and push. `./install.sh --update` rc 0; the M1 line comes before
   the marker line; `git -C ~/dotfiles rev-parse HEAD` equals
   `git -C ~/origin.git rev-parse HEAD`; log has
   `Dotfiles: <a>..<b> (1 commits)`; `~/.tmux/plugins/tmux-yank` exists;
   `pgrep -f '^tmux'` exits 1 afterwards (no server left).
7. AC5: push one more commit from `/tmp/pusher` (any new file) and commit a
   different new file locally in `~/dotfiles`; `./install.sh --update` rc 1;
   log has M2 and no `Installing packages`. Then `git -C ~/dotfiles reset
   --hard '@{u}'`.
8. AC6 and AC7: replace the tools by older releases: remove
   `/usr/local/bin/nvim`, `/usr/local/share/nvim`, `/usr/local/lib/nvim`,
   extract the v0.11.5 `nvim-linux-<arch>.tar.gz` into `/usr/local` the way
   `install.sh` does, then `sudo touch /usr/local/share/nvim/runtime/e2e-stale.vim`;
   put the v0.26.1 `tree-sitter-linux-<arch>.gz` binary at
   `/usr/local/bin/tree-sitter`; install Starship v1.24.0 into
   `/usr/local/bin` (the release tarball for the arch, or the install script
   with its version flag). Confirm the three old versions, then
   `./install.sh --update` rc 0; log has the three M9 lines; `nvim --version`,
   `tree-sitter --version`, `starship --version` equal the tags behind
   `https://github.com/<repo>/releases/latest` (strip `v`);
   `e2e-stale.vim` is gone; every file under `/usr/local/share/nvim/runtime`
   is listed in the latest tarball (`tar -tzf`, first path component
   stripped).
9. AC11: `./install.sh --update` rc 0; log has `Dotfiles already up to date`
   and none of M9, M2, `Warning:`.
10. Install mode after all that: `./install.sh` rc 0, log holds none of M1
    to M20.

fedora:latest:

1. AC3 as ubuntu step 1.
2. AC10: `env SHELLOPTS=xtrace ./install.sh --update` rc 0 (xtrace follows
   the re-exec); log has
   `+ sudo dnf upgrade -y stow zsh curl git jq tmux fzf ripgrep make gcc unzip python3 nodejs npm golang zsh-autosuggestions`.
3. AC11 as ubuntu step 9.

`$SP/e2e/mac-stub.sh` (G6, AC12), on this Mac, in under a minute:

- Refuses to run unless `uname -s` is `Darwin`; `H=$SP/e2e/mac-home` is
  deleted and recreated; the script aborts unless `H` starts with `$SP/`.
- `git clone -q --bare -b feat/install-update-flag <W> $SP/e2e/mac-origin.git`
  (fresh), `git clone -q $SP/e2e/mac-origin.git $H/dotfiles`.
- Stub dir `$SP/e2e/mac-bin` first on PATH:
  - `brew` appends `brew $*` to `$HOME/brew.log`; `outdated --cask --quiet`
    prints `aerospace` and `some-other-cask`; `install --cask karabiner-elements`
    and `install --cask font-jetbrains-mono-nerd-font` exit 1; everything else
    exits 0.
  - `nvim` appends `nvim $*` to `$HOME/nvim.log`, exits 0.
- `$H/.tmux/plugins/tpm/bin/install_plugins` and `update_plugins` stubs append
  `install TMUX=$TMUX` and `update $* TMUX=$TMUX` to `$HOME/tpm.log` (the TPM
  clone is then skipped). The real Homebrew `tmux` runs the private server.
- Runs: `env -i HOME="$H" PATH="$SP/e2e/mac-bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin" SHELL=/bin/zsh USER="$USER" TERM=dumb bash "$H/dotfiles/install.sh"`
  first, then with `--update` (logs truncated in between). `SHELL=/bin/zsh`
  skips `chsh`; no `~/.ssh/id_ed25519.pub` skips signing.
- Checks, each printed as `PASS`/`FAIL <what>`:
  - plain run rc 0; `brew.log` equals exactly (formulae in array order):

    ```
    brew install stow neovim tmux starship fzf fd bat eza yazi jq zsh-fast-syntax-highlighting zsh-autosuggestions zsh-completions lazygit lazydocker topgrade terminal-notifier ripgrep tree-sitter-cli go node yarn gh
    brew install --cask ghostty
    brew install --cask karabiner-elements
    brew install --cask font-jetbrains-mono-nerd-font
    brew install --cask nikitabobko/tap/aerospace
    ```

    `nvim.log` and `tpm.log` are absent or empty; output holds none of M1 to
    M20.
  - `--update` run rc 0; `brew.log` equals exactly: `brew update`, the five
    lines above, `brew upgrade stow neovim ... gh` (same 23 formulae, same
    order), `brew outdated --cask --quiet`,
    `brew upgrade --cask nikitabobko/tap/aerospace`.
  - `nvim.log` lines start with `nvim --headless +Lazy! restore +qa`, then
    `nvim --headless -c luafile `, then `nvim --headless -c MasonUpdate -c luafile `.
  - `tpm.log` has one `install TMUX=<dir>/tmux,0,0` and one
    `update all TMUX=<dir>/tmux,0,0` line; afterwards `<dir>` does not exist.
  - output has M1, `Dotfiles already up to date`, M20, `Done.`.

Report: per AC (AC3 to AC12) PASS/FAIL with the evidence lines and log
paths, the run time, and anything that contradicts this plan.

### T4: reviews and validation (owner: orchestrator)

`plan-reviewer` per commit (T1, T2); `acceptance-validator` with the T3
report and logs, after both verdicts. Fix loop per the `/feature` workflow.

## Not doing

- Anything in "Non-goals" of the design.
- Changes outside `install.sh`, `README.md` and this plan (no `nvim/`,
  `zsh/`, `.tmux.conf`, `CLAUDE.md`, `AGENTS.md`, `everything.md`).
- Installing the config's missing tree-sitter parsers in update mode: the
  parser list is local to `nvim/lua/plugins/treesitter.lua`; the next
  interactive start installs them as today.
- Retry or timeout tuning for `Lazy! restore` (it reports no exit status).
- A `brew list --cask` probe: R3 replaces it.
- amd64 emulation runs, RHEL family, Intel macOS.
- A test suite or harness inside the repo: the e2e scripts live in the
  scratchpad.
- Push, merge into `main`, removing the worktree: the user does that.

## Follow-up F1: non-blocking fixes after the validator PASS

The acceptance validator passed AC1 to AC13 at `0dc1010` and listed three
non-blocking fixes; all stay inside `install.sh`. Install-mode behavior and
output stay as they are.

### F1: install.sh (owner: implementer)

Scope: `install.sh` only. Anchors verified at `0dc1010`.

1. Line 57, in `install_nvim`: append ` || { rm -f "$tarball"; return 1; }`
   to the `curl -fsSL -o "$tarball" ...` line. The callers stay simple
   commands, so `set -e` still stops the run; only the stray temp file goes.
2. Headless nvim ends its last message without a newline, so the next
   M-line was glued to it (`Successfully updated 1 registry.Dotfiles already
   up to date (...)`). In `sync_nvim_plugins`:
   - right above line 113 (`  nvim --headless "+Lazy! restore" +qa || rc=1`)
     add the comment line
     `  # Headless nvim ends its last message without a newline`
   - right below each of these four lines add an `echo` line with the same
     indentation as the nvim line: 113 (two spaces), 116
     (`    nvim --headless "+Lazy! restore" +qa || rc=1`, four spaces), 147
     (`  nvim --headless -c "luafile $lua" +qa || rc=1`), 169
     (`  nvim --headless -c MasonUpdate -c "luafile $lua" +qa || rc=1`).
3. Fedora 42+ links `/usr/local/sbin` to `bin`; with sbin first in PATH,
   `command -v` names the sbin path and the literal `==` skipped the update.
   - Line 282: `"$(command -v tree-sitter)" == /usr/local/bin/tree-sitter`
     becomes `"$(command -v tree-sitter)" -ef /usr/local/bin/tree-sitter`;
     right above line 282 add, with two spaces of indentation,
     `  # -ef, not ==: Fedora links /usr/local/sbin to bin, and an sbin-first PATH finds the tool there`
   - Line 296: `"$(command -v starship)" == /usr/local/bin/starship` becomes
     `"$(command -v starship)" -ef /usr/local/bin/starship` (no comment).

Must not change: every other line of `install.sh`.

Task gates: G1, G2, G4, G5 (install.sh), and
`git -C $HOME/dotfiles-worktrees/install-update-flag diff --stat`
lists `install.sh` only with 9 insertions and 3 deletions. Never run
`install.sh` on the host.

Definition of done: the three edits in place, every task gate passes.
Verification by the orchestrator afterwards: G3, G6, G7 rerun at the new HEAD;
the fedora xtrace log shows the `tree-sitter --version` call after the `-ef`
test; no update log matches
`grep -nE 'registry\.Dotfiles|\.\.\.Updating|parser(Updating|Warning)'`.
