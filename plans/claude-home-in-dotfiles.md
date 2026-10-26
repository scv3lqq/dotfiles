# Move the global ~/.claude config into dotfiles

## Goal

Every hand-written piece of the global Claude Code config (`~/.claude/CLAUDE.md`,
`settings.json`, hooks, `bin/`, own skills) lives in this public repo under
`claude/` and is linked back into `~/.claude`, the way `/feature`, its agents,
the status line and the theme already are. Nothing personal lands in the repo or
its history: personal facts move to a private overlay `~/.claude/private/` that is
never linked or committed, and a pre-commit hook refuses staged lines that match
a private denylist.

## Current behavior

`~/.claude` holds the config as regular files; only `skills/feature/SKILL.md`
(a file link inside a real directory), four agents, `hooks/notify.sh`,
`hooks/pane-state.sh`, `statusline.sh` and `themes/ayu.json` link into
`~/dotfiles/claude/`. `install.sh` merges `statusLine`, `theme`, the Stop hook
and the pane-state hooks into `~/.claude/settings.json` with `jq > tmp && mv`.

## Decisions

- One-hop links. Claude Code's atomic `settings.json` write follows one link hop
  (the multi-hop failure is anthropics/claude-code#78162), so
  `~/.claude/settings.json -> ~/dotfiles/claude/settings.json` keeps working.
  `jq > tmp && mv tmp settings.json` replaces a link with a regular file, so
  `install.sh` stops merging into it on macOS and `bin/settings-edit.sh` writes
  through the link. The tmux-assistant-resurrect plugin resolves links only on
  its removal path; its install path (`install_claude_hooks`) still writes with
  `mv`, but only when its two hooks are missing, and the repo `settings.json`
  already holds them. T14's `readlink` check detects a replaced link.
- Skills become directory links (Claude Code 2.0.62 fixed files inside symlinked
  skill directories), so a file a session adds to a skill lands in the repo.
  Agents, hooks and `bin/` stay file links.
- `claude/CLAUDE.md` pulls the personal part in with the import line
  `@~/.claude/private/CLAUDE.md` (code.claude.com/docs/en/memory, "Import
  additional files"); `install.sh` creates an empty file there when missing.
- `CLAUDE.md` and `settings.json` are linked on macOS only: their workflow rules
  and hooks are macOS-specific. Linux keeps a local `settings.json` with the
  two key merges it has today.
- No personal value is ever committed, not even in an intermediate commit: the
  history is public. T0 (the guard) lands first; every task sanitizes its files
  before the orchestrator commits them.
- Live `~/.claude` changes only after the merge (section "Post-merge"), from a
  frozen snapshot, so a failed branch leaves `~/.claude` untouched.
- Not moved (see "Not doing"): third-party skills, the work-only
  `confluence-doc`, the agent `go-code-reviewer.md` of unknown origin, runtime
  state.

## Acceptance criteria

Run from any directory; paths are absolute.

- AC1 guard: the F0 fixture (T0) prints `case1 exit=0`, `case2 exit=1`, `1`,
  `case3 exit=0`, `1`.
- AC2 privacy: the G-PRIV block prints `0`, then `grep exit=1` with no lines
  before it, then `0` (commit messages), then `gitleaks exit=0`.
- AC3 parity: the G-PAR block prints exactly the lines of SD-EXPECTED-DIFF (any
  order) and nothing else.
- AC4 syntax: the G-SYN block prints only `install-ok`.
- AC5 install: the F11 fixture (T11) prints only `DONE`.
- AC6 hooks: the F3 fixtures (T3) print `new exit=2`, `1`, `known exit=0`,
  `novault exit=0`, then `edit exit=0`, `link-kept`, `1`, `1`, `bad exit=1`, `1`.
- AC7 docs: each `grep -c -F` in G-DOCS prints the number it names, and
  `wc -l < ~/dotfiles/CLAUDE.md | tr -d ' '` prints `199`.
- AC8 no new em dash: G-DASH prints `0`.
- AC9 (post-merge, orchestrator): the AC-POST block prints no `FAIL`, then `22`,
  an empty `git status`, `.githooks`, `identity-ok` (the personal line itself
  is never printed).

## Gates

G-SYN:

```bash
bash -n ~/dotfiles/install.sh && echo install-ok
find ~/dotfiles/claude ~/dotfiles/.githooks -type f \( -name '*.sh' -o -name pre-commit \) -exec sh -c '/bin/bash -n "$1" || echo "FAIL $1"' _ {} \;
find ~/dotfiles/claude -name '*.zsh' -exec sh -c 'zsh -n "$1" /dev/null || echo "FAIL $1"' _ {} \;
find ~/dotfiles/claude -name '*.py' -not -path '*/__pycache__/*' -exec sh -c 'python3 -c "import ast, sys; ast.parse(open(sys.argv[1]).read())" "$1" || echo "FAIL $1"' _ {} \;
find ~/dotfiles/claude -name '*.json' -exec sh -c 'jq empty "$1" || echo "FAIL $1"' _ {} \;
find ~/dotfiles/claude -name '*.mjs' -exec sh -c 'node --check "$1" || echo "FAIL $1"' _ {} \;
```

G-PRIV (the denylist is personal: never print it, never copy it into the repo):

```bash
deny=$(mktemp); grep -v -E '^[[:space:]]*(#|$)' ~/.claude/private/denylist > "$deny"
git -C ~/dotfiles log -p --no-color main..HEAD | grep '^+' | grep -c -i -E -f "$deny"
git -C ~/dotfiles grep -n -I -i -E -f "$deny" -- claude .githooks install.sh README.md CLAUDE.md .claude/skills plans/claude-home-in-dotfiles.md; echo "grep exit=$?"
git -C ~/dotfiles log --format=%B main..HEAD | grep -c -i -E -f "$deny"
gitleaks git --no-banner --redact --log-opts='main..HEAD' ~/dotfiles; echo "gitleaks exit=$?"
```

A task's scoped privacy check (before the orchestrator commits it):
`grep -r -n -I -i -E -f <(grep -v -E '^[[:space:]]*(#|$)' ~/.claude/private/denylist) <task files>`
prints nothing.

G-PAR:

```bash
S=~/.claude/backups/claude-home-move/snapshot; R=~/dotfiles/claude
{ diff -rq -x __pycache__ -x '*.pyc' -x .DS_Store "$S/skills" "$R/skills" | grep -v -F "Only in $R/skills: feature" | sed -E 's#^Files .*/snapshot/skills/([^ ]+) and .* differ$#differs: skills/\1#'
  for f in CLAUDE.md settings.json hooks/bash-guard.py hooks/git-commit-guard.py hooks/no-em-dash.sh hooks/skill-note-sync.sh bin/settings-edit.sh; do cmp -s "$S/$f" "$R/$f" || echo "differs: $f"; done
} | sort
```

G-DOCS:

```bash
grep -c -F 'one directory link per skill' ~/dotfiles/README.md            # 2
grep -c -F 'a regular file there is first moved to' ~/dotfiles/README.md  # 1
grep -c -F '.githooks/pre-commit' ~/dotfiles/README.md                    # 1
grep -c -F 'skills/feature/SKILL.md' ~/dotfiles/README.md                 # 0
grep -c -F '.githooks/pre-commit' ~/dotfiles/CLAUDE.md                    # 1
grep -c -F 'chore(claude): sync settings' ~/dotfiles/CLAUDE.md            # 1
grep -c -F 'skills/feature/SKILL.md' ~/dotfiles/.claude/skills/setup-dotfiles/SKILL.md  # 0
grep -c -F 'is skipped by' ~/dotfiles/.claude/skills/setup-dotfiles/SKILL.md            # 1
wc -l < ~/dotfiles/CLAUDE.md | tr -d ' '                                  # 199
```

G-DASH (moved files keep their old text; every line this branch writes is
dash-free):

```bash
git -C ~/dotfiles diff main...HEAD -U0 -- install.sh README.md CLAUDE.md .githooks .claude claude/CLAUDE.md claude/hooks/skill-note-sync.sh claude/bin claude/skills/feature plans | grep '^+' | grep -c $'\xe2\x80\x94'
```

Plus per edited skill file: `diff <snapshot file> <repo file> | grep '^>' | grep -c $'\xe2\x80\x94'`
prints `0`.

## Shared definitions

### SD-PATHS

- Repo: `~/dotfiles` (`$DOTFILES` in `install.sh`). Live config: `~/.claude`.
- Snapshot: `~/.claude/backups/claude-home-move/snapshot/`, a frozen copy of
  every live item this plan moves, laid out like `~/.claude` (`CLAUDE.md`,
  `settings.json`, `hooks/`, `bin/`, `skills/<name>/`). It already exists. Tasks
  copy FROM the snapshot, never from live `~/.claude`, and never write into it.
- Overlay: `~/.claude/private/` (mode 700). It already exists; tasks only point
  at it. Never linked, never inside the repo. Files:
  - `CLAUDE.md`: the personal part of the global instructions.
  - `denylist`: one case-insensitive extended regex per line; `#` comments and
    blank lines are ignored.
  - `vault`: one line, the absolute path of the Obsidian vault root.
  - `mac-audit-baseline.md`: the known-benign baseline of this Mac.
  - `obsidian-sr-flashcards.md`: the vault-specific override of that skill.

### SD-NOQUOTE

Personal values (account name, real name, employers, work projects, vault name,
hosts, IPs, installed corporate software) never appear in this plan, in code,
in comments, in commit messages or in reports. This plan points at them by file,
line and kind; read the snapshot file to find the exact text, then replace it.

### SD-LISTS

- L-SKILLS, moved (17): `anki anki-addon anki-grammar cc-settings
  git-history-rewrite mac-audit mac-space obsidian-sr-flashcards page-shot
  public-repo refactor-proof repo-knowledge-base retro session-handoff
  system-design-diagram tech-note-review tmux-cleanup`.
  - L-CLEAN, copied unchanged by T1: `anki-addon git-history-rewrite mac-space
    page-shot refactor-proof retro session-handoff system-design-diagram
    tmux-cleanup`.
  - The other eight are copied and edited by T4..T9.
- `mac-*` skills are macOS-only: `install.sh` links them on Darwin only.
- L-HOOKS: `bash-guard.py git-commit-guard.py no-em-dash.sh` (T1, unchanged),
  `skill-note-sync.sh` (T3).
- L-STAYS, left as regular entries in `~/.claude` and never copied: skills
  `excalidraw-diagram excalidraw-skill system-design confluence-doc synced
  .trash`, `agents/go-code-reviewer.md`, `settings.local.json`, every runtime
  directory (`projects`, `sessions`, `plugins`, `cache`, ...).

### SD-COPY

A skill directory is copied with:

```bash
rsync -a --exclude __pycache__ --exclude '*.pyc' --exclude .venv --exclude node_modules --exclude .DS_Store \
  ~/.claude/backups/claude-home-move/snapshot/skills/<name>/ ~/dotfiles/claude/skills/<name>/
```

A single file with `cp -p <snapshot path> <repo path>`. Both keep the mode bits.
Edits to an existing line use the Edit tool: the Bash hook blocks `sed -i`.

### SD-EXPECTED-DIFF

After all tasks, G-PAR prints exactly these lines:

```text
differs: CLAUDE.md
differs: bin/settings-edit.sh
differs: hooks/skill-note-sync.sh
differs: skills/anki-grammar/SKILL.md
differs: skills/anki/SKILL.md
differs: skills/cc-settings/SKILL.md
differs: skills/mac-audit/SKILL.md
differs: skills/mac-audit/references/agents.md
differs: skills/obsidian-sr-flashcards/SKILL.md
differs: skills/public-repo/SKILL.md
differs: skills/repo-knowledge-base/SKILL.md
differs: skills/tech-note-review/SKILL.md
```

### SD-LINKS (target layout; T11 implements it, T12..T14 describe it)

- Both OSes: `~/.claude/skills/<name>` is a directory link to
  `~/dotfiles/claude/skills/<name>` for every directory there (`mac-*` on
  Darwin only); one file link per `claude/agents/*.md`, `claude/hooks/*.sh`,
  `claude/hooks/*.py`, `claude/bin/*`; `statusline.sh`; `themes/ayu.json`.
- macOS only: `~/.claude/CLAUDE.md` and `~/.claude/settings.json` link to
  `~/dotfiles/claude/`; a regular file in the way first moves to
  `~/.claude/backups/<name>.<YYYYmmdd-HHMMSS>`; `~/.claude/private/` is created
  with mode 700 and an empty `CLAUDE.md` when missing.
- Linux: `settings.json` stays a local file; `install.sh` sets its `statusLine`
  and `theme` keys as today.
- Repo-local git config: `core.hooksPath=.githooks`.
- A real skill directory in the way: one that holds only links (the old
  `feature` layout) is replaced; one that holds any other entry is skipped with
  `Skipping <path>: a real directory with files, move it aside first`.

### SD-GUARD (exact content of `.githooks/pre-commit`, mode 755)

```bash
#!/bin/bash
# Refuse a commit whose added lines match a personal pattern. The patterns are
# personal data themselves, so they live outside the repo: one case-insensitive
# extended regex per line in ~/.claude/private/denylist, `#` starts a comment.
set -u
deny="$HOME/.claude/private/denylist"
if [ ! -f "$deny" ]; then
    echo "pre-commit: no $deny, personal-data check skipped" >&2
    exit 0
fi
patterns=$(mktemp)
trap 'rm -f "$patterns"' EXIT
grep -v -E '^[[:space:]]*(#|$)' "$deny" > "$patterns"
[ -s "$patterns" ] || exit 0
hits=$(git diff --cached -U0 --no-color --no-ext-diff --diff-filter=ACMR \
    | awk '/^\+\+\+ / { file = substr($0, 7); next } /^\+/ { print file ": " substr($0, 2) }' \
    | grep -i -E -f "$patterns")
[ -n "$hits" ] || exit 0
printf 'pre-commit: staged lines match %s:\n%s\n' "$deny" "$hits" >&2
echo 'Move the personal part to ~/.claude/private/ or rewrite it generically.' >&2
exit 1
```

## Tasks

Waves: T0 alone (committed before anything else); then T1..T10 in parallel;
then T11..T14 in parallel. Implementers do not commit: the orchestrator commits
each task by explicit pathspec after its gates, so the guard checks every
commit. Every task also runs its scoped privacy check (Gates).

Commit subjects (the guard does not see messages; G-PRIV checks them):
T0 `feat(git): refuse personal data in staged lines`,
T1 `feat(claude): move clean ~/.claude config into the repo`,
T2 `feat(claude): track global instructions, import the private part`,
T3 `feat(claude): track note-sync hook and settings-edit, write through links`,
T4 `feat(claude): track anki skills with home-relative paths`,
T5 `feat(claude): track cc-settings, note the settings link`,
T6 `feat(claude): track mac-audit, baseline moves to the overlay`,
T7 `feat(claude): track flashcards skill, vault override in the overlay`,
T8 `feat(claude): track public-repo and repo-knowledge-base skills`,
T9 `feat(claude): track tech-note-review, vault path from the overlay`,
T10 `docs(claude): generalize a /feature lesson`,
T11 `feat(install): link the whole claude/ tree into ~/.claude`,
T12 `docs(readme): describe the claude/ links`,
T13 `docs(claude): map claude/ and the private overlay`,
T14 `docs(setup): check the new claude/ links`.

### T0: personal-data pre-commit hook

- Files: `.githooks/pre-commit` (new).
- Write SD-GUARD verbatim, `chmod 755`. Then run
  `git -C ~/dotfiles config core.hooksPath .githooks` (repo-local config).
- Task gates: `/bin/bash -n ~/dotfiles/.githooks/pre-commit`; fixture F0 prints
  `case1 exit=0`, `case2 exit=1`, `1`, `case3 exit=0`, `1`;
  `git -C ~/dotfiles config core.hooksPath` prints `.githooks`.

F0:

```bash
T=$(mktemp -d)
git -C "$T" init -q
git -C "$T" config user.name t; git -C "$T" config user.email t@example.com
git -C "$T" config commit.gpgsign false; git -C "$T" config core.hooksPath "$HOME/dotfiles/.githooks"
mkdir -p "$T/h/.claude/private"
printf '# comment\n\nfixture-token-q7\n' > "$T/h/.claude/private/denylist"
echo hello > "$T/a.txt"; git -C "$T" add a.txt
HOME="$T/h" git -C "$T" commit -qm one; echo "case1 exit=$?"
echo 'line with Fixture-Token-Q7 inside' >> "$T/a.txt"; git -C "$T" add a.txt
HOME="$T/h" git -C "$T" commit -qm two 2> "$T/err2"; echo "case2 exit=$?"
grep -c -F 'a.txt: line with Fixture-Token-Q7 inside' "$T/err2"
mv "$T/h/.claude/private/denylist" "$T/h/denylist.off"
HOME="$T/h" git -C "$T" commit -qm three 2> "$T/err3"; echo "case3 exit=$?"
grep -c -F 'personal-data check skipped' "$T/err3"
```

Case 1 also proves that a blank or comment line in the denylist does not match
every line.

### T1: copy the clean items

- Files (new): `claude/settings.json`, `claude/hooks/bash-guard.py`,
  `claude/hooks/git-commit-guard.py`, `claude/hooks/no-em-dash.sh`, and
  `claude/skills/<name>/` for every name in L-CLEAN.
- `cp -p` the four files from the snapshot; SD-COPY each L-CLEAN skill. No edits.
- Task gates: `cmp` of each file against its snapshot copy is silent;
  `diff -rq -x __pycache__ -x '*.pyc' -x .DS_Store <snapshot skill> <repo skill>`
  is silent for each L-CLEAN skill; `jq empty ~/dotfiles/claude/settings.json`;
  scoped privacy check over all T1 files prints nothing.

### T2: global instructions

- File (new): `claude/CLAUDE.md`, from `cp -p` of the snapshot `CLAUDE.md`.
- Edit 1: lines 4..8 are the body of `## Identity` (five lines between the
  `## Identity` heading and the blank line before `## Response style`). Replace
  those five lines with the single line `@~/.claude/private/CLAUDE.md`. Keep the
  heading and the blank line.
- Edit 2: insert this bullet as a new line directly before the line that starts
  with `- Plan before coding for non-trivial tasks`:

```text
- `~/.claude/` `CLAUDE.md`, `settings.json`, hooks, `bin/`, agents and my own skills are links into the public repo `~/dotfiles/claude/` (one directory link per skill): an edit there is a dotfiles change, committed there by explicit pathspec; a new skill: create `~/dotfiles/claude/skills/<name>/`, then `ln -s` it into `~/.claude/skills/`. Personal facts (names, employers, work projects, hosts, IPs, home paths, this machine's setup) go to `~/.claude/private/`, never linked; the dotfiles pre-commit hook refuses staged lines matching `~/.claude/private/denylist`, so extend that list when a new kind of personal value appears
```

- Nothing else changes.
- Task gates: `sed -n 3,4p ~/dotfiles/claude/CLAUDE.md` prints `## Identity`
  and `@~/.claude/private/CLAUDE.md`;
  `diff <snapshot CLAUDE.md> ~/dotfiles/claude/CLAUDE.md | grep -c '^>'` prints
  `2` and `... | grep -c '^<'` prints `5`; scoped privacy check prints nothing.

### T3: hook and settings script write paths

- Files (new): `claude/hooks/skill-note-sync.sh`, `claude/bin/settings-edit.sh`,
  each from `cp -p` of its snapshot copy.
- `skill-note-sync.sh` line 7 is the `NOTE=` assignment (it holds a vault path).
  Replace that one line with these two lines:

```bash
# The vault root is personal, so its path lives outside the repo
NOTE="$(cat "$HOME/.claude/private/vault" 2>/dev/null)/meta/claude-code/Claude Code Skills.md"
```

  A missing `vault` file yields a path that does not exist, and the existing
  `[ -f "$NOTE" ] || exit 0` turns the hook into a no-op.
- `settings-edit.sh`: replace the line `mv "$tmp" "$file"` with these two lines:

```bash
# Write through: settings.json may be a link into ~/dotfiles, and mv would replace the link
cat "$tmp" > "$file" && rm -f "$tmp"
```

- Task gates: `/bin/bash -n` on both files; F3 prints the AC6 sequence; scoped
  privacy check prints nothing.

F3:

```bash
T=$(mktemp -d)
mkdir -p "$T/h/.claude/private" "$T/v/meta/claude-code"
printf '%s\n' "$T/v" > "$T/h/.claude/private/vault"
printf -- '- `/known`* one line\n' > "$T/v/meta/claude-code/Claude Code Skills.md"
hook="$HOME/dotfiles/claude/hooks/skill-note-sync.sh"
echo '{"tool_name":"Write","tool_input":{"file_path":"/x/skills/newone/SKILL.md"}}' | HOME="$T/h" /bin/bash "$hook" 2> "$T/err1"; echo "new exit=$?"
grep -c -F '/newone' "$T/err1"
echo '{"tool_name":"Write","tool_input":{"file_path":"/x/skills/known/SKILL.md"}}' | HOME="$T/h" /bin/bash "$hook"; echo "known exit=$?"
rm "$T/h/.claude/private/vault"
echo '{"tool_name":"Write","tool_input":{"file_path":"/x/skills/newone/SKILL.md"}}' | HOME="$T/h" /bin/bash "$hook"; echo "novault exit=$?"
edit="$HOME/dotfiles/claude/bin/settings-edit.sh"
mkdir -p "$T/repo"; echo '{"a": 0}' > "$T/repo/s.json"; ln -s "$T/repo/s.json" "$T/h/s.json"
HOME="$T/h" /bin/bash "$edit" "$T/h/s.json" '.a = 1' > "$T/out"; echo "edit exit=$?"
[ -L "$T/h/s.json" ] && echo link-kept
jq -r .a "$T/repo/s.json"
ls "$T/h/.claude/backups" | grep -c '^s.json.bak.'
HOME="$T/h" /bin/bash "$edit" "$T/h/s.json" '.a =' 2> /dev/null; echo "bad exit=$?"
[ -L "$T/h/s.json" ] && jq -r .a "$T/repo/s.json"
```

### T4: anki and anki-grammar home paths

- Files (new): `claude/skills/anki/`, `claude/skills/anki-grammar/` (SD-COPY).
- `anki/SKILL.md` lines 23, 24, 154 and `anki-grammar/SKILL.md` lines 16, 17
  hold absolute home paths of the form `/Users/<account>/.claude/...`. On each
  of those lines replace the `/Users/<account>/` prefix with `~/`, so they read
  `~/.claude/skills/anki/scripts/anki.py`, `~/.claude/skills/anki/config.json`,
  `~/.claude/skills/anki-grammar/SKILL.md`. Nothing else changes.
- Task gates: `grep -r -c '/Users/' ~/dotfiles/claude/skills/anki ~/dotfiles/claude/skills/anki-grammar`
  prints only `:0` counts; `diff <snapshot SKILL.md> <repo SKILL.md> | grep -c '^>'`
  prints `3` for anki and `2` for anki-grammar; scoped privacy check prints nothing.

### T5: cc-settings link note

- Files (new): `claude/skills/cc-settings/` (SD-COPY).
- Insert these three lines directly after the line `the file, so never hand-write one.`
  (end of step 2 of `## Procedure`):

```text
On macOS `~/.claude/settings.json` is a link into `~/dotfiles/claude/settings.json`: the script
writes through it, while `jq ... > tmp && mv tmp` onto the link would replace it with a regular
file. A settings change is a dotfiles commit.
```

- Task gates: `diff` against the snapshot shows exactly 3 added lines and no
  removed ones; scoped privacy check prints nothing.

### T6: mac-audit baseline to the overlay

- Files (new): `claude/skills/mac-audit/` (SD-COPY). Edits in `SKILL.md` and
  `references/agents.md` only.
- `SKILL.md` line 13 ends with these words:

```text
paste the Baseline below into `<BASELINE>`.
```

  Replace them with:

```text
paste `~/.claude/private/mac-audit-baseline.md` into `<BASELINE>` (the word `none` when that file is missing).
```

- `SKILL.md` line 20: its last sentence starts with a backticked `dig`, then
  `returns`, and ends with `fake IPs (198.18.x).` (it names this Mac's VPN
  client). Replace that sentence with:

```text
`dig` may return fake-IP answers (198.18.x) behind a local proxy or VPN client.
```
- `SKILL.md` lines 29..40: the heading `## Baseline (known benign as of
  2026-10-25; re-check only if changed)`, a blank line and ten bullets, up to
  the blank line before `## Limits`. The overlay already holds them. Replace the
  twelve lines with these four:

```text
## Baseline

Known-benign items of this Mac live in `~/.claude/private/mac-audit-baseline.md`, outside the
public dotfiles repo. After the run update that file: add what the user confirmed benign.
```

- `references/agents.md` line 3: replace the parenthetical that starts with
  `(in 2026-10-25 the starship hash` and ends with `were each checked by two agents)`
  with `(an earlier run had three items checked by two agents each)`.
- `references/agents.md` line 7: replace the parenthetical right after
  `auditing the user's own Mac ` (it names the account and the macOS version)
  with ``(account from `id -un`, version from `sw_vers -productVersion`)``.
- `references/agents.md` line 69 starts `2. Wallet extensions: version vs known incidents`
  and names one wallet brand with a version and dates (taken from this Mac's
  history). Replace the whole line with:

```text
2. Wallet extensions: version vs known incidents (web-search each wallet extension's name and version for compromised releases) and browser History for unlocks in the incident window.
```

- Task gates: G-SYN's zsh and python lines for the skill's scripts; `diff`
  against the snapshot touches only the lines above; `grep -c -i baseline
  SKILL.md` prints `3`; scoped privacy check prints nothing.

### T7: obsidian-sr-flashcards vault override

- Files (new): `claude/skills/obsidian-sr-flashcards/` (SD-COPY). Edits in
  `SKILL.md` only.
- Line 3: the `description:` value opens with a parenthetical about the vault
  (from `(` through `here.)`). Delete it and the space after it, so the line
  starts `description: Write, review, fix and lint spaced-repetition flashcards`.
  In the same line wrap the one token that starts with `#` (the deck tag before
  the word `decks`) in backticks: an unquoted ` #` starts a YAML comment and
  would cut the description there.
- Line 48: `Before (a real card from the user's vault):` becomes
  `Before (a typical weak card):`.
- After the H1 line `# Flashcards for Obsidian Spaced Repetition, from technical books`
  and its blank line, insert this line plus one blank line:

```text
Vault-specific overrides: read `~/.claude/private/obsidian-sr-flashcards.md` when it exists; it wins over the plugin workflow below.
```

- Task gates: `head -3 SKILL.md | tail -1 | cut -c1-40` prints
  `description: Write, review, fix and lint`; `diff` against the snapshot touches
  only lines 3, 48 and the two inserted lines; scoped privacy check prints nothing.

### T8: public-repo and repo-knowledge-base

- Files (new): `claude/skills/public-repo/`, `claude/skills/repo-knowledge-base/`
  (SD-COPY).
- `public-repo/SKILL.md` line 20: the backticked copyright string names the
  owner. Replace it with `` `Copyright (c) <year> <git config user.name>` ``.
- `public-repo/SKILL.md` line 32: `never attach the self-hosted runner from the owner's VPS (fork PRs would`
  becomes `never attach a self-hosted runner (fork PRs would`.
- `public-repo/SKILL.md` line 43: `- grep tracked files for the owner's hosts, IPs, ports, domains, username, email: empty.`
  becomes
  ``- `git ls-files -z | xargs -0 grep -nIiE -f <(grep -vE '^[[:space:]]*(#|$)' ~/.claude/private/denylist)`: empty; no denylist file: say so in the report.``
- `repo-knowledge-base/SKILL.md` lines 56..57: replace `(these repos use` with
  `(for example` and `paths: ["app/consumers/*.py",` with `paths: ["src/x/*.py",`.
- Task gates: `diff` against the snapshots touches only those lines; scoped
  privacy check prints nothing.

### T9: tech-note-review vault paths

- Files (new): `claude/skills/tech-note-review/` (SD-COPY). Edits in `SKILL.md`.
- Line 51: replace the backticked book path after `Rogov's book: ` and the
  final period with:

```text
`<vault>/attachments/postgresql_internals-18.pdf`, where `<vault>` is the path in `~/.claude/private/vault` (no such file: ask the user for the PDF once).
```

- Line 74: the text before the backticked `to_obsidian.py`, which reads
  `2. Save with its Obsidian target: `, becomes the text below; the rest of the
  line is unchanged:

```text
2. Save with its Obsidian target (`<vault>`: the path in `~/.claude/private/vault`): 
```
- Line 75: replace the quoted absolute path (a home path into the vault) with
  `"<vault>/Visuals/<EN Name>.excalidraw.md"`; the rest of the line unchanged.
- Task gates: `grep -c '/Users/' SKILL.md` prints `0`; `diff` against the
  snapshot touches only lines 51, 74, 75; scoped privacy check prints nothing.

### T10: /feature lesson wording

- File: `claude/skills/feature/SKILL.md` (tracked).
- Line 46: the wording that names two work services
  becomes `a sibling service missed a consumer reading from `latest` and cost a fix iteration).`
- Task gates: `git diff --stat` shows 1 insertion, 1 deletion.

### T11: install.sh links the whole claude/ tree

- File: `install.sh`.
- Replace lines 371..447 (from the `# ===` line above
  `# Claude Code: the /feature skill and the agents it runs` through the `fi`
  that closes the macOS notifications block, the line before the blank line and
  the `# ===` line above `# Commit signing for this repo`) with this text:

```bash
# =============================================================================
# Claude Code: config from claude/
# =============================================================================
# Skills are directory links; agents, hooks and bin are file links:
# ~/.claude/skills and ~/.claude/agents also hold entries from outside this repo.
echo "Linking Claude Code skills, agents and hooks..."
mkdir -p ~/.claude/skills ~/.claude/agents ~/.claude/hooks ~/.claude/bin ~/.claude/themes
for src in "$DOTFILES"/claude/skills/*/; do
  src="${src%/}"
  name="$(basename "$src")"
  if [[ "$OS" != "Darwin" && "$name" == mac-* ]]; then
    continue
  fi
  dst="$HOME/.claude/skills/$name"
  if [[ -d "$dst" && ! -L "$dst" ]]; then
    # Older installs linked only SKILL.md into a real directory
    if [[ -n "$(find "$dst" -mindepth 1 ! -type l)" ]]; then
      echo "Skipping $dst: a real directory with files, move it aside first"
      continue
    fi
    find "$dst" -mindepth 1 -type l -delete
    rmdir "$dst"
  fi
  ln -sfn "$src" "$dst"
done
ln -sf "$DOTFILES"/claude/agents/*.md ~/.claude/agents/
ln -sf "$DOTFILES"/claude/hooks/*.sh "$DOTFILES"/claude/hooks/*.py ~/.claude/hooks/
ln -sf "$DOTFILES"/claude/bin/* ~/.claude/bin/
ln -sf "$DOTFILES/claude/statusline.sh" ~/.claude/statusline.sh
ln -sf "$DOTFILES/claude/themes/ayu.json" ~/.claude/themes/ayu.json

if [[ "$OS" == "Darwin" ]]; then
  # Instructions and settings come from the repo; personal facts live in
  # ~/.claude/private, which is never linked (CLAUDE.md imports it)
  echo "Linking Claude Code instructions and settings..."
  mkdir -p ~/.claude/private ~/.claude/backups
  chmod 700 ~/.claude/private
  [[ -f ~/.claude/private/CLAUDE.md ]] || : > ~/.claude/private/CLAUDE.md
  for f in CLAUDE.md settings.json; do
    if [[ -f "$HOME/.claude/$f" && ! -L "$HOME/.claude/$f" ]]; then
      mv "$HOME/.claude/$f" "$HOME/.claude/backups/$f.$(date +%Y%m%d-%H%M%S)"
    fi
    ln -sf "$DOTFILES/claude/$f" "$HOME/.claude/$f"
  done

  # The Stop hook is the only alert source: the built-in channel and gopass
  # alerts are turned off, Ghostty drops terminal OSC notifications.
  # A global config key: the same key in settings.json does not override it
  [[ -f ~/.claude.json ]] || echo '{}' > ~/.claude.json
  if ! jq -e '.preferredNotifChannel == "notifications_disabled"' ~/.claude.json >/dev/null; then
    tmp="$(mktemp)"
    jq '.preferredNotifChannel = "notifications_disabled"' ~/.claude.json > "$tmp" && mv "$tmp" ~/.claude.json
  fi

  # Without an existing config gopass would start its interactive setup
  if command -v gopass &>/dev/null && [[ -f ~/.config/gopass/config ]]; then
    gopass config core.notifications false >/dev/null
  fi
else
  # Linux keeps a local settings.json: only the status line and theme keys
  settings="$HOME/.claude/settings.json"
  [[ -f "$settings" ]] || echo '{}' > "$settings"
  if ! jq -e '.statusLine.command == "~/.claude/statusline.sh"' "$settings" >/dev/null; then
    tmp="$(mktemp)"
    jq '.statusLine = {"type": "command", "command": "~/.claude/statusline.sh"}' \
      "$settings" > "$tmp" && mv "$tmp" "$settings"
  fi
  if ! jq -e '.theme == "custom:ayu"' "$settings" >/dev/null; then
    tmp="$(mktemp)"
    jq '.theme = "custom:ayu"' "$settings" > "$tmp" && mv "$tmp" "$settings"
  fi
fi

# =============================================================================
# Personal-data guard for this repo
# =============================================================================
# .githooks/pre-commit refuses staged lines matching ~/.claude/private/denylist
git -C "$DOTFILES" config core.hooksPath .githooks
```

- Must not change: everything outside lines 371..447, bash 3.2 compatibility
  (`.claude/rules/shell-scripts.md`), the `set -e` behavior of the script.
- Task gates: `bash -n ~/dotfiles/install.sh`; F11 prints only `DONE`; never run
  `install.sh` itself.

F11 runs the new section against fake homes (it never touches the real
`~/.claude`):

```bash
T=$(mktemp -d); R="$HOME/dotfiles"
awk '/^# Claude Code: config from claude\/$/ {on = 1} /^# Personal-data guard for this repo$/ {on = 0} on' "$R/install.sh" > "$T/section.sh"
run() { env -i HOME="$1" PATH="$PATH" DOTFILES="$R" OS="$2" /bin/bash -e "$T/section.sh"; }
fail() { echo "FAIL $*"; }
links_ok() {
  for s in "$R"/claude/skills/*/; do
    n=$(basename "$s")
    case "$n" in mac-*) if [ "$2" != Darwin ]; then [ ! -e "$1/.claude/skills/$n" ] || fail "$1 $n linked on Linux"; continue; fi;; esac
    [ "$(readlink "$1/.claude/skills/$n")" = "$R/claude/skills/$n" ] || fail "$1 skill $n"
  done
  for p in "$R"/claude/agents/*.md "$R"/claude/hooks/*.sh "$R"/claude/hooks/*.py "$R"/claude/bin/* "$R/claude/statusline.sh" "$R/claude/themes/ayu.json"; do
    rel=${p#"$R"/claude/}
    [ "$(readlink "$1/.claude/$rel")" = "$p" ] || fail "$1 $rel"
  done
}
mkdir -p "$T/a"; run "$T/a" Darwin > "$T/a.out" || fail "a exit"
links_ok "$T/a" Darwin
for f in CLAUDE.md settings.json; do [ "$(readlink "$T/a/.claude/$f")" = "$R/claude/$f" ] || fail "a $f"; done
{ [ -f "$T/a/.claude/private/CLAUDE.md" ] && [ ! -s "$T/a/.claude/private/CLAUDE.md" ]; } || fail "a private CLAUDE.md"
[ "$(stat -f %Lp "$T/a/.claude/private")" = 700 ] || fail "a private mode"
[ -z "$(ls "$T/a/.claude/backups")" ] || fail "a backups not empty"
mkdir -p "$T/b/.claude"; echo '{"x": 1}' > "$T/b/.claude/settings.json"; echo old > "$T/b/.claude/CLAUDE.md"
run "$T/b" Darwin > "$T/b.out" || fail "b exit"
for f in CLAUDE.md settings.json; do [ "$(readlink "$T/b/.claude/$f")" = "$R/claude/$f" ] || fail "b $f"; done
[ "$(cat "$T"/b/.claude/backups/CLAUDE.md.*)" = old ] || fail "b CLAUDE.md backup"
jq -e '.x == 1' "$T"/b/.claude/backups/settings.json.* > /dev/null || fail "b settings backup"
mkdir -p "$T/c/.claude/skills/feature"; ln -s "$R/claude/skills/feature/SKILL.md" "$T/c/.claude/skills/feature/SKILL.md"
run "$T/c" Darwin > "$T/c.out" || fail "c exit"
[ "$(readlink "$T/c/.claude/skills/feature")" = "$R/claude/skills/feature" ] || fail "c feature"
mkdir -p "$T/d/.claude/skills/anki"; echo keep > "$T/d/.claude/skills/anki/notes.txt"
run "$T/d" Darwin > "$T/d.out" || fail "d exit"
grep -q -F "Skipping $T/d/.claude/skills/anki: a real directory with files, move it aside first" "$T/d.out" || fail "d message"
{ [ ! -L "$T/d/.claude/skills/anki" ] && [ "$(cat "$T/d/.claude/skills/anki/notes.txt")" = keep ]; } || fail "d touched"
mkdir -p "$T/e"; run "$T/e" Linux > "$T/e.out" || fail "e exit"
links_ok "$T/e" Linux
{ [ -f "$T/e/.claude/settings.json" ] && [ ! -L "$T/e/.claude/settings.json" ]; } || fail "e settings not a regular file"
jq -e '.statusLine.command == "~/.claude/statusline.sh" and .theme == "custom:ayu"' "$T/e/.claude/settings.json" > /dev/null || fail "e keys"
{ [ ! -e "$T/e/.claude/CLAUDE.md" ] && [ ! -e "$T/e/.claude/private" ]; } || fail "e macOS-only items"
run "$T/a" Darwin > "$T/f.out" || fail "f exit"
links_ok "$T/a" Darwin
for s in "$R"/claude/skills/*/; do n=$(basename "$s"); [ ! -L "$s$n" ] || fail "f nested link $n"; done
echo DONE
```

Cases: a fresh macOS home; b regular files in the way get backed up; c the old
`feature` layout; d a real skill directory is left alone; e Linux; f a re-run is
idempotent and nests no link inside a linked directory (the `ln` without `-n`
bug would write into the repo).

### T12: README

- File: `README.md`. Six edits, quoted old text:
- E1: `` `install.sh` does not back anything up: `` becomes
  `` `install.sh` backs up nothing but the two Claude Code files named below: ``
- E2: replace the two bullets that start
  `` - `~/.claude/skills/feature/SKILL.md` and `implementer.md`, `` and
  `` - `~/.claude/statusline.sh` and `~/.claude/themes/ayu.json` are replaced by ``
  (seven lines in total, through `overwritten (Claude Code status line and color theme).`)
  with:

```text
- In `~/.claude/`, an entry named like one in `claude/` is replaced by a link:
  one directory link per skill under `claude/skills/` (`mac-*` skills on macOS
  only), one file link per file in `claude/agents/`, `claude/hooks/` and
  `claude/bin/`, plus `statusline.sh` and `themes/ayu.json`. A real skill
  directory that holds files is skipped with a message instead.
- macOS: `~/.claude/CLAUDE.md` and `~/.claude/settings.json` become links too;
  a regular file there is first moved to `~/.claude/backups/<name>.<timestamp>`.
- Linux: the `statusLine` and `theme` keys in `~/.claude/settings.json` are
  overwritten (Claude Code status line and color theme).
```

- E3: in the backup loop, replace the four lines from
  `  ~/.claude/skills/feature/SKILL.md ~/.claude/agents/implementer.md \`
  through `  ~/.claude/themes/ayu.json; do` with:

```text
  ~/.claude/agents/implementer.md ~/.claude/agents/plan-reviewer.md \
  ~/.claude/agents/acceptance-validator.md ~/.claude/agents/skill-dry-run.md \
  ~/.claude/hooks/notify.sh ~/.claude/hooks/pane-state.sh \
  ~/.claude/hooks/bash-guard.py ~/.claude/hooks/git-commit-guard.py \
  ~/.claude/hooks/no-em-dash.sh ~/.claude/hooks/skill-note-sync.sh \
  ~/.claude/bin/settings-edit.sh ~/.claude/statusline.sh \
  ~/.claude/themes/ayu.json; do
```

- E4: the two lines
  ``default shell to zsh, links the Claude Code `/feature` skill, its agents, the``
  and `status line and the color theme, wires the Claude Code Stop hook, and sets up`
  become
  ``default shell to zsh, links the Claude Code config from `claude/` (instructions,``
  and `settings, skills, agents, hooks, status line, color theme), and sets up`.
- E5: the two lines
  ``no password prompt from `chsh`), links the Claude Code `/feature` skill, its``
  and `agents, the status line and the color theme, and sets up commit signing when`
  become
  ``no password prompt from `chsh`), links the Claude Code skills, agents, hooks,``
  and ``status line and color theme from `claude/`, and sets up commit signing when``.
- E6: in the layout table, replace the four rows whose first cells are
  `` `claude/hooks/notify.sh` ``, `` `claude/hooks/pane-state.sh` ``,
  `` `claude/skills/feature/SKILL.md` `` and `` `claude/agents/*.md` `` with:

```text
| `claude/CLAUDE.md`, `claude/settings.json` | `~/.claude/` | macOS only; global Claude Code instructions and settings; the personal part of the instructions is imported from `~/.claude/private/CLAUDE.md`, which stays outside the repo |
| `claude/skills/*/` | `~/.claude/skills/` | one directory link per skill, `/feature` among them; `mac-*` skills on macOS only |
| `claude/agents/*.md`, `claude/hooks/*`, `claude/bin/*`, `claude/statusline.sh`, `claude/themes/ayu.json` | `~/.claude/` | one link per file: the `/feature` agents, the hooks `settings.json` wires (Stop alert, picker state, guards), `settings-edit.sh`, the status line and color theme |
| `.githooks/pre-commit` | | refuses staged lines that match `~/.claude/private/denylist`; `install.sh` sets `core.hooksPath` |
```

- Task gates: G-DOCS README lines; the README loop is still POSIX sh
  (`sed -n '/^backup=~\/dotfiles-backup/,/^done$/p' README.md | sh -n`).

### T13: repo CLAUDE.md

- File: `CLAUDE.md`. Two edits, net zero lines (the file stays at 199):
- E1: replace the five lines from
  ``- `claude/hooks/` (`notify.sh` Stop alert, `pane-state.sh` picker state),``
  through ``file-linked into `~/.claude/` by `install.sh`; edit them here, not via the links.``
  with:

```text
- `claude/`: the global `~/.claude` config, linked by `install.sh` (skills as
  dir links; `CLAUDE.md`, `settings.json` on macOS only). Personal facts live in
  `~/.claude/private/`, never linked; `.githooks/pre-commit` refuses staged
  lines matching its `denylist`. Design: `plans/claude-*.md`.
```

- E2: replace the three lines from
  ``- `~/.claude/` targets outside `claude/` (other skills, agents) are outside``
  through ``  `diff` against the backup; only the plan is committed.`` with:

```text
- `~/.claude/` targets outside `claude/` (third-party skills) are outside
  git: back them up to `~/.claude/backups/<name>.<ts>` before dispatch, gate on
  `diff` against the backup. A dirty `claude/settings.json` alone (Claude Code
  writes `/model` through the link) is committed first: `chore(claude): sync settings`.
```

- Task gates: G-DOCS CLAUDE.md lines; `wc -l < ~/dotfiles/CLAUDE.md | tr -d ' '` prints `199`.

### T14: setup-dotfiles skill

- File: `.claude/skills/setup-dotfiles/SKILL.md`. Three edits, quoted old text:
- E1: replace the six lines from `  Check only the Claude Code files `install.sh` links over:`
  through `  goes on the move list.` with:

```text
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
```

- E2: in the step 6 block, the line
  `  ~/.claude/skills/feature/SKILL.md ~/.claude/agents/implementer.md`
  becomes
  `  ~/.claude/skills/feature ~/.claude/agents/implementer.md ~/.claude/hooks/pane-state.sh`.
- E3: replace the three lines from `checkout is clean. On macOS also`
  through `` `~/.claude/hooks/notify.sh`. `` with:

```text
checkout is clean. On macOS also `readlink ~/.claude/settings.json` (and the
same for `~/.claude/CLAUDE.md`) prints a path under `~/dotfiles/claude/`.
```

- Task gates: G-DOCS setup-dotfiles lines.

## Seams

| Producer | Consumer | Shared definition |
| --- | --- | --- |
| T0 guard | every later commit | SD-GUARD, overlay `denylist` format (SD-PATHS) |
| T1, T4..T9 copies | T11 links, F11 fixture | SD-LISTS, SD-LINKS (skill dirs under `claude/skills/`) |
| T3 `skill-note-sync.sh` | T9 tech-note-review | overlay `vault` (SD-PATHS) |
| T2 `CLAUDE.md` import | T11 empty `private/CLAUDE.md` | SD-LINKS macOS bullet |
| T11 install.sh | T12 README, T13 CLAUDE.md, T14 setup skill | SD-LINKS |
| T3 `settings-edit.sh` | T5 cc-settings note | write-through behavior (T3) |
| T8 public-repo gate | T0 guard | overlay `denylist` format |

## Not doing

- Third-party skills `excalidraw-diagram`, `excalidraw-skill`, `system-design`
  (no license in the copies) and the agent `go-code-reviewer.md` (unknown
  origin) stay local; `tech-note-review` and `system-design-diagram` keep
  calling them by their `~/.claude/skills/...` paths.
- `confluence-doc` stays local: it only makes sense for one work repo.
- Runtime state, `settings.local.json`, `projects/` (auto memory), `synced/`,
  `.trash/`.
- Em dashes already inside moved files (the move keeps their text; cleaning
  them is a separate task) and Russian trigger phrases or card examples (this
  repo already ships Russian text).
- Rewriting history for personal traces already pushed (home paths in older
  plans, two work names in the `/feature` lesson fixed by T10).
- `everything.md` (it lags the configs by design; `docs-sync` refreshes it).

## Post-merge (orchestrator)

After the ff-merge and push, switch the live entries, item by item. An item
whose live copy changed after the snapshot is skipped and reported, never
overwritten.

```sh
S=~/.claude/backups/claude-home-move
R=~/dotfiles/claude
mkdir -p "$S/replaced/skills" "$S/replaced/hooks" "$S/replaced/bin"
skipped=""
for item in skills/anki skills/anki-addon skills/anki-grammar skills/cc-settings \
  skills/git-history-rewrite skills/mac-audit skills/mac-space skills/obsidian-sr-flashcards \
  skills/page-shot skills/public-repo skills/refactor-proof skills/repo-knowledge-base \
  skills/retro skills/session-handoff skills/system-design-diagram skills/tech-note-review \
  skills/tmux-cleanup hooks/bash-guard.py hooks/git-commit-guard.py hooks/no-em-dash.sh \
  hooks/skill-note-sync.sh bin/settings-edit.sh CLAUDE.md; do
  if diff -rq -x __pycache__ -x '*.pyc' -x .DS_Store "$S/snapshot/$item" ~/.claude/"$item" > /dev/null; then
    mv ~/.claude/"$item" "$S/replaced/$item" && ln -s "$R/$item" ~/.claude/"$item"
  else
    skipped="$skipped $item"
  fi
done
echo "skipped:$skipped"
cmp -s ~/.claude/settings.json "$R/settings.json" || cp ~/.claude/settings.json "$R/settings.json"
mv ~/.claude/settings.json "$S/replaced/settings.json" && ln -s "$R/settings.json" ~/.claude/settings.json
rm ~/.claude/skills/feature/SKILL.md && rmdir ~/.claude/skills/feature && ln -s "$R/skills/feature" ~/.claude/skills/feature
git -C ~/dotfiles status --short
```

A changed `claude/settings.json` is committed alone as
`chore(claude): sync settings` and pushed. A skipped item gets its live changes
reviewed against the denylist, copied into the repo, committed, then switched.

AC-POST:

```bash
for n in feature anki anki-addon anki-grammar cc-settings git-history-rewrite mac-audit mac-space obsidian-sr-flashcards page-shot public-repo refactor-proof repo-knowledge-base retro session-handoff system-design-diagram tech-note-review tmux-cleanup; do
  [ "$(readlink ~/.claude/skills/$n)" = "$HOME/dotfiles/claude/skills/$n" ] || echo "FAIL skill $n"
done
for f in CLAUDE.md settings.json hooks/bash-guard.py hooks/git-commit-guard.py hooks/no-em-dash.sh hooks/skill-note-sync.sh bin/settings-edit.sh; do
  [ "$(readlink ~/.claude/$f)" = "$HOME/dotfiles/claude/$f" ] || echo "FAIL $f"
done
ls ~/.claude/skills/*/SKILL.md | wc -l
git -C ~/dotfiles status --short
git -C ~/dotfiles config core.hooksPath
[ "$(claude -p --model haiku 'Quote the first line under the "## Identity" heading of your user-level instructions, verbatim, nothing else.')" = "$(head -1 ~/.claude/private/CLAUDE.md)" ] && echo identity-ok || echo identity-FAIL
```

## Rollback

Per item: `rm ~/.claude/<item>` (a link) and
`mv ~/.claude/backups/claude-home-move/replaced/<item> ~/.claude/<item>`.
`feature`: `rm ~/.claude/skills/feature`, then
`mkdir ~/.claude/skills/feature && ln -s ~/dotfiles/claude/skills/feature/SKILL.md ~/.claude/skills/feature/SKILL.md`.
The repo side is a normal `git revert` of the merged commits.
