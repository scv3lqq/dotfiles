# Portable setup: /setup-dotfiles skill, vendored /feature, file moves

## Goal

A fresh clone on another machine gets everything this repo's `CLAUDE.md`
relies on, and a Claude Code skill that runs the setup:

1. `.tmux.conf` moves to `tmux/tmux.conf`, `starship.toml` to
   `starship/starship.toml`. Link targets stay `~/.tmux.conf` and
   `~/.config/starship.toml`.
2. The `/feature` skill and the four agents it dispatches move into the repo
   (`claude/skills/feature/SKILL.md`, `claude/agents/*.md`) as the source of
   truth, copied as is (user decision 2026-10-24: dated notes stay).
   `install.sh` file-links them into `~/.claude/` on macOS and Linux; on this
   machine the live files become those links.
3. `AGENTS.md` becomes a symlink to `CLAUDE.md`; root `plan.md` (a stale
   pre-`plans/` plan) is deleted.
4. A project skill `.claude/skills/setup-dotfiles/SKILL.md` (`/setup-dotfiles`,
   `/setup-dotfiles update`) checks requirements, moves existing configs
   aside, runs `install.sh` in a tmux window or the user's terminal, verifies
   the links, lists the first-run steps left. The README mentions it in its
   first paragraphs.

Current behavior: `install.sh` links `$DOTFILES/.tmux.conf` and
`$DOTFILES/starship.toml` with `ln -sf`; `/feature` and its agents exist only
in `~/.claude/` of this machine; `AGENTS.md` is a separate legacy Codex file.

## Facts verified before planning

- Claude Code 2.1.310 loads an agent whose `~/.claude/agents/<name>.md` is a
  symlink and a skill whose `~/.claude/skills/<name>/SKILL.md` is a symlink
  inside a real directory (probe with `claude -p`, 2026-10-24).
- The Edit tool refuses to write through a symlink and names the target path,
  so edits land in the repo copy and the links survive.
- `disable-model-invocation: true` skills are absent from the model's skill
  list: `/feature` and `/setup-dotfiles` cannot be probed with `claude -p`;
  agents can.
- No other file in the repo or in `~/.claude/{skills,agents,hooks,rules}`
  references `~/dotfiles/.tmux.conf` or `~/dotfiles/starship.toml`;
  `.tmux.conf` itself only references its target `~/.tmux.conf` (line 47)
  and `~/dotfiles/tmux/session-picker.sh`.

## Gates

Run from `$HOME/dotfiles`:

