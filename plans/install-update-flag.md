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
