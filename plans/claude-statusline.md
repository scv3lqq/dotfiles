# Claude Code status line

## Goal

A minimal, low-contrast Claude Code status line kept in this repo: one row in
the tmux-dotbar gray (`#565B66`) showing where the session is (directory, git
branch, linked worktree), which model and effort it runs, and how full the
context is. Color appears only when something needs attention: context at 60%
(yellow) and 80% (red); the 5h and 7d rate limits are hidden below 80%
(ClaudeBar shows them in the menu bar) and appear yellow at 80%, red at 95%.

Current behavior: `~/.claude/settings.json` has no `statusLine` key, so Claude
Code shows no status line.

Decision (user): own bash + jq script instead of ccstatusline. Reasons: one jq
and at most two git calls per repaint versus a Node start (70 ms or more, about
1 s via `npx`), no npm package outside the repo, threshold-based visibility.
Docs: https://code.claude.com/docs/en/statusline (stdin JSON schema, `statusLine`
settings key, exit code 0 plus stdout required, ANSI colors allowed).

Example rows (gray unless noted):

```
dotfiles  main · opus 5.5 xhigh · 23%
dotfiles  main · opus 5.5 xhigh · 64%            (64% yellow)
dotfiles  main · opus 5.5 xhigh · 23% · 5h 86%   (5h 86% yellow)
dotfiles  feat/x ⎇ wt · opus 5.5 xhigh · 23%
```

## Acceptance criteria

1. The fixture suite (Shared definitions, "Fixture suite") prints only `PASS`
   lines and exits 0: `bash <suite> ; echo "rc=$?"` ends with `rc=0` and
   `grep -c FAIL` on its output is `0`.
2. `/bin/bash -n claude/statusline.sh` exits 0 (macOS system bash 3.2).
3. `git ls-files -s claude/statusline.sh | cut -c1-6` prints `100755`.
4. `bash -n install.sh` exits 0, and
   `grep -cF 'ln -sf "$DOTFILES/claude/statusline.sh" ~/.claude/statusline.sh' install.sh`
   prints `1`.
5. `grep -cF '"command": "~/.claude/statusline.sh"' install.sh` prints `1`.
6. `grep -cF 'the status line, wires the Claude Code Stop hook' README.md`
   prints `1`; `grep -cF 'agents and the status line, and sets up commit signing' README.md`
   prints `1`; `grep -cF '~/.claude/agents/skill-dry-run.md ~/.claude/statusline.sh; do' README.md`
   prints `1`; `grep -cF 'is overwritten (Claude Code status line).' README.md`
   prints `1`.
7. `grep -cF 'statusline.sh`: the status line. `install.sh' CLAUDE.md` prints `1`,
   and `wc -l < CLAUDE.md` prints a number not above `199`.
8. Live (after T4): `readlink ~/.claude/statusline.sh` prints
   `$HOME/dotfiles/claude/statusline.sh` (expanded);
   `jq -c .statusLine ~/.claude/settings.json` prints
   `{"type":"command","command":"~/.claude/statusline.sh"}`.
9. Live: `diff <(jq -S 'del(.statusLine)' <backup>) <(jq -S 'del(.statusLine)' ~/.claude/settings.json)`
   prints nothing (the backup path is given in the dispatch prompt): no other
   key changed.
10. `git diff main...HEAD --stat` lists exactly `CLAUDE.md`, `README.md`,
    `claude/statusline.sh`, `install.sh`, `plans/claude-statusline.md`.

## Gates

Run from the repo root:

- `/bin/bash -n claude/statusline.sh`
- `bash -n install.sh`
- `test -x claude/statusline.sh`
- the Fixture suite below
- `git diff --check main...HEAD`

There is no shellcheck on this machine and no test suite in the repo.

## Shared definitions

### Paths and settings value

- Script in the repo: `claude/statusline.sh`, git mode `100755`.
- Live link: `~/.claude/statusline.sh` -> `$DOTFILES/claude/statusline.sh`.
- Settings value, exactly: `.statusLine = {"type": "command", "command": "~/.claude/statusline.sh"}`
  (no `padding`, no `refreshInterval`: nothing in the row is time-based, and
  Claude Code re-runs the script itself when a rate-limit window resets).

### Output format

One line on stdout, then exit 0. The line is:

```
<G><segments joined by " · "><RST>\n
```

- `G` = `\033[38;2;86;91;102m` (truecolor `#565B66`, the tmux-dotbar gray),
  `Y` = `\033[33m`, `R` = `\033[31m` (theme palette yellow and red),
  `RST` = `\033[0m`.
