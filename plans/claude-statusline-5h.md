# Status line: 5h limit bar at the right edge

## Goal

Show the 5-hour rate limit at the right edge of the Claude Code status line,
styled after the user's reference screenshot: `5h ━━━━━━━━━━ 26% ↻ 2h 7m`
(gray label, a 10-cell line whose filled part is Claude orange and whose track
is light gray, the percentage bold and bright, then the time left until the
window resets). The rest of the row stays as it is; the old left-side
`5h <n>%` segment (shown only at 80% and above) goes away. The 7d segment
stays on the left, unchanged.

Current behavior: `claude/statusline.sh` prints one gray row
`<dir>  <branch> · <model effort> · <ctx bar> <ctx>%` plus `5h <n>%` and
`7d <n>%` segments only at 80% and above (`plans/claude-statusline.md`,
`plans/claude-statusline-bar.md`). It never reads `COLUMNS`.
`claude/settings.json` has `statusLine` without `refreshInterval`, so the
script runs only on events (new assistant message, mode change, ...).

Example rows (COLUMNS=100):

```
plain · opus 5.5 · ━───────── 10%                                      5h ━━━━━━━━━━ 26% ↻ 2h 7m
plain · opus 5.5 · ━───────── 10% · 7d 97%                                5h ━━━━━━━━━━ 79% ↻ 41m
```

Decisions (planner, from the screenshot and measurements, see Row geometry):

- Colors sampled from the screenshot: fill `#CD7C5C` -> 256-color 173, track
  `#999999` -> 246, label and reset text `#898989` -> 245 (the existing
  `FILL`), percentage `#E8E6DD` bold -> 254 + bold. Brighter than the gray
  row on purpose: the user asked for the screenshot's look.
- Fill and track are the same glyph `━` (U+2501): the screenshot line has one
  thickness. 10 cells, 10% steps, no half cells.
- Thresholds keep the old 5h semantics: at 80% the fill and the percentage
  turn `Y`, at 95% `R` (the percentage stays bold).
- `refreshInterval: 30`: a terminal resize does not re-run the script, and the
  countdown would freeze in an idle session; 30 s bounds both. One run costs
  about 15 ms.

## Acceptance criteria

1. The Status line suite below prints only `PASS` lines and exits 0:
   `bash <suite> ; echo "rc=$?"` ends with `rc=0`, `grep -c FAIL` is `0`.
2. The Install suite below prints only `PASS` lines and exits 0.
3. `/bin/bash -n claude/statusline.sh` exits 0; `test -x claude/statusline.sh`.
4. `jq -c .statusLine claude/settings.json` prints
   `{"type":"command","command":"~/.claude/statusline.sh","refreshInterval":30}`
   and `git diff main...HEAD --numstat -- claude/settings.json` prints
   `2	1	claude/settings.json`.
5. `bash -n install.sh` exits 0;
   `grep -cF '"refreshInterval": 30}' install.sh` prints `1`;
   `grep -cF '.statusLine.refreshInterval == 30' install.sh` prints `1`;
   `grep -cF '"command": "~/.claude/statusline.sh"' install.sh` prints `1`.
6. `grep -cF 'Status line geometry (2.1.310, fullscreen)' claude/skills/cc-settings/SKILL.md`
   prints `1`, and the T4 block diff gate prints nothing.
7. Live: in the pane running this cycle, after T1 and T2 are committed and one
   assistant message later,
   `tmux capture-pane -p -t "$TMUX_PANE" | grep -c '5h ━━━━━━━━━━ [0-9]*%'`
   prints `1`, and that line, trailing blanks removed, is exactly
   `pane_width - 2` characters long:
   `tmux capture-pane -p -t "$TMUX_PANE" | grep '5h ━━━━━━━━━━' | perl -CS -ne 'chomp; s/\s+$//; print length, "\n"'`
   equals `$(( $(tmux display -p -t "$TMUX_PANE" '#{pane_width}') - 2 ))`.