```sh
bash -n install.sh
zsh -n zsh/.zshrc zsh/.zprofile zsh/aliases.zsh
grep -rnE '(^|[ `"(])(\.tmux\.conf|starship\.toml)' README.md CLAUDE.md everything.md install.sh .claude/rules .claude/skills   # expect no output (exit 1)
git diff main...HEAD -- . ':(exclude)claude/skills/feature' ':(exclude)claude/agents' | python3 -c "import sys; print(sum(1 for l in sys.stdin if l.startswith('+') and chr(0x2014) in l))"   # expect 0
awk 'END { exit !(NR <= 199) }' CLAUDE.md   # exit 0
git status --short   # expect empty after the last commit
```

## Acceptance criteria

Each is a command run from `$HOME/dotfiles` with the expected result.

- AC1: `git diff -M --name-status main...HEAD | grep -cE '^R100\s+(\.tmux\.conf\s+tmux/tmux\.conf|starship\.toml\s+starship/starship\.toml)$'` prints `2`.
- AC2: `readlink ~/.tmux.conf` prints `$HOME/dotfiles/tmux/tmux.conf`, `readlink ~/.config/starship.toml` prints `$HOME/dotfiles/starship/starship.toml`, and `test -f ~/.tmux.conf && test -f ~/.config/starship.toml` exits 0.
- AC3: the stale-name `grep -rnE` from Gates prints nothing.
- AC4: each of these prints `1`:
  `grep -cxF 'ln -sf "$DOTFILES/tmux/tmux.conf" ~/.tmux.conf' install.sh`,
  `grep -cxF 'ln -sf "$DOTFILES/starship/starship.toml" ~/.config/starship.toml' install.sh`,
  `grep -cxF 'ln -sf "$DOTFILES/claude/skills/feature/SKILL.md" ~/.claude/skills/feature/SKILL.md' install.sh`,
  `grep -cxF 'ln -sf "$DOTFILES"/claude/agents/*.md ~/.claude/agents/' install.sh`;
  and `awk '/^ln -sf "\$DOTFILES\/claude\/skills/{a=NR} /^echo .export ZDOTDIR/{z=NR} /^# Claude Code notifications \(macOS\)/{n=NR} END{print (z<a && a<n) ? "ok" : "bad"}' install.sh` prints `ok` (the block runs on both OSes, outside the macOS `if`).
- AC5: `diff -r ~/.claude/backups/feature-vendor.2026-10-24/skills/feature claude/skills/feature && diff -r ~/.claude/backups/feature-vendor.2026-10-24/agents claude/agents` exits 0 with no output, and `ls claude/agents` lists exactly `acceptance-validator.md implementer.md plan-reviewer.md skill-dry-run.md`.
- AC6 (post-merge, orchestrator): `readlink ~/.claude/skills/feature/SKILL.md` prints `$HOME/dotfiles/claude/skills/feature/SKILL.md`; for each name in L-AGENTS `readlink ~/.claude/agents/<name>.md` prints `$HOME/dotfiles/claude/agents/<name>.md`; `find ~/.claude/agents -maxdepth 1 -type l | wc -l` prints `4` (the other agents stay regular files).
- AC7 (post-merge, orchestrator): run from an empty temp dir, `env -u TMUX -u TMUX_PANE claude -p --model claude-haiku-5-5 --settings '{"disableAllHooks": true}' 'Answer in one line, no tools: which of these names appear as agent types in your Agent tool description: implementer, plan-reviewer, acceptance-validator, skill-dry-run?'` names all four.
- AC8: `git ls-files -s AGENTS.md` starts with `120000`, `readlink AGENTS.md` prints `CLAUDE.md`, `git ls-files plan.md` prints nothing and `test ! -e plan.md` exits 0, `grep -c legacy CLAUDE.md` prints `0`.
- AC9: `grep -cF 'claude/skills/feature/SKILL.md' CLAUDE.md` prints at least `1`; `grep -cF '~/.claude/skills/feature/SKILL.md' CLAUDE.md` prints `0`; `awk 'END { exit !(NR <= 199) }' CLAUDE.md` exits 0.
- AC10: `.claude/skills/setup-dotfiles/SKILL.md` is byte-identical to the block S-SKILL below; this prints `same`:
  ```sh
  python3 - <<'EOF'
  p = open('plans/portable-setup.md').read().split('\n')
  s = p.index('~~~~markdown setup-dotfiles') + 1
  e = p.index('~~~~', s)
  want = '\n'.join(p[s:e]) + '\n'
  got = open('.claude/skills/setup-dotfiles/SKILL.md').read()
  print('same' if want == got else 'DIFF')
  EOF
  ```
  Plus `uv run --no-project --with pyyaml python -c "import yaml,sys; d=yaml.safe_load(open(sys.argv[1]).read().split('---')[1]); assert d['name']=='setup-dotfiles' and d['disable-model-invocation'] is True and d['argument-hint']=='[update]' and ': ' not in d['description']; print('ok')" .claude/skills/setup-dotfiles/SKILL.md` prints `ok`.
- AC11: `sed -n '1,15p' README.md | grep -cF '/setup-dotfiles'` prints at least `1`.
- AC12: the README backup snippet moves the Claude files and keeps links. This prints two `moved` lines (the Claude files), then `ls` lists exactly `SKILL.md` and `implementer.md` (any order or layout), then `link-kept`:
  ```sh
  T="$(mktemp -d)"
  mkdir -p "$T/.claude/agents" "$T/.claude/skills/feature"
  echo x > "$T/.claude/agents/implementer.md"; echo y > "$T/.claude/skills/feature/SKILL.md"; ln -s /nonexistent "$T/.tmux.conf"
  python3 - "$T" <<'EOF'
  import sys
  t = open('README.md').read()
  s = t.index('## Before you start: existing configs')
  b = t.index('```sh\n', s) + len('```sh\n')
  e = t.index('```', b)
  open(sys.argv[1] + '/snippet.sh', 'w').write(t[b:e])
  EOF
  HOME="$T" sh "$T/snippet.sh"; ls "$T"/dotfiles-backup/*/; test -L "$T/.tmux.conf" && echo link-kept
  ```

## Shared definitions

- Repo: `$HOME/dotfiles` (= `~/dotfiles`, `$DOTFILES` in `install.sh`).
  Branch `feat/portable-setup`, base `main` at `6c9b561`.
- New repo paths: `tmux/tmux.conf`, `starship/starship.toml`,
  `claude/skills/feature/SKILL.md`, `claude/agents/<name>.md`,
  `.claude/skills/setup-dotfiles/SKILL.md`.
- Link targets (unchanged): `~/.tmux.conf`, `~/.config/starship.toml`.
- New link targets: `~/.claude/skills/feature/SKILL.md` and
  `~/.claude/agents/<name>.md`, one file link each, both OSes.
- L-AGENTS (the agent names, this order everywhere):
  `implementer plan-reviewer acceptance-validator skill-dry-run`.
- Backup of the live Claude files: `~/.claude/backups/feature-vendor.2026-10-24/`
  holding `skills/feature/SKILL.md` and `agents/<name>.md` for L-AGENTS.
- No em dash (U+2014) in any line a task writes. The vendored copies keep
  theirs (they are copied, not written).
- Commits are made by the orchestrator after each task's gates, not by
  implementers.

## Tasks

Strictly sequential (T1, T2, T3, T4 share `CLAUDE.md` and `README.md`); each
is committed before the next starts.

### T1: move tmux.conf and starship.toml

Files: `.tmux.conf` -> `tmux/tmux.conf`, `starship.toml` ->
`starship/starship.toml`, `install.sh`, `README.md`, `CLAUDE.md`,
`.claude/rules/tmux.md`, `.claude/skills/docs-sync/SKILL.md`; live links
`~/.tmux.conf`, `~/.config/starship.toml`.

1. `git mv .tmux.conf tmux/tmux.conf` and `mkdir -p starship && git mv starship.toml starship/starship.toml`. No content change in either file.
2. `install.sh` lines 359-360, replace
   ```
   ln -sf "$DOTFILES/starship.toml" ~/.config/starship.toml
   ln -sf "$DOTFILES/.tmux.conf" ~/.tmux.conf
   ```
   with
   ```
   ln -sf "$DOTFILES/starship/starship.toml" ~/.config/starship.toml
   ln -sf "$DOTFILES/tmux/tmux.conf" ~/.tmux.conf
   ```
3. `README.md` line 260: `` | `starship.toml` | `` -> `` | `starship/starship.toml` | `` (rest of the row unchanged).
   Line 261: `` | `.tmux.conf` | `` -> `` | `tmux/tmux.conf` | `` (rest unchanged).
   Line 291: `` newly listed in `.tmux.conf` and `` -> `` newly listed in `tmux/tmux.conf` and ``.
4. `CLAUDE.md`
   - line 32 (starts `` - `zsh/`, `.tmux.conf`, `starship.toml` ``, ends `shell, multiplexer, prompt.`, an em dash between them) is replaced as a whole line by
     `` - `zsh/`, `tmux/tmux.conf`, `starship/starship.toml`: shell, multiplexer, prompt. ``
     (Edit: copy the whole old line, em dash included, from the Read output into `old_string`; the no-em-dash hook ignores `old_string`.)
   - line 48: `` - `.tmux.conf`, `starship.toml`: directly linked configs. `prefix + s` runs `` ->
     `` - `tmux/tmux.conf`, `starship/starship.toml`: directly linked configs. `prefix + s` runs ``
   - line 137: `` applies and validates `.tmux.conf`; errors `` -> `` applies and validates `tmux/tmux.conf`; errors ``
5. `.claude/rules/tmux.md`: delete line 3 (`  - ".tmux.conf"`); `"tmux/**"` stays and covers the new file.
6. `.claude/skills/docs-sync/SKILL.md` line 20: `` | `.tmux.conf` ( `` -> `` | `tmux/tmux.conf` ( ``; line 36: `` @plugin' .tmux.conf `` -> `` @plugin' tmux/tmux.conf ``.
7. Re-link the live configs (same targets, new sources):
   ```sh
   ln -sf "$HOME/dotfiles/tmux/tmux.conf" ~/.tmux.conf
   ln -sf "$HOME/dotfiles/starship/starship.toml" ~/.config/starship.toml
   ```
   Do not reload tmux: the content is unchanged. Starship reads its config
   on every prompt, so these links must follow the moved files on the
   branch. Rollback if the cycle stops before the merge (orchestrator, after
   `git switch main`):
   `ln -sf "$HOME/dotfiles/.tmux.conf" ~/.tmux.conf; ln -sf "$HOME/dotfiles/starship.toml" ~/.config/starship.toml`.

Must not change: file contents of the two moved files; `~/.tmux.conf`
mentions everywhere (targets); `plans/`; `AGENTS.md` (T3 replaces it);
`.claude/settings.local.json`.

Task gates: `bash -n install.sh`; `git diff --cached -M --name-status` shows
`R100` for both moves; AC2; AC3.

Done: the seven steps applied, task gates green.

### T2: vendor /feature and its agents, link them from install.sh

Files: new `claude/skills/feature/SKILL.md`, new `claude/agents/<name>.md`
(L-AGENTS), `install.sh`, `README.md`, `CLAUDE.md`; backup dir. The live
files under `~/.claude/` are NOT touched in this task (see Post-merge).

Line numbers below are positions in the file before this task; match every
edit by its old text (Edit `old_string`), never by line number alone.

1. Backup (stop with BLOCKED if the backup dir already exists):
   ```sh
   B=~/.claude/backups/feature-vendor.2026-10-24
   test ! -e "$B" || { echo "BLOCKED: $B exists"; exit 1; }
   mkdir -p "$B/skills/feature" "$B/agents"
   cp -p ~/.claude/skills/feature/SKILL.md "$B/skills/feature/"
   for a in implementer plan-reviewer acceptance-validator skill-dry-run; do cp -p ~/.claude/agents/$a.md "$B/agents/"; done
   ```
2. Copy into the repo with `cp` from the backup (never Write: the files carry
   em dashes the hook rejects): `mkdir -p claude/skills/feature claude/agents`,
   `cp "$B/skills/feature/SKILL.md" claude/skills/feature/`,
   `cp "$B"/agents/*.md claude/agents/`. Then `chmod 644` the five repo files.
3. `install.sh`: insert this block after the line
   `echo 'export ZDOTDIR="$HOME/.config/zsh"' > ~/.zshenv` and its following
   blank line, before the `# ===...` banner line that opens
   `# Claude Code notifications (macOS)`; keep one blank line on each side:
   ```bash
   # =============================================================================
   # Claude Code: the /feature skill and the agents it runs
   # =============================================================================
   # File links: ~/.claude/skills and ~/.claude/agents also hold skills and
   # agents from outside this repo. A regular file in the way is replaced.
   echo "Linking Claude Code skills and agents..."
   mkdir -p ~/.claude/skills/feature ~/.claude/agents
   ln -sf "$DOTFILES/claude/skills/feature/SKILL.md" ~/.claude/skills/feature/SKILL.md
   ln -sf "$DOTFILES"/claude/agents/*.md ~/.claude/agents/
   ```
4. (no step: the live links are made after the merge, see Post-merge)
5. `README.md`
   - after line 36 (`` - `~/.tmux.conf` and `~/.config/starship.toml` are replaced by links. ``) insert:
     ```
     - `~/.claude/skills/feature/SKILL.md` and `implementer.md`,
       `plan-reviewer.md`, `acceptance-validator.md`, `skill-dry-run.md` in
       `~/.claude/agents/` are replaced by links (Claude Code's `/feature`
       skill and the agents it runs).
     ```
   - the loop head, lines 51-53:
     ```
     for p in ~/.zshenv ~/.tmux.conf ~/.config/starship.toml \
       ~/.config/nvim ~/.config/zsh ~/.config/yazi \
       ~/.config/ghostty ~/.config/aerospace ~/.config/karabiner ~/.config/topgrade; do
     ```
     becomes:
     ```
     for p in ~/.zshenv ~/.tmux.conf ~/.config/starship.toml \
       ~/.config/nvim ~/.config/zsh ~/.config/yazi \
       ~/.config/ghostty ~/.config/aerospace ~/.config/karabiner ~/.config/topgrade \
       ~/.claude/skills/feature/SKILL.md ~/.claude/agents/implementer.md \
       ~/.claude/agents/plan-reviewer.md ~/.claude/agents/acceptance-validator.md \
       ~/.claude/agents/skill-dry-run.md; do
     ```
   - lines 85-88 (macOS install paragraph):
     ```
     The script installs Homebrew if missing, the formulae and casks listed below,
     links the configs, clones TPM, writes `ZDOTDIR` into `~/.zshenv`, switches the
     default shell to zsh, wires the Claude Code Stop hook, and sets up commit
     signing for this repo when `~/.ssh/id_ed25519.pub` exists.
     ```
     become:
     ```
     The script installs Homebrew if missing, the formulae and casks listed below,
     links the configs, clones TPM, writes `ZDOTDIR` into `~/.zshenv`, switches the
     default shell to zsh, links the Claude Code `/feature` skill and its agents,
     wires the Claude Code Stop hook, and sets up commit signing for this repo when
     `~/.ssh/id_ed25519.pub` exists.
     ```
   - lines 106-110 (Linux install paragraph):
     ```
     The script installs the apt or dnf packages listed below plus Neovim,
     the tree-sitter CLI and Starship, links the configs, clones TPM, writes
     `ZDOTDIR` into `~/.zshenv`, switches the default shell to zsh (`sudo usermod`,
     no password prompt from `chsh`), and sets up commit signing when
     `~/.ssh/id_ed25519.pub` exists. macOS-only configs are skipped.
     ```
     become:
     ```
     The script installs the apt or dnf packages listed below plus Neovim,
     the tree-sitter CLI and Starship, links the configs, clones TPM, writes
     `ZDOTDIR` into `~/.zshenv`, switches the default shell to zsh (`sudo usermod`,
     no password prompt from `chsh`), links the Claude Code `/feature` skill and
     its agents, and sets up commit signing when `~/.ssh/id_ed25519.pub` exists.
     macOS-only configs are skipped.
     ```
   - Layout table: after the `claude/hooks/pane-state.sh` row insert:
     ```
     | `claude/skills/feature/SKILL.md` | `~/.claude/skills/feature/SKILL.md` | Claude Code `/feature` skill: plan, implement, review on a branch |
     | `claude/agents/*.md` | `~/.claude/agents/` | one link per file: the agents `/feature` runs (implementer, plan-reviewer, acceptance-validator, skill-dry-run) |
     ```
6. `CLAUDE.md`
   - after line 59 (`` `install.sh`, which also wires settings.json; see `plans/claude-*.md`. ``) insert:
     ```
     - `claude/skills/feature/`, `claude/agents/`: `/feature` and its four agents,
       file-linked into `~/.claude/` by `install.sh`; edit them here, not via the links.
     ```
   - line 98: `` `~/.claude/skills/feature/SKILL.md`), with no OK wait. Overrides here: `` ->
     `` `claude/skills/feature/SKILL.md`), with no OK wait. Overrides here: ``
   - lines 107-109:
     ```
     - `~/.claude/` targets (skills, agents) are outside git: back them up to
       `~/.claude/backups/<name>.<ts>` before dispatch, gate on `diff` against the
       backup; only the plan is committed.
     ```
     become:
     ```
     - `~/.claude/` targets outside `claude/` (other skills, agents) are outside
       git: back them up to `~/.claude/backups/<name>.<ts>` before dispatch, gate on
       `diff` against the backup; only the plan is committed.
     ```

Must not change: the content of the five vendored files; the macOS
notifications block of `install.sh`; any other file in `~/.claude/agents` or
`~/.claude/skills`.

Task gates: `bash -n install.sh`; AC4 (the two Claude lines and the awk
check); AC5; AC12; `find ~/.claude/agents -maxdepth 1 -type l | wc -l` still
prints `0` (live files untouched).

Done: steps applied, task gates green.

### T3: AGENTS.md as a link, drop plan.md

Files: `AGENTS.md`, `plan.md`, `CLAUDE.md`.

1. `git rm -q plan.md`.
2. `rm AGENTS.md && ln -s CLAUDE.md AGENTS.md && git add AGENTS.md` (relative target `CLAUDE.md`).
3. `CLAUDE.md`
   - lines 8-9 become:
     ```
     - IMPLEMENTER: Claude Haiku 5.5 (`claude-haiku-5-5`), medium effort; may also be Codex,
       which reads this file through the `AGENTS.md` symlink.
     ```
   - the `everything.md` entry (3 lines, starts `` - `everything.md`: Russian cheatsheet ``) becomes:
     ```
     - `everything.md`: Russian cheatsheet of the whole stack and keymaps, derived
       from the configs, so it lags them.
     ```
   - `` - `AGENTS.md`: legacy Codex contract; Claude sessions and agents skip it. `` ->
     `` - `AGENTS.md`: symlink to this file for Codex; edit `CLAUDE.md`. ``
   - last two lines of the file become:
     ```
     change. Keep rules actionable, remove outdated ones, avoid duplication with
     `README.md`. Keep the file under 200 lines; `AGENTS.md` follows it as a link.
     ```

Task gates: AC8; `awk 'END { exit !(NR <= 198) }' CLAUDE.md` exits 0.

Done: steps applied, task gates green.

### T4: the setup-dotfiles skill and the README mention

Files: new `.claude/skills/setup-dotfiles/SKILL.md`, `README.md`, `CLAUDE.md`.
(The `skill-note-sync.sh` hook wants every skill in the vault's skills
index; the orchestrator already added the `/setup-dotfiles` line there.)

1. Write `.claude/skills/setup-dotfiles/SKILL.md` with exactly the text of
   S-SKILL (between the `~~~~markdown setup-dotfiles` line and the closing
   `~~~~`, excluding both), ending with one newline.
2. `README.md`: after line 7 (`are live.`) insert a blank line and:
   ```
   With Claude Code installed, `/setup-dotfiles` in a Claude Code session opened
   in `~/dotfiles` walks through the setup below: it checks the requirements,
   moves existing configs aside, runs `install.sh` and lists the first-run
   steps that are left. `/setup-dotfiles update` does the same with
   `install.sh --update`.
   ```
3. `README.md` Layout table: after the `claude/agents/*.md` row (added by T2) insert:
   ```
   | `.claude/skills/` | | Claude Code skills of this repo: `/setup-dotfiles`, `docs-sync` |
   ```
4. `CLAUDE.md`: after the `` - `README.md` `` line of the repository map insert:
   ```
   - `.claude/skills/`: project skills `setup-dotfiles` (`/setup-dotfiles`) and `docs-sync`.
   ```

Task gates: AC10; AC11; AC9's `wc -l`.

Done: steps applied, task gates green.

S-SKILL:

~~~~markdown setup-dotfiles
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
  Check only the Claude Code files `install.sh` links over:
  `~/.claude/skills/feature/SKILL.md` and
  `~/.claude/agents/{implementer,plan-reviewer,acceptance-validator,skill-dry-run}.md`.
  Each one that is a regular file (not a link) and differs from its copy
  under `~/dotfiles/claude/` (`cmp -s`; a missing copy counts as different)
  goes on the move list.

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
  ~/.claude/skills/feature/SKILL.md ~/.claude/agents/implementer.md
cat ~/.zshenv; ls -d ~/.tmux/plugins/tpm
dscl . -read "/Users/$USER" UserShell 2>/dev/null || getent passwd "$USER" | cut -d: -f7
git -C ~/dotfiles status --short
```

Expected: every link resolves into `~/dotfiles` (`~/.tmux.conf` to
`tmux/tmux.conf`, `~/.config/starship.toml` to `starship/starship.toml`),
`~/.zshenv` exports `ZDOTDIR`, TPM exists, the login shell is zsh, the
checkout is clean. On macOS also
`jq -r '.hooks.Stop[].hooks[].command' ~/.claude/settings.json` lists
`~/.claude/hooks/notify.sh`.

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
~~~~

## Post-merge (orchestrator, after `git merge --ff-only` into `main`)

The live `~/.claude` files become links only once `main` holds the repo
copies, so a stopped cycle or a `git switch main` by another session never
leaves `/feature` and its agents dangling.

1. `cmp` each live file against its repo copy (`~/.claude/skills/feature/SKILL.md`
   vs `claude/skills/feature/SKILL.md`, each L-AGENTS file); a difference
   means another session edited it during the cycle: stop and report.
2. Link:
   ```sh
   mkdir -p ~/.claude/skills/feature ~/.claude/agents
   ln -sf "$HOME/dotfiles/claude/skills/feature/SKILL.md" ~/.claude/skills/feature/SKILL.md
   ln -sf "$HOME"/dotfiles/claude/agents/*.md ~/.claude/agents/
   ```
3. Run AC6 and AC7.

## Seams

| Producer | Consumer | Shared definition |
|---|---|---|
| T1 (new paths `tmux/tmux.conf`, `starship/starship.toml`) | T4 (S-SKILL steps 1 and 6) | Shared definitions: new repo paths, link targets |
| T2 (README backup loop with the Claude files) | T4 (S-SKILL steps 2 and 4 run that loop) | L-AGENTS, new link targets |
| T2 (`install.sh` Claude link block) | T4 (S-SKILL step 2 set-up check, step 6) | new link targets, L-AGENTS |
| T2 (Layout rows) | T4 (Layout row after `claude/agents/*.md`) | T2 step 5 row text |
| T1, T2, T3, T4 (`CLAUDE.md` line budget) | Gates (`wc -l` at most 199) | T1 +0, T2 +2, T3 -1, T4 +1: 195 -> 197 |

## Edge cases

- macOS vs Linux: the Claude link block runs on both (Claude Code also runs on
  servers); the hooks and notification block stays macOS-only. `mkdir -p`
  creates `~/.claude` on a machine without Claude Code, harmless.
- Missing tools: the new block needs only `mkdir` and `ln`.
- Set-up machines that pull this change: `install.sh --update` pulls first,
  then the new script re-links `~/.tmux.conf` and `~/.config/starship.toml`.
  Between pull and re-link the two links dangle (a running tmux keeps its
  loaded config). A plain `git pull` without `install.sh` leaves them
  dangling until the next run.
- A machine with its own regular `~/.claude/agents/implementer.md` (or the
  other four): `ln -sf` replaces it silently; README lists them in the
  backup loop and the skill checks them on set-up machines.
- Dirty worktree: `main` was clean at `6c9b561`; the other Claude pane in
  this repo was idle (`done`) at branch time.
- First run: covered by S-SKILL; nothing in this plan runs `install.sh`.

## Not doing

- No change of link targets, no XDG `~/.config/tmux`, no Stow for `tmux/`,
  `starship/` or `claude/`.
- No edits under `plans/` (old references to `.tmux.conf` stay as history),
  in `everything.md`, or in the gitignored `.claude/settings.local.json`.
- No content edits to the vendored `/feature` and agent files.
- No vendoring of other `~/.claude` skills (anki-addon, cc-settings,
  session-handoff, ...), hooks (bash-guard.py, skill-note-sync.sh) or the
  global `~/.claude/CLAUDE.md`.
- Not running `install.sh`.