- Separator: space, U+00B7 middle dot, space (` · `).
- A colored segment is written as `<Y or R><text><G>`, so the gray resumes.

Segments, in this order, each omitted when empty:

1. Location: `<dir>`, then `  <branch>` (two spaces) when there is a branch,
   then ` ⎇ <worktree>` (U+2387) when there is a worktree name.
   - `dir`: `~` when cwd equals `$HOME`; otherwise the last path component;
     `/` when that is empty.
   - `branch`: only when cwd is an existing directory:
     `git -C "$cwd" symbolic-ref --short -q HEAD`, falling back to
     `git -C "$cwd" rev-parse --short HEAD` (detached HEAD), stderr discarded.
     No `git status`: no dirty marker. Longer than 32 characters: the first 31
     characters plus `…` (U+2026).
2. Agent name (`--agent` sessions).
3. Model plus effort: `<model> <effort>`, either part may be empty.
4. Context: `<ctx>%`; `R` at 80 and above, `Y` at 60 and above, else gray.
5. `5h <n>%`: only when the 5h limit is 80 or above; `R` at 95 and above, else `Y`.
6. `7d <n>%`: same rule for the 7-day limit.

### Fixture suite

Run as `bash <file>` or `bash <<'EOF' ... EOF` from anywhere inside the repo.
It leaves its fixture repos in a `mktemp -d` directory (prints the path).