8. `git diff main...HEAD --stat` lists exactly `claude/statusline.sh`,
   `claude/settings.json`, `install.sh`, `claude/skills/cc-settings/SKILL.md`,
   `plans/claude-statusline-5h.md`, `plans/claude-statusline.md`,
   `plans/claude-statusline-bar.md` (the last three are the planner's commit).

## Gates

- `/bin/bash -n claude/statusline.sh`
- `test -x claude/statusline.sh`
- `bash -n install.sh`
- `jq empty claude/settings.json`
- the Status line suite and the Install suite (both all PASS, rc 0)
- `git diff --check main...HEAD`
- `git diff main...HEAD | perl -CSD -ne '$n++ if /^\+.*\x{2014}/; END { print $n+0, "\n" }'` prints `0`

## Shared definitions

### Row geometry (measured on 2.1.310, `tui: fullscreen`)

- Claude Code indents the status row by 2 columns and cuts it with `…` once
  the text is wider than `COLUMNS - 4` cells. `COLUMNS - 4` cells fit exactly;
  so the last cell of a right-aligned segment lands at column `COLUMNS - 2`.
- `COLUMNS` and `LANG=en_US.UTF-8` are in the script's environment; bash
  `${#s}` then counts characters (in a C locale it counts bytes, which only
  makes the computed gap smaller).
- A terminal resize does not re-run the script; `refreshInterval` re-runs it
  with the new `COLUMNS`.
- `disableAllHooks` also disables the status line; an isolated probe runs with
  `--setting-sources local --settings '{"tui": "fullscreen", "statusLine": {...}}'`,
  and `send-keys BTab` (mode change) re-runs the script.

### statusLine object

Exactly, in both `claude/settings.json` (macOS, linked) and the Linux block of
`install.sh`:

```
{"type": "command", "command": "~/.claude/statusline.sh", "refreshInterval": 30}
```

### Segment 6 format (5h)

- Present only when `rate_limits.five_hour.used_percentage` is present
  (`h5 >= 0`; the jq filter maps absence to -1). Absent: no segment, no
  padding, the row is byte-identical to today's minus the old 5h segment.
- `cells = (h5 * 10 + 50) / 100`, capped at 10; `cells` x `━` in the fill
  color, then `10 - cells` x `━` in `TRACK5`.
- Fill color `hc`: `R` at h5 >= 95, `Y` at h5 >= 80, else `ORANGE`.
  Percentage color `pc`: `hc` at h5 >= 80, else `BRIGHT`; always wrapped as
  `BOLD pc <h5>% NOBOLD`.
- Reset text from `h5r` = `floor(resets_at - now)` seconds (jq `now`; absent
  `resets_at` gives a negative number). `h5r <= 0`: no reset text. Else
  `mins = (h5r + 59) / 60` (rounded up): `mins >= 60` gives ` ↻ <mins/60>h <mins%60>m`,
  else ` ↻ <mins>m`. Note the leading space.
- Full segment bytes:
  `FILL "5h " hc <fill> TRACK5 <track> " " BOLD pc <h5> "%" NOBOLD FILL <reset>`.
  Visible width `15 + ${#h5} + ${#reset}`.
- Compact segment bytes: `FILL "5h " BOLD pc <h5> "%" NOBOLD`. Visible width
  `4 + ${#h5}`.
- Gap (spaces between the left row and the segment): `COLUMNS` not a
  positive integer (unset, empty, non-numeric): gap 2, full segment.
  Else `gap = COLUMNS - 4 - <left visible width> - <full width>`; below 2,
  switch to compact and recompute with the compact width; still below 2,
  gap 2 (Claude Code then cuts the row).
- Left visible width: `${#plain}` with `plain` = the left row `out` with every
  `ESC [ <digits and ;> m` removed.
- Output: `printf '%s%s%s%s\n' "$G" "$out" "<gap spaces><segment>" "$RST"`.

New color variables (256-color indexes, see `cc-settings` on tmux):
`ORANGE` `\033[38;5;173m`, `TRACK5` `\033[38;5;246m`, `BRIGHT`
`\033[38;5;254m`, `BOLD` `\033[1m`, `NOBOLD` `\033[22m`. Existing: `G` 240,
`Y` 33, `R` 31, `FILL` 245, `TRACK` 237, `RST` 0.

### Status line suite

Supersedes the suite in `plans/claude-statusline-bar.md`. Run as
`bash <file>` from anywhere inside the repo. C1..C23 except C6, C7 and C20
are unchanged from the previous suite.

```bash
export LC_ALL=en_US.UTF-8
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
NOW=$(date +%s)
fail=0
mk() { jq -cn --arg cwd "$1" "{workspace: {current_dir: \$cwd}} * $2"; }
raw() { printf '%s' "$1" | env -u COLUMNS "$SL"; }
rawc() { printf '%s' "$2" | COLUMNS="$1" "$SL"; }
strip() { perl -pe 's/\e\[[0-9;]*m//g'; }
sp() { printf '%*s' "$1" ''; }
raw_has() { perl -0777 -ne 'BEGIN{$p=shift @ARGV; $p =~ s/\\e/\e/g} exit(index($_, $p) < 0 ? 1 : 0)' "$1"; }
check() {
  out=$(raw "$2"); rc=$?
  got=$(printf '%s' "$out" | strip)
  if [ "$rc" = 0 ] && [ "$got" = "$3" ]; then echo "PASS $1"
  else echo "FAIL $1 rc=$rc got=[$got] want=[$3]"; fail=1; fi
}
checkc() {
  out=$(rawc "$2" "$3"); rc=$?
  got=$(printf '%s' "$out" | strip)
  if [ "$rc" = 0 ] && [ "$got" = "$4" ]; then echo "PASS $1"
  else echo "FAIL $1 rc=$rc got=[$got] want=[$4]"; fail=1; fi
}
color() {
  if raw "$2" | raw_has "$3"; then r=yes; else r=no; fi
  if [ "$r" = "$4" ]; then echo "PASS $1"
  else echo "FAIL $1 substring [$3] present=$r want=$4"; fail=1; fi
}
h5j() { mk "$T/plain" "{model: {id: \"claude-opus-5-5\"}, context_window: {used_percentage: 10}, rate_limits: {five_hour: $1}}"; }
L24='plain · opus 5.5 · ━───────── 10%'
F24='5h ━━━━━━━━━━ 26% ↻ 2h 7m'
J24=$(h5j "{used_percentage: 26.4, resets_at: $((NOW + 7620))}")
J1=$(mk "$T/repo" '{model: {id: "claude-opus-5-5"}, effort: {level: "xhigh"}, context_window: {used_percentage: 23.7}}')
check C1 "$J1" 'repo  demo-branch · opus 5.5 xhigh · ━━╾─────── 23%'
color C1r "$J1" '\e[38;5;245m━━╾\e[38;5;237m───────\e[38;5;240m 23%' yes
J2=$(mk "$T/plain" '{model: {id: "claude-sonnet-4-5-20250929"}, context_window: {used_percentage: null}}')
check C2 "$J2" 'plain · sonnet 4.5 · ────────── 0%'
color C2r "$J2" '\e[38;5;245m\e[38;5;237m──────────\e[38;5;240m 0%' yes
J3=$(mk "$T/plain" '{model: {id: "claude-opus-5-5[1m]"}, effort: {level: "high"}, context_window: {used_percentage: 64}}')
check C3 "$J3" 'plain · opus 5.5 high · ━━━━━━╾─── 64%'
color C3c "$J3" '\e[33m━━━━━━╾\e[38;5;237m───\e[38;5;240m \e[33m64%\e[38;5;240m' yes
J4=$(mk "$T/plain" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 85}}')
check C4 "$J4" 'plain · opus 5.5 · ━━━━━━━━╾─ 85%'
color C4c "$J4" '\e[31m━━━━━━━━╾\e[38;5;237m─\e[38;5;240m \e[31m85%\e[38;5;240m' yes
J5=$(mk "$T/plain" '{model: {id: "claude-opus-5-5"}, effort: {level: "high"}, context_window: {used_percentage: 59.9}}')
check C5 "$J5" 'plain · opus 5.5 high · ━━━━━━──── 59%'
color C5y "$J5" '\e[33m' no
color C5r "$J5" '\e[31m' no
J6=$(mk "$T/plain" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 10}, rate_limits: {five_hour: {used_percentage: 86.4}, seven_day: {used_percentage: 41}}}')
check C6 "$J6" 'plain · opus 5.5 · ━───────── 10%  5h ━━━━━━━━━━ 86%'
color C6c "$J6" '\e[38;5;245m5h \e[33m━━━━━━━━━\e[38;5;246m━ \e[1m\e[33m86%\e[22m\e[38;5;245m\e[0m' yes
J7=$(mk "$T/plain" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 10}, rate_limits: {five_hour: {used_percentage: 79.9}, seven_day: {used_percentage: 97}}}')
check C7 "$J7" 'plain · opus 5.5 · ━───────── 10% · 7d 97%  5h ━━━━━━━━━━ 79%'
color C7c "$J7" '\e[31m7d 97%\e[38;5;240m' yes
color C7o "$J7" '\e[38;5;173m━━━━━━━━\e[38;5;246m━━ \e[1m\e[38;5;254m79%\e[22m' yes
check C8 "$(mk "$T/repo" '{workspace: {git_worktree: "wt"}, model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 5}}')" 'repo  demo-branch ⎇ wt · opus 5.5 · ╾───────── 5%'
check C9 "$(mk "$T/repo" '{agent: {name: "reviewer"}, model: {id: "claude-haiku-5-5"}, effort: {level: "medium"}, context_window: {used_percentage: 5}}')" 'repo  demo-branch · reviewer · haiku 5.5 medium · ╾───────── 5%'
check C10 "$(mk "$T/plain" '{model: {id: "us.anthropic.claude-opus-4-1-20250805-v1:0"}, context_window: {used_percentage: 1}}')" 'plain · opus 4.1 · ────────── 1%'
check C11 "$(mk "$T/plain" '{model: {id: "claude-opus-4-20250514"}, context_window: {used_percentage: 1}}')" 'plain · opus 4 · ────────── 1%'
check C12 "$(mk "$T/plain" '{model: {id: "gpt-x", display_name: "Custom Model"}, context_window: {used_percentage: 1}}')" 'plain · custom model · ────────── 1%'
check C13 "$(mk "$T/long" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 1}}')" 'long  feature/this-is-a-very-long-bra… · opus 5.5 · ────────── 1%'
check C14 "$(mk "$T/det" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 1}}')" "det  $SHA · opus 5.5 · ────────── 1%"
check C15 "$(mk "$HOME" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 1}}')" '~ · opus 5.5 · ────────── 1%'
out=$(printf 'not json' | "$SL"); rc=$?
if [ "$rc" = 0 ] && [ -z "$out" ]; then echo "PASS C16"; else echo "FAIL C16 rc=$rc out=[$out]"; fail=1; fi
check C17 "$(mk "$T/plain" '{context_window: {used_percentage: 3}}')" 'plain · ╾───────── 3%'
if raw "$J1" | perl -0777 -ne 'exit(/\A\e\[38;5;240m[^\n]*\e\[0m\n\z/ ? 0 : 1)'; then echo "PASS C18"; else echo "FAIL C18 framing"; fail=1; fi
check C19 "$(mk "$T/gone" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 1}}')" 'gone · opus 5.5 · ────────── 1%'
t0=$(perl -MTime::HiRes=time -e 'printf "%.3f", time')
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do rawc 100 "$J24" >/dev/null; done
t1=$(perl -MTime::HiRes=time -e 'printf "%.3f", time')
if perl -e "exit(($t1 - $t0) < 1.0 ? 0 : 1)"; then echo "PASS C20 20 runs in $(perl -e "printf '%.3f', $t1 - $t0") s"
else echo "FAIL C20 20 runs took $(perl -e "printf '%.3f', $t1 - $t0") s"; fail=1; fi
J21=$(mk "$T/plain" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 100}}')
check C21 "$J21" 'plain · opus 5.5 · ━━━━━━━━━━ 100%'
color C21r "$J21" '\e[31m━━━━━━━━━━\e[38;5;237m\e[38;5;240m \e[31m100%\e[38;5;240m' yes
check C22 "$(mk "$T/plain" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 150}}')" 'plain · opus 5.5 · ━━━━━━━━━━ 150%'
check C23 "$(mk "$T/plain" '{model: {id: "claude-opus-5-5"}, context_window: {used_percentage: 17}}')" 'plain · opus 5.5 · ━╾──────── 17%'
checkc C24 100 "$J24" "$L24$(sp 38)$F24"
color C24r "$J24" '\e[38;5;245m5h \e[38;5;173m━━━\e[38;5;246m━━━━━━━ \e[1m\e[38;5;254m26%\e[22m\e[38;5;245m ↻ 2h 7m\e[0m' yes
J25=$(h5j "{used_percentage: 5, resets_at: $((NOW + 2520))}")
check C25 "$J25" "$L24  5h ━━━━━━━━━━ 5% ↻ 42m"
color C25r "$J25" '\e[38;5;173m━\e[38;5;246m━━━━━━━━━ ' yes
J26=$(h5j "{used_percentage: 26.4, resets_at: $((NOW - 100))}")
check C26 "$J26" "$L24  5h ━━━━━━━━━━ 26%"
color C26r "$J26" '26%\e[22m\e[38;5;245m\e[0m' yes
check C27 "$(h5j "{used_percentage: 26.4, resets_at: $((NOW + 3600))}")" "$L24  5h ━━━━━━━━━━ 26% ↻ 1h 0m"
checkc C28 60 "$J24" "$L24$(sp 17)5h 26%"
checkc C29 30 "$J24" "$L24  5h 26%"
checkc C30 64 "$J24" "$L24  $F24"
checkc C31 63 "$J24" "$L24$(sp 20)5h 26%"
out=$(printf '%s' "$J24" | LC_ALL=C COLUMNS=100 "$SL"); rc=$?
got=$(printf '%s' "$out" | strip)
n=$(printf '%s' "$got" | perl -CS -ne 'print length')
case "$got" in *"$F24") tail_ok=yes ;; *) tail_ok=no ;; esac
if [ "$rc" = 0 ] && [ "$n" -le 96 ] && [ "$tail_ok" = yes ]; then echo "PASS C32 C locale width $n"
else echo "FAIL C32 rc=$rc width=$n tail=$tail_ok got=[$got]"; fail=1; fi
checkc C33 100 "$J1" 'repo  demo-branch · opus 5.5 xhigh · ━━╾─────── 23%'
J34=$(h5j '{used_percentage: 0}')
check C34 "$J34" "$L24  5h ━━━━━━━━━━ 0%"
color C34r "$J34" '\e[38;5;173m\e[38;5;246m━━━━━━━━━━ \e[1m\e[38;5;254m0%\e[22m' yes
J35=$(h5j '{used_percentage: 97}')
check C35 "$J35" "$L24  5h ━━━━━━━━━━ 97%"
color C35r "$J35" '\e[31m━━━━━━━━━━\e[38;5;246m \e[1m\e[31m97%\e[22m' yes
J36=$(h5j '{used_percentage: 150}')
check C36 "$J36" "$L24  5h ━━━━━━━━━━ 150%"
color C36r "$J36" '\e[31m━━━━━━━━━━\e[38;5;246m \e[1m\e[31m150%' yes
checkc C37 abc "$J24" "$L24  $F24"
if rawc 100 "$J24" | perl -0777 -ne 'exit(/\A\e\[38;5;240m[^\n]*\e\[0m\n\z/ ? 0 : 1)'; then echo "PASS C38"; else echo "FAIL C38 framing"; fail=1; fi
check C39 "$(h5j "{used_percentage: 26.4, resets_at: $((NOW + 30))}")" "$L24  5h ━━━━━━━━━━ 26% ↻ 1m"
color C40 "$(h5j '{used_percentage: 80}')" '\e[33m━━━━━━━━\e[38;5;246m━━ \e[1m\e[33m80%' yes
color C41 "$(h5j '{used_percentage: 95}')" '\e[31m━━━━━━━━━━\e[38;5;246m \e[1m\e[31m95%' yes
exit $fail
```

### Install suite

Runs the Linux settings block of `install.sh` against a temp `HOME` (writes
nothing outside it). Run as `bash <file>` from anywhere inside the repo.

```bash
R="$(git rev-parse --show-toplevel)"
H=$(mktemp -d)
mkdir -p "$H/.claude"
blk="$H/block.sh"
sed -n '/# Linux keeps a local settings.json/,/^fi$/p' "$R/install.sh" | sed '$d' > "$blk"
fail=0
if grep -q 'Linux keeps a local settings.json' "$blk" && grep -qF "jq '.theme = \"custom:ayu\"'" "$blk"; then echo "PASS I0 markers"
else echo "FAIL I0 markers"; exit 1; fi
want='{"type":"command","command":"~/.claude/statusline.sh","refreshInterval":30}'
s="$H/.claude/settings.json"
run() { HOME="$H" bash "$blk"; }
ok() { if [ "$2" = "$3" ]; then echo "PASS $1"; else echo "FAIL $1 got=[$2] want=[$3]"; fail=1; fi; }
run
ok I1 "$(jq -c .statusLine "$s")" "$want"
ok I1t "$(jq -r .theme "$s")" "custom:ayu"
echo '{"statusLine":{"type":"command","command":"~/.claude/statusline.sh"},"keep":1}' > "$s"
run
ok I2 "$(jq -c .statusLine "$s")" "$want"
ok I2k "$(jq -c .keep "$s")" "1"
cp "$s" "$H/before.json"
run
if cmp -s "$s" "$H/before.json"; then echo "PASS I3 idempotent"; else echo "FAIL I3 idempotent"; fail=1; fi
echo '{"statusLine":{"type":"command","command":"other.sh","refreshInterval":30}}' > "$s"
run
ok I4 "$(jq -c .statusLine "$s")" "$want"
exit $fail
```

## Tasks

Wave 1: T1, T2, T3 in parallel (disjoint files). Wave 2: T4.

### T1: `claude/statusline.sh`, segment 6 (5h) at the right edge

Scope: only `claude/statusline.sh`. Five edits, each quoted as the exact old
text (line numbers are hints from `main` at 3284bf4). Keep mode `100755`.
Literal non-ASCII characters typed into the file: `━` (U+2501), `↻`
(U+21BB), `…` (U+2026, comment only). No em dash.

Edit 1 (line 5), old:

```
command -v jq >/dev/null || exit 0
```

new:

```
command -v jq >/dev/null || exit 0

# Segment 6 strips color codes with *(...), so extglob must be on first.
shopt -s extglob
```

Edit 2 (lines 11-12), old:

```
TRACK=$'\033[38;5;237m'
RST=$'\033[0m'
```

new:

```
TRACK=$'\033[38;5;237m'
ORANGE=$'\033[38;5;173m'
TRACK5=$'\033[38;5;246m'
BRIGHT=$'\033[38;5;254m'
BOLD=$'\033[1m'
NOBOLD=$'\033[22m'
RST=$'\033[0m'
```

Edit 3 (lines 23-24), old:

```
(.rate_limits.seven_day.used_percentage // -1 | floor)
'
```

new:

```
(.rate_limits.seven_day.used_percentage // -1 | floor),
((.rate_limits.five_hour.resets_at // 0) - now | floor)
'
```

Edit 4 (line 27), old:

```
IFS= read -r d7; } < <(jq -r "$filter" 2>/dev/null)
```

new:

```
IFS= read -r d7; IFS= read -r h5r; } < <(jq -r "$filter" 2>/dev/null)
```

Edit 5 (lines 102-114, from the `# 5-6.` comment to the end of the file), old:

```
# 5-6. Rate limits, shown only near the cap
if [ "$h5" -ge 80 ]; then
  tint "$h5" 80 95 "5h ${h5}%"
  add "$REPLY"
fi
if [ "$d7" -ge 80 ]; then
  tint "$d7" 80 95 "7d ${d7}%"
  add "$REPLY"
fi

printf '%s%s%s\n' "$G" "$out" "$RST"
exit 0
```

new:

```
# 5. 7d rate limit, shown only near the cap
if [ "$d7" -ge 80 ]; then
  tint "$d7" 80 95 "7d ${d7}%"
  add "$REPLY"
fi

# 6. 5h rate limit at the right edge: 10-cell bar, percentage, time to reset.
# Claude Code indents the row by 2 and cuts it with … past COLUMNS - 4 cells.
right=""
if [ "$h5" -ge 0 ]; then
  cells=$(( (h5 * 10 + 50) / 100 ))
  [ "$cells" -gt 10 ] && cells=10
  bar=""
  i=0
  while [ "$i" -lt "$cells" ]; do bar="${bar}━"; i=$((i + 1)); done
  rest=""
  while [ "$i" -lt 10 ]; do rest="${rest}━"; i=$((i + 1)); done
  if [ "$h5" -ge 95 ]; then hc=$R; elif [ "$h5" -ge 80 ]; then hc=$Y; else hc=$ORANGE; fi
  if [ "$h5" -ge 80 ]; then pc=$hc; else pc=$BRIGHT; fi
  pct="$BOLD$pc${h5}%$NOBOLD"
  reset=""
  if [ "$h5r" -gt 0 ]; then
    mins=$(( (h5r + 59) / 60 ))
    if [ "$mins" -ge 60 ]; then
      reset=" ↻ $((mins / 60))h $((mins % 60))m"
    else
      reset=" ↻ ${mins}m"
    fi
  fi
  right="${FILL}5h $hc$bar$TRACK5$rest $pct$FILL$reset"
  cols=$COLUMNS
  case "$cols" in ''|*[!0-9]*) cols=0 ;; esac
  gap=2
  if [ "$cols" -gt 0 ]; then
    plain=${out//$'\033'\[*([0-9;])m/}
    gap=$(( cols - 4 - ${#plain} - 15 - ${#h5} - ${#reset} ))
    if [ "$gap" -lt 2 ]; then
      right="${FILL}5h $pct"
      gap=$(( cols - 4 - ${#plain} - 4 - ${#h5} ))
    fi
    [ "$gap" -lt 2 ] && gap=2
  fi
  printf -v right '%*s%s' "$gap" '' "$right"
fi

printf '%s%s%s%s\n' "$G" "$out" "$right" "$RST"
exit 0
```

Must not change: segments 1-4, `add`, `tint`, the existing color values, the
`[ -n "$ctx" ] || exit 0` guard, the single jq call. No new external command
(no `date`, `tput`, `wc`, `sed`): `now` comes from jq, padding from the
`printf -v` builtin. bash 3.2 compatible (`/bin/bash` on macOS).

Task gates: `/bin/bash -n claude/statusline.sh`, `test -x claude/statusline.sh`,
the Status line suite (all PASS, rc 0).

Done: the five edits applied, gates green.

### T2: `claude/settings.json`, `refreshInterval`

Scope: only `claude/settings.json`, through the settings helper (it writes
through the `~/.claude/settings.json` link and validates the JSON). Apply:

```sh
~/.claude/bin/settings-edit.sh ~/.claude/settings.json '.statusLine.refreshInterval = 30'
```

Read the printed diff: only the `statusLine` object changes (a comma after the
`command` line and the new `"refreshInterval": 30` line). Do not hand-edit the
file, do not touch any other key.

Task gates: `jq -c .statusLine claude/settings.json` prints
`{"type":"command","command":"~/.claude/statusline.sh","refreshInterval":30}`;
`git diff --numstat -- claude/settings.json` prints `2	1	claude/settings.json`;
`test -L ~/.claude/settings.json` (the link survived).

Done: the key is set, gates green.

### T3: `install.sh`, Linux statusLine object with `refreshInterval`

Scope: only `install.sh`, the Linux branch near line 433 (`# Linux keeps a
local settings.json`). One edit, old:

```
  if ! jq -e '.statusLine.command == "~/.claude/statusline.sh"' "$settings" >/dev/null; then
    tmp="$(mktemp)"
    jq '.statusLine = {"type": "command", "command": "~/.claude/statusline.sh"}' \
      "$settings" > "$tmp" && mv "$tmp" "$settings"
```

new:

```
  if ! jq -e '.statusLine.command == "~/.claude/statusline.sh" and .statusLine.refreshInterval == 30' \
    "$settings" >/dev/null; then
    tmp="$(mktemp)"
    jq '.statusLine = {"type": "command", "command": "~/.claude/statusline.sh", "refreshInterval": 30}' \
      "$settings" > "$tmp" && mv "$tmp" "$settings"
```

Must not change: the theme block, the macOS branch, the `ln -sf` of the
status line script, anything else in the file.

Task gates: `bash -n install.sh`, the Install suite (all PASS, rc 0),
`git diff --stat -- install.sh` shows 1 file, 3 insertions, 2 deletions.

Done: the edit applied, gates green.

### T4: `claude/skills/cc-settings/SKILL.md`, status line geometry bullet

Scope: only `claude/skills/cc-settings/SKILL.md`. Insert the block below as
one new line right after the line that starts with
`- Footer: the permission-mode indicator has no hide key;` (line 62), in the
"Look: status line, theme, footer" section. Nothing else changes.

<!-- T4 block start -->
```
- Status line geometry (2.1.310, fullscreen): the row is indented 2 columns and cut with `…` past `COLUMNS - 4` cells, so a right-aligned segment pads to `COLUMNS - 4` (live: `claude/statusline.sh` segment 6). A terminal resize does not re-run the script; `refreshInterval` does, with the new `COLUMNS`. `disableAllHooks` turns the status line off too: probe one in an isolated instance with `--setting-sources local --settings '{"tui": "fullscreen", "statusLine": {"type": "command", "command": "<probe>"}}'` (no user hooks), `send-keys BTab` re-runs it.
```
<!-- T4 block end -->

Task gates: the block diff gate prints nothing:

```bash
diff <(awk '/<!-- T4 block start -->/{f=1; next} /<!-- T4 block end -->/{f=0} f' plans/claude-statusline-5h.md | sed '1d;$d') \
  <(grep -F -- '- Status line geometry (2.1.310, fullscreen)' claude/skills/cc-settings/SKILL.md)
```

and `sed -n 63p claude/skills/cc-settings/SKILL.md | grep -c '^- Status line geometry'`
prints `1`; `git diff --numstat -- claude/skills/cc-settings/SKILL.md` prints
`1	0	claude/skills/cc-settings/SKILL.md`.

Done: one line inserted, gates green.

## Seams

| Producer | Consumer | Shared definition |
| --- | --- | --- |
| T2 | T3 | statusLine object (same value on macOS and Linux) |
| T1 | T4 | Row geometry (`COLUMNS - 4`, indent 2), segment 6 named in the bullet |

## Edge cases

- macOS vs Linux: `/bin/bash` 3.2 on macOS (`printf -v`, extglob and
  `${var//pat/}` exist since 3.1/2.x); Linux bash 5 runs the same code. A
  server shell with a C locale counts bytes in `${#plain}`, so the segment
  sits a few cells left of the edge or goes compact, never past the cut (C32).
- Missing data: no `rate_limits.five_hour` (API key, before the first reply):
  no segment and no padding (C1, C33). No `resets_at` or a past one: no reset
  text (C26). `COLUMNS` unset or junk: gap 2 (C6, C37).
- Narrow pane: full segment, then compact `5h 26%`, then gap 2 and Claude Code
  cuts the row (C28-C31).
- Resize: the old width stays until the next trigger, at most 30 s with
  `refreshInterval`; after a shrink the row is cut with `…` meanwhile.
- Non-fullscreen TUI (`tui` unset, e.g. a Linux server): notifications share
  the row's right side and can cover the segment; the user runs fullscreen
  here, not handled.
- Dirty worktree: `main` was clean at plan time; `claude/settings.json` is
  clean too (no `/model` write pending).
- First run: Linux `install.sh` creates `{}` first (Install suite I1).

## Not doing

- A 7d bar or moving the 7d segment right; spend limit; cost; a clock.
- Restyling the left row (gray 240, context bar glyphs).
- Multi-line output, `padding`.
- `README.md` (it describes the status line by path only), `everything.md`.
- ClaudeBar changes.