```bash
SL="$(git rev-parse --show-toplevel)/claude/statusline.sh"
T=$(mktemp -d)
echo "fixtures in $T"
git init -q -b demo-branch "$T/repo"
git init -q -b feature/this-is-a-very-long-branch-name-for-tests "$T/long"
git init -q -b main "$T/det"
git -C "$T/det" -c commit.gpgsign=false -c user.name=t -c user.email=t@example.com \
  commit -q --allow-empty -m init
git -C "$T/det" checkout -q --detach
mkdir "$T/plain"
SHA=$(git -C "$T/det" rev-parse --short HEAD)
fail=0
mk() { jq -cn --arg cwd "$1" "{workspace: {current_dir: \$cwd}} * $2"; }
raw() { printf '%s' "$1" | "$SL"; }
raw_has() { perl -0777 -ne 'BEGIN{$p=shift @ARGV; $p =~ s/\\e/\e/g} exit(index($_, $p) < 0 ? 1 : 0)' "$1"; }
check() {
  out=$(raw "$2"); rc=$?
  got=$(printf '%s' "$out" | perl -pe 's/\e\[[0-9;]*m//g')
  if [ "$rc" = 0 ] && [ "$got" = "$3" ]; then echo "PASS $1"
  else echo "FAIL $1 rc=$rc got=[$got] want=[$3]"; fail=1; fi
}
color() {
  if raw "$2" | raw_has "$3"; then r=yes; else r=no; fi
  if [ "$r" = "$4" ]; then echo "PASS $1"
  else echo "FAIL $1 substring [$3] present=$r want=$4"; fail=1; fi
}
J1=$(mk "$T/repo" '{model: {id: "claude-opus-5-5"}, effort: {level: "xhigh"}, context_window: {used_percentage: 23.7}}')
check C1 "$J1" 'repo  demo-branch · opus 5.5 xhigh · 23%'
check C2 "$(mk "$T/plain" '{model: {id: "claude-sonnet-4-5-20250929"}, context_window: {used_percentage: null}}')" 'plain · sonnet 4.5 · 0%'
J3=$(mk "$T/plain" '{model: {id: "claude-opus-5-5[1m]"}, effort: {level: "high"}, context_window: {used_percentage: 64}}')
check C3 "$J3" 'plain · opus 5.5 high · 64%'
color C3c "$J3" '\e[33m64%\e[38;2;86;91;102m' yes
color C4 "$(mk "$T/plain" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 85}}')" '\e[31m85%\e[38;2;86;91;102m' yes
J5=$(mk "$T/plain" '{model: {id: "claude-opus-5-5"}, effort: {level: "high"}, context_window: {used_percentage: 59.9}}')
check C5 "$J5" 'plain · opus 5.5 high · 59%'
color C5y "$J5" '\e[33m' no
color C5r "$J5" '\e[31m' no
J6=$(mk "$T/plain" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 10}, rate_limits: {five_hour: {used_percentage: 86.4}, seven_day: {used_percentage: 41}}}')
check C6 "$J6" 'plain · opus 5.5 · 10% · 5h 86%'
color C6c "$J6" '\e[33m5h 86%\e[38;2;86;91;102m' yes
J7=$(mk "$T/plain" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 10}, rate_limits: {five_hour: {used_percentage: 79.9}, seven_day: {used_percentage: 97}}}')
check C7 "$J7" 'plain · opus 5.5 · 10% · 7d 97%'
color C7c "$J7" '\e[31m7d 97%\e[38;2;86;91;102m' yes
check C8 "$(mk "$T/repo" '{workspace: {git_worktree: "wt"}, model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 5}}')" 'repo  demo-branch ⎇ wt · opus 5.5 · 5%'
check C9 "$(mk "$T/repo" '{agent: {name: "reviewer"}, model: {id: "claude-haiku-5-5"}, effort: {level: "medium"}, context_window: {used_percentage: 5}}')" 'repo  demo-branch · reviewer · haiku 5.5 medium · 5%'
check C10 "$(mk "$T/plain" '{model: {id: "us.anthropic.claude-opus-4-1-20250805-v1:0"}, context_window: {used_percentage: 1}}')" 'plain · opus 4.1 · 1%'
check C11 "$(mk "$T/plain" '{model: {id: "claude-opus-4-20250514"}, context_window: {used_percentage: 1}}')" 'plain · opus 4 · 1%'
check C12 "$(mk "$T/plain" '{model: {id: "gpt-x", display_name: "Custom Model"}, context_window: {used_percentage: 1}}')" 'plain · custom model · 1%'
check C13 "$(mk "$T/long" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 1}}')" 'long  feature/this-is-a-very-long-bra… · opus 5.5 · 1%'
check C14 "$(mk "$T/det" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 1}}')" "det  $SHA · opus 5.5 · 1%"
check C15 "$(mk "$HOME" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 1}}')" '~ · opus 5.5 · 1%'
out=$(printf 'not json' | "$SL"); rc=$?
if [ "$rc" = 0 ] && [ -z "$out" ]; then echo "PASS C16"; else echo "FAIL C16 rc=$rc out=[$out]"; fail=1; fi
check C17 "$(mk "$T/plain" '{context_window: {used_percentage: 3}}')" 'plain · 3%'
if raw "$J1" | perl -0777 -ne 'exit(/\A\e\[38;2;86;91;102m[^\n]*\e\[0m\n\z/ ? 0 : 1)'; then echo "PASS C18"; else echo "FAIL C18 framing"; fail=1; fi
check C19 "$(mk "$T/gone" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 1}}')" 'gone · opus 5.5 · 1%'
t0=$(perl -MTime::HiRes=time -e 'printf "%.3f", time')
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do raw "$J1" >/dev/null; done
t1=$(perl -MTime::HiRes=time -e 'printf "%.3f", time')
if perl -e "exit(($t1 - $t0) < 1.0 ? 0 : 1)"; then echo "PASS C20 20 runs in $(perl -e "printf '%.3f', $t1 - $t0") s"
else echo "FAIL C20 20 runs took $(perl -e "printf '%.3f', $t1 - $t0") s"; fail=1; fi
exit $fail
```

C15 assumes `$HOME` itself is not inside a git repository (true on the
workstation). C19's directory does not exist on purpose.

## Tasks

### T1: `claude/statusline.sh` (new file), dispatch with `model: sonnet`

Scope: the whole script. No other file.

Behavior (follow Shared definitions "Output format" exactly):

- Shebang `#!/bin/bash`; must run under macOS `/bin/bash` 3.2: no `mapfile`,
  no `${var,,}`, no associative arrays. Header comment in the style of
  `claude/hooks/notify.sh`: what the script is (Claude Code status line, reads
  the session JSON on stdin), and that it prints one line and always exits 0
  because a non-zero exit or empty output blanks the row. Other comments only
  for a non-obvious why.
- No `set -e`. Last statement `exit 0`.
- `command -v jq >/dev/null || exit 0`.
- Read all fields with ONE jq call that reads the script's stdin directly,
  one field per line, into variables with
  `{ IFS= read -r cwd; IFS= read -r wt; IFS= read -r agent; IFS= read -r model; IFS= read -r effort; IFS= read -r ctx; IFS= read -r h5; IFS= read -r d7; } < <(jq -r "$filter" 2>/dev/null)`.
  The filter, verbatim (keep it in a single-quoted variable):

  ```jq
  (.workspace.current_dir // .cwd // ""),
  (.workspace.git_worktree // .worktree.name // ""),
  (.agent.name // ""),
  (((.model.id // "") | capture("claude-(?<f>[a-z]+)-(?<maj>[0-9]+)(-(?<min>[0-9]{1,2})(?![0-9]))?") // null) as $m
    | if $m then $m.f + " " + $m.maj + (if ($m.min // "") != "" then "." + $m.min else "" end)
      else (.model.display_name // "" | ascii_downcase) end),
  (.effort.level // ""),
  (.context_window.used_percentage // 0 | floor),
  (.rate_limits.five_hour.used_percentage // -1 | floor),
  (.rate_limits.seven_day.used_percentage // -1 | floor)
  ```

  `-1` means "window absent". `($m.min // "") != ""` guards against jq builds
  that return `""` for an unmatched optional group.
- `[ -n "$ctx" ] || exit 0`: empty `ctx` means jq failed (invalid input), the
  script prints nothing (fixture C16).
- Location, branch, worktree, truncation: as in "Output format", segment 1.
  Guard git with `[ -d "$cwd" ]` (an empty `-C ""` would mean the current
  directory). `${branch:0:31}` is fine in bash 3.2.
- Colors defined once as `G`, `Y`, `R`, `RST` with `$'\033[...m'` quoting.
- Joining: a small function that appends `" · "` only when the line is not
  empty. Thresholds through one helper that takes the value, the yellow and
  the red threshold and the text, and returns the text wrapped as
  `<Y or R><text><G>` or plain. Context uses 60/80; 5h and 7d are added only
  when `>= 80` and use 80/95.
- Print with `printf '%s%s%s\n' "$G" "$out" "$RST"`.
- Literal non-ASCII characters in the file: `·` (U+00B7), `⎇` (U+2387),
  `…` (U+2026). No em dash anywhere.
- `chmod +x claude/statusline.sh` so git records mode `100755`.

Must not: call `git status`, read `COLUMNS`, use `tput`, write any file, print
to stderr, take more than one jq call.

Task gates: `/bin/bash -n claude/statusline.sh`, `test -x claude/statusline.sh`,
the Fixture suite (all PASS, rc 0).

Done: the file exists, executable, gates green.

### T2: `install.sh` (wire the link and the settings key)

Scope: one insert. Anchor (verified, lines 378-379):

```
ln -sf "$DOTFILES/claude/skills/feature/SKILL.md" ~/.claude/skills/feature/SKILL.md
ln -sf "$DOTFILES"/claude/agents/*.md ~/.claude/agents/
```

Insert right after these two lines (before the blank line and the
`# Claude Code notifications (macOS)` banner), outside any OS branch, since
the status line works on macOS and Linux alike:

```bash

# =============================================================================
# Claude Code status line
# =============================================================================
echo "Linking Claude Code status line..."
ln -sf "$DOTFILES/claude/statusline.sh" ~/.claude/statusline.sh
settings="$HOME/.claude/settings.json"
[[ -f "$settings" ]] || echo '{}' > "$settings"
if ! jq -e '.statusLine.command == "~/.claude/statusline.sh"' "$settings" >/dev/null; then
  tmp="$(mktemp)"
  jq '.statusLine = {"type": "command", "command": "~/.claude/statusline.sh"}' \
    "$settings" > "$tmp" && mv "$tmp" "$settings"
fi
```

`~/.claude` exists at that point (`mkdir -p ~/.claude/skills/feature` above);
`jq` is in the package lists of all three package managers. The later macOS
block reassigns `settings` to the same value: leave it unchanged.

Must not change: anything else in `install.sh`.

Task gates: `bash -n install.sh`; criteria 4 and 5.

Done: block inserted verbatim, gates green.

### T3: `README.md` and `CLAUDE.md` (docs)

Scope: four edits in `README.md`, one in `CLAUDE.md`. Each `old_string` below
is verified against the current file.

README edit 1, old:

```
  `~/.claude/agents/` are replaced by links (Claude Code's `/feature`
  skill and the agents it runs).
```

new:

```
  `~/.claude/agents/` are replaced by links (Claude Code's `/feature`
  skill and the agents it runs).
- `~/.claude/statusline.sh` is replaced by a link and the `statusLine` key in
  `~/.claude/settings.json` is overwritten (Claude Code status line).
```

README edit 2, old:

```
  ~/.claude/agents/skill-dry-run.md; do
```

new:

```
  ~/.claude/agents/skill-dry-run.md ~/.claude/statusline.sh; do
```

README edit 3, old:

```
default shell to zsh, links the Claude Code `/feature` skill and its agents,
wires the Claude Code Stop hook, and sets up commit signing for this repo when
`~/.ssh/id_ed25519.pub` exists.
```

new:

```
default shell to zsh, links the Claude Code `/feature` skill, its agents and
the status line, wires the Claude Code Stop hook, and sets up commit signing
for this repo when `~/.ssh/id_ed25519.pub` exists.
```

README edit 4, old:

```
no password prompt from `chsh`), links the Claude Code `/feature` skill and
its agents, and sets up commit signing when `~/.ssh/id_ed25519.pub` exists.
```

new:

```
no password prompt from `chsh`), links the Claude Code `/feature` skill, its
agents and the status line, and sets up commit signing when
`~/.ssh/id_ed25519.pub` exists.
```

CLAUDE.md edit (keeps the line count at 199; the file must stay under 200),
old:

```
- `claude/hooks/`: `notify.sh` (Stop hook, macOS alert) and `pane-state.sh`
  (turn state in pane options for the picker), linked into `~/.claude/hooks/` by
  `install.sh`, which also wires settings.json; see `plans/claude-*.md`.
```

new:

```
- `claude/hooks/`: `notify.sh` (Stop hook, macOS alert), `pane-state.sh` (turn
  state for the picker); `claude/statusline.sh`: the status line. `install.sh`
  links them into `~/.claude/` and wires settings.json; see `plans/claude-*.md`.
```

Must not change: any other line of either file.

Task gates: criteria 6 and 7.

Done: five edits applied verbatim, gates green.

### T4: live apply (no repo files), after T1 and T2 are committed

Scope: apply the T2 block on this machine without running `install.sh`.
The orchestrator has already backed up `~/.claude/settings.json`; the backup
path is in the dispatch prompt.

Run from the repo root, verbatim:

```bash
ln -sf "$HOME/dotfiles/claude/statusline.sh" ~/.claude/statusline.sh
tmp="$(mktemp)"
jq '.statusLine = {"type": "command", "command": "~/.claude/statusline.sh"}' \
  ~/.claude/settings.json > "$tmp" && mv "$tmp" ~/.claude/settings.json
```

Then check: `jq -c .statusLine ~/.claude/settings.json`, `readlink
~/.claude/statusline.sh`, and criterion 9's diff against the backup. Pipe one
fixture through the live link to prove it resolves:
`printf '{"workspace":{"current_dir":"/tmp"},"context_window":{"used_percentage":1}}' | ~/.claude/statusline.sh | perl -pe 's/\e\[[0-9;]*m//g'`
prints `tmp · 1%`.

Must not: edit any other key in `settings.json`, touch repo files, run
`install.sh`.

Task gates: criteria 8 and 9.

Done: link and key in place, the diff against the backup is empty.

## Seams

| Producer | Consumer | Shared definition |
| --- | --- | --- |
| T1 | T2, T4 | Paths and settings value (`claude/statusline.sh`, `~/.claude/statusline.sh`, the `statusLine` object) |
| T2 | T4 | The same `statusLine` object and link command (T4 runs T2's block by hand) |
| T1 | T3 | Docs describe the script by path only; no behavior text to keep in sync |

## Edge cases

- macOS vs Linux: `/bin/bash` 3.2 on macOS (T1 restrictions); `jq` and `git`
  come from install.sh on both; truecolor gray needs RGB support, which
  `tmux/tmux.conf` enables for `xterm-ghostty`; a terminal without it shows a
  close 256-color gray.
- Missing tools: no `jq`, no output (blank row); no `git` or not a repo, no
  branch segment.
- First run of a session: `used_percentage` null gives `0%`; `rate_limits`,
  `effort`, `agent`, worktree fields absent give no segment.
- Dirty worktree: the repo was clean at plan time; T4 touches no repo file.
- First install: `~/.claude/settings.json` missing is created as `{}` by T2's
  block; a different existing `statusLine` is replaced (install.sh owns it).

## Not doing

- ccstatusline, starship-claude, or any npm package.
- Cost, duration, lines changed, prompt-cache stats, session name, PR badge
  (Claude Code shows the PR itself), vim mode, git dirty marker, clock.
- Width handling via `COLUMNS`, multi-line output, `refreshInterval`, `padding`.
- `everything.md` (it lags the configs by design).
- Linux server rollout beyond the install.sh block.
